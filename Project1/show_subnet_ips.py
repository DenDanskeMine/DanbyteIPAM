import db  # Assuming your database connection function is in db.py

def get_ips_for_subnet(subnet_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all IPs associated with the subnet
    cursor.execute('SELECT * FROM IPs WHERE subnet_id = %s', (subnet_id,))
    ips = cursor.fetchall()

    # Get the subnet details
    cursor.execute('SELECT * FROM SUBNETS WHERE id = %s', (subnet_id,))
    subnet = cursor.fetchone()

    conn.close()

    return subnet, ips


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