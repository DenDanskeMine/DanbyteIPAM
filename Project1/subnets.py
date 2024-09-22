import db

def get_all_subnets():
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM SUBNETS')
    subnets = cursor.fetchall()
    conn.close()
    return subnets

def get_subnet(subnet_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM SUBNETS WHERE id = %s', (subnet_id,))
    subnet = cursor.fetchone()
    conn.close()
    return subnet

def update_subnet(subnet_id, **kwargs):
    columns = ', '.join(f"{k} = %s" for k in kwargs.keys())
    values = tuple(kwargs.values()) + (subnet_id,)
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'UPDATE SUBNETS SET {columns} WHERE id = %s', values)
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating subnet: {e}")
        raise
    finally:
        cursor.close()
        conn.close()