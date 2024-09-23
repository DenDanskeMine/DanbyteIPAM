import db
import logging
from ipaddress import ip_network
import subprocess
import socket
import datetime
import ipaddress

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def scan_ips(subnet_id=None):
    logging.info("Starting IP scan")

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if subnet_id:
        logging.info(f"Scanning subnet with ID: {subnet_id}")
        cursor.execute('SELECT * FROM IPs WHERE subnet_id = %s AND is_scannable = TRUE', (subnet_id,))
    else:
        logging.info("Scanning all scannable IPs")
        cursor.execute('SELECT * FROM IPs WHERE is_scannable = TRUE')

    ips = cursor.fetchall()
    cursor.close()
    conn.close()

    logging.info(f"Found {len(ips)} IPs to scan")

    for ip_record in ips:
        ip = ip_record['address']
        subnet_id = ip_record['subnet_id']
        scan_and_resolve(ip, subnet_id)

    logging.info("IP scan completed")

def scan_and_resolve(ip, subnet_id):
    is_online = ping_ip(ip)
    hostname = resolve_hostname(ip) if is_online else None

    conn = db.get_db_connection()
    cursor = conn.cursor()

    # Check if the IP exists in the database
    cursor.execute(
        'SELECT * FROM IPs WHERE address = %s AND subnet_id = %s',
        (ip, subnet_id)
    )
    result = cursor.fetchone()

    if is_online:
        logging.info(f"Detected active host: {ip} with hostname: {hostname}")
        if result is None:
            # Insert new IP entry
            cursor.execute(
                '''
                INSERT INTO IPs (address, hostname, subnet_id, status, is_scannable, is_resolvable, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''',
                (ip, hostname if hostname else None, subnet_id, 1, True, bool(hostname), datetime.datetime.now())
            )
            conn.commit()
            logging.info(f"Inserted IP {ip} with hostname {hostname} into subnet {subnet_id}")
        else:
            # Update existing IP entry
            cursor.execute(
                '''
                UPDATE IPs
                SET hostname = %s, last_seen = %s, status = %s, is_resolvable = %s
                WHERE address = %s AND subnet_id = %s
                ''',
                (hostname if hostname else None, datetime.datetime.now(), 1, bool(hostname), ip, subnet_id)
            )
            conn.commit()
            logging.info(f"Updated IP {ip} with hostname {hostname} in subnet {subnet_id}")
    else:
        logging.info(f"IP {ip} is not online")
        if result is not None:
            # Update the IP status to offline
            cursor.execute(
                '''
                UPDATE IPs
                SET status = %s
                WHERE address = %s AND subnet_id = %s
                ''',
                (0, ip, subnet_id)
            )
            conn.commit()
            logging.info(f"Updated IP {ip} status to offline in subnet {subnet_id}")
        else:
            logging.info(f"IP {ip} does not exist in database and is offline")

    cursor.close()
    conn.close()


