import mysql.connector
import db
import logging
from db import get_db_connection

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection function
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',        # Adjust with your DB details
        user='danbyte_admin',    # Adjust with your DB user
        password='admin',        # Adjust with your DB password
        database='DANBYTE'       # Adjust with your DB name
    )
    return connection

# Function to fetch switch data
# Project1/switch_data.py
def get_switch_data(switch_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query for the latest switch interfaces based on timestamp
    cursor.execute('''
        SELECT * FROM SNMP_DATA_SWITCH 
        WHERE switch_id = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (switch_id,))

    # Fetch the result
    switch_data = cursor.fetchone()

    # Ensure the result is fully processed
    cursor.fetchall()  # This fetches any remaining results, if any

    cursor.close()
    conn.close()

    if not switch_data:
        logging.error(f"No data found for switch_id {switch_id}")
        return None

    # Log the data returned
    logging.debug(f"Fetched switch data for switch_id {switch_id}: {switch_data}")

    # Check if 'int_names' and 'int_status' keys are present
    if 'int_names' not in switch_data or 'int_status' not in switch_data:
        logging.error(f"Missing 'int_names' or 'int_status' in switch data for switch_id {switch_id}")
        return None

    # Split int_names and int_status into lists
    int_names = switch_data.get('int_names', '').split(',')
    int_status = switch_data.get('int_status', '').split(',')
    int_shutdown = switch_data.get('interface_shutdown_status', '').split(',')

    if len(int_names) != len(int_status) or len(int_names) != len(int_shutdown):
        logging.error(f"Mismatch between int_names, int_status, and int_shutdown lengths for switch_id {switch_id}")
        return None

    return {
        'switch': switch_data,
        'int_names': int_names,
        'int_status': int_status,
        'int_shutdown': int_shutdown
    }


def add_new_switch(hostname, ip_address, location, community, model, firmware_version, port_count, is_online, is_favorite):
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            INSERT INTO SWITCHES (hostname, ip_address, location, community, model, firmware_version, port_count, is_online, is_favorite)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (hostname, ip_address, location, community, model, firmware_version, port_count, is_online, is_favorite)
        )
        conn.commit()
        logging.info(f"Switch {hostname} added successfully.")
    except Exception as e:
        logging.error(f"Error adding switch: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

__all__ = ['get_switch_data', 'add_new_switch']