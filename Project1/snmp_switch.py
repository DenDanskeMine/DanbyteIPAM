import logging
from easysnmp import Session
import db

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def gather_snmp_data(ip, community='public'):
    session = Session(hostname=ip, community=community, version=2)

    # Example OIDs for demonstration purposes
    numOf_int_oid = '1.3.6.1.2.1.2.1.0'  # Number of interfaces
    int_names_oid = '1.3.6.1.2.1.2.2.1.2'  # Interface names
    int_status_oid = '1.3.6.1.2.1.2.2.1.8'  # Interface statuses
    is_shutdown_oid = '1.3.6.1.2.1.2.2.1.7'  # Interface shutdown status

    # Collect SNMP data
    numOf_int = session.get(numOf_int_oid).value
    int_names = [item.value for item in session.walk(int_names_oid)]
    int_status = [item.value for item in session.walk(int_status_oid)]
    is_shutdown = [item.value for item in session.walk(is_shutdown_oid)]

    logging.debug(f"SNMP Data for IP {ip}: numOf_int={numOf_int}, int_names={int_names}, int_status={int_status}, is_shutdown={is_shutdown}")

    return {
        'numOf_int': numOf_int,
        'int_names': ','.join(int_names),  # Store as comma-separated values
        'int_status': ','.join(int_status),  # Store as comma-separated values
        'is_shutdown': ','.join(is_shutdown)  # Store as comma-separated values for each interface
    }

def store_snmp_data(switch_id, snmp_data):
    conn = db.get_db_connection()
    cursor = conn.cursor()
    logging.debug(f"Storing SNMP Data for switch_id {switch_id}: {snmp_data}")
    try:
        cursor.execute('''
            INSERT INTO SNMP_DATA_SWITCH (switch_id, numOf_int, int_names, int_status, interface_shutdown_status)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                numOf_int = VALUES(numOf_int),
                int_names = VALUES(int_names),
                int_status = VALUES(int_status),
                interface_shutdown_status = VALUES(interface_shutdown_status)
        ''', (switch_id, snmp_data['numOf_int'], snmp_data['int_names'], snmp_data['int_status'], snmp_data['is_shutdown']))
        conn.commit()
    except Exception as e:
        logging.error(f"Error storing SNMP data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
def snmp_switch():
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM SWITCHES')
    switches = cursor.fetchall()
    cursor.close()
    conn.close()

    for switch in switches:
        ip = switch['ip_address']
        switch_id = switch['id']
        snmp_data = gather_snmp_data(ip)
        store_snmp_data(switch_id, snmp_data)

    return switches

def refresh_snmp_data_for_switch(switch_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the IP address of the switch
    cursor.execute('SELECT ip_address FROM SWITCHES WHERE id = %s', (switch_id,))
    switch = cursor.fetchone()
    
    if not switch:
        logging.error(f"No switch found with id {switch_id}")
        return
    
    ip = switch['ip_address']
    cursor.close()
    conn.close()
    
    # Gather SNMP data
    snmp_data = gather_snmp_data(ip)
    
    # Store SNMP data
    store_snmp_data(switch_id, snmp_data)