def ping_ip(ip):
    try:
        result = subprocess.run(['ping', '-c', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Error pinging IP {ip}: {e}")
        return False

def resolve_hostname(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        logging.info(f"Resolved hostname for IP {ip}: {hostname}")
        return hostname
    except socket.herror as e:
        logging.warning(f"Failed to resolve hostname for IP {ip}: {e}")
        return None

def detect_hosts(subnet_id=None):
    logging.info("Starting host detection")

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if subnet_id:
        logging.info(f"Detecting hosts in subnet with ID: {subnet_id}")
        cursor.execute('SELECT * FROM SUBNETS WHERE id = %s', (subnet_id,))
    else:
        logging.info("Detecting hosts in all subnets")
        cursor.execute('SELECT * FROM SUBNETS')

    subnets = cursor.fetchall()
    cursor.close()
    conn.close()

    logging.info(f"Found {len(subnets)} subnets to scan")

    for subnet in subnets:
        # Use the 'range' field to generate the IP range
        ip_range = generate_ip_range(subnet['range'])
        subnet_id = subnet['id']

        for ip in ip_range:
            scan_and_insert_ip(ip, subnet_id)

    logging.info("Host detection completed")

def scan_and_insert_ip(ip, subnet_id):
    is_online = ping_ip(ip)
    hostname = resolve_hostname(ip) if is_online else None

    conn = db.get_db_connection()
    cursor = conn.cursor()

    if is_online:
        logging.info(f"Detected active host: {ip} with hostname: {hostname}")

        # Check if the IP already exists in the database
        cursor.execute(
            'SELECT * FROM IPs WHERE address = %s AND subnet_id = %s',
            (ip, subnet_id)
        )
        result = cursor.fetchone()
        if result is None:
            # Insert the active IP into the IPs table
            cursor.execute(
                '''
                INSERT INTO IPs (address, hostname, subnet_id, status, is_scannable, is_resolvable, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''',
                (ip, hostname if hostname else None, subnet_id, 1, True, bool(hostname), datetime.datetime.now())
            )
            conn.commit()
            logging.info(f"Inserted IP {ip} with hostname {hostname} into subnet {subnet_id}")
        else:
            # Update the existing IP entry with the new hostname
            cursor.execute(
                '''
                UPDATE IPs
                SET hostname = %s, last_seen = %s, status = %s, is_resolvable = %s
                WHERE address = %s AND subnet_id = %s
                ''',
                (hostname if hostname else None, datetime.datetime.now(), 1, bool(hostname), ip, subnet_id)
            )
            conn.commit()
            logging.info(f"Updated IP {ip} with hostname {hostname} in subnet {subnet_id}")
    else:
        logging.info(f"IP {ip} is not online")
        # Optionally, you can insert/update offline IPs here if needed
        cursor.execute(
            '''
            UPDATE IPs
            SET status = %s
            WHERE address = %s AND subnet_id = %s
            ''',
            (0, ip, subnet_id)
        )
        conn.commit()
        logging.info(f"Updated IP {ip} status to offline in subnet {subnet_id}")

    cursor.close()
    conn.close()

def generate_ip_range(cidr):
    # Generate IP range from CIDR notation
    net = ip_network(cidr, strict=False)
    return [str(ip) for ip in net.hosts()]

def get_ips_for_subnet(subnet_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch the subnet details only once
    cursor.execute('SELECT * FROM SUBNETS WHERE id = %s', (subnet_id,))
    subnet = cursor.fetchone()
    
    # Fetch IPs and corresponding switch details in a single query
    cursor.execute("""
        SELECT IPs.*, SWITCHES.hostname AS switch_hostname, SWITCHES.ip_address AS switch_ip
        FROM IPs
        LEFT JOIN SWITCHES ON IPs.switch_id = SWITCHES.id
        WHERE IPs.subnet_id = %s
    """, (subnet_id,))
    
    ips = cursor.fetchall()
    
    # Cast 'status' to integer for each IP
    for ip in ips:
        ip['status'] = int(ip['status']) if ip['status'] is not None else -1
    
    conn.close()
    
    return subnet, ips


def get_ips_for_availability(subnet_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the subnet details to get the range
    cursor.execute('SELECT `range` FROM SUBNETS WHERE id = %s', (subnet_id,))
    subnet = cursor.fetchone()

    if not subnet:
        return None, []

    # Get all the IPs already in use from the IPs table
    cursor.execute('SELECT address FROM IPs WHERE subnet_id = %s', (subnet_id,))
    used_ips = {row['address'] for row in cursor.fetchall()}

    # Generate the full range of IPs from the subnet
    subnet_range = ip_network(subnet['range'])
    all_ips = [str(ip) for ip in subnet_range.hosts()]  # List of all IPs in the range

    conn.close()

    return used_ips, all_ips

def get_ip(ip_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Join IPs and Switches tables to get the switch hostname
    cursor.execute("""
        SELECT IPs.*, SWITCHES.hostname AS switch_hostname
        FROM IPs
        LEFT JOIN SWITCHES ON IPs.switch_id = SWITCHES.id
        WHERE IPs.id = %s
    """, (ip_id,))
    
    ip = cursor.fetchone()
    conn.close()

    # Convert 'None' strings to None
    for key in ['hostname', 'mac', 'description', 'note', 'location', 'port']:
        if ip[key] == 'None':
            ip[key] = None

    # Debugging output to check what is returned
    logging.debug(f"Fetched IP data: {ip}")
    
    return ip


def add_ip_to_subnet(subnet_id, **kwargs):
    kwargs['subnet_id'] = subnet_id
    columns = ', '.join(kwargs.keys())
    placeholders = ', '.join(['%s'] * len(kwargs))
    values = tuple(kwargs.values())
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'INSERT INTO IPs ({columns}) VALUES ({placeholders})', values)
        conn.commit()
    except Exception as e:
        logging.error(f"Error adding IP: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def update_ip(ip_id, **kwargs):
    conn = db.get_db_connection()
    cursor = conn.cursor()

    columns = ', '.join(f"{k} = %s" for k in kwargs.keys())
    values = tuple(kwargs.values()) + (ip_id,)

    query = f"UPDATE IPs SET {columns} WHERE id = %s"
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()
