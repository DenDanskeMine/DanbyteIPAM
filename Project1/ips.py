import db
import logging

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