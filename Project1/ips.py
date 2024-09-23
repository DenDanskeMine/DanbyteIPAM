import db
import logging
from ipaddress import ip_network
import subprocess
import socket
import datetime
import ipaddress
import asyncio


logging.basicConfig(level=logging.INFO)

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
    logging.info(f"Found {len(ips)} IPs to scan")

async def ping_ip(ip):
    try:
        # Ping the IP address asynchronously
        process = await asyncio.create_subprocess_exec(
            'ping', '-c', '1', ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode == 0
    except Exception as e:
        logging.error(f"Error pinging IP {ip}: {e}")
        return False

async def resolve_hostname(ip):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, socket.gethostbyaddr, ip)
        return result[0]  # Extract the hostname from the tuple
    except socket.herror:
        return None
    
async def detect_hosts(subnet_id=None):
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
    logging.info(f"Found {len(subnets)} subnets to scan")

    tasks = []
    for subnet in subnets:
        # Use the 'range' field to generate the IP range
        ip_range = generate_ip_range(subnet['range'])

        for ip in ip_range:
            tasks.append(scan_and_insert_ip(ip, subnet['id'], cursor, conn))  # Pass conn here

    await asyncio.gather(*tasks)

    cursor.close()
    conn.close()
    logging.info("Host detection completed")

async def scan_and_insert_ip(ip, subnet_id, cursor, conn):
    is_online = await ping_ip(ip)
    hostname = await resolve_hostname(ip) if is_online else None

    if is_online:
        logging.info(f"Detected active host: {ip} with hostname: {hostname}")

        # Check if the IP already exists in the database
        cursor.execute(
            'SELECT COUNT(*) FROM IPs WHERE address = %s AND subnet_id = %s',
            (ip, subnet_id)
        )
        result = cursor.fetchone()
        if result['COUNT(*)'] == 0:
            # Insert the active IP into the IPs table
            cursor.execute(
                'INSERT INTO IPs (address, hostname, subnet_id, status, is_scannable, is_resolvable, last_seen) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (ip, hostname, subnet_id, 1, True, hostname is not None, datetime.datetime.now())
            )
            conn.commit()
        else:
            logging.info(f"IP {ip} already exists in subnet {subnet_id}")

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
    
    # Fetch the IP data including the switch information
    ips = cursor.fetchall()
    conn.close()
    
    # Return both subnet details and IPs with switch information
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

    # Debugging output to check what is returned
    print(ip)  # Add this to verify what is being returned
    
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