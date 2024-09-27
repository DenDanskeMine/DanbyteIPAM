import logging
from easysnmp import Session, EasySNMPTimeoutError
import src.db as db
import binascii
import asyncio

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def gather_snmp_data(ip, community='public'):
    try:
        # Use asyncio.to_thread to run the blocking SNMP session in an async manner
        snmp_data = await asyncio.to_thread(run_snmp_session, ip, community)
        return snmp_data
    except EasySNMPTimeoutError as e:
        logging.error(f"Error collecting SNMP data from {ip}: {e}")
        return None

def run_snmp_session(ip, community):
    session = Session(hostname=ip, community=community, version=2)
    
    # Example OIDs
    numOf_int_oid = '1.3.6.1.2.1.2.1.0'
    int_names_oid = '1.3.6.1.2.1.2.2.1.2'
    int_status_oid = '1.3.6.1.2.1.2.2.1.8'
    is_shutdown_oid = '1.3.6.1.2.1.2.2.1.7'
    vlan_oid = '1.3.6.1.2.1.17.7.1.4.5.1.1'
    mac_oid = '1.3.6.1.2.1.2.2.1.6'

    # Collect SNMP data
    numOf_int = session.get(numOf_int_oid).value
    int_names = [item.value for item in session.walk(int_names_oid)]
    int_status = [item.value for item in session.walk(int_status_oid)]
    is_shutdown = [item.value for item in session.walk(is_shutdown_oid)]
    vlan = [item.value for item in session.walk(vlan_oid)]
    mac = [item.value for item in session.walk(mac_oid)]

    return {
        'numOf_int': numOf_int,
        'int_names': ','.join(int_names),
        'int_status': ','.join(int_status),
        'is_shutdown': ','.join(is_shutdown),
        'vlan': ','.join(vlan),
        'mac': format_mac_addresses(mac)
    }

def format_mac_addresses(mac_list):
    return ','.join(binascii.hexlify(mac.encode()).decode() for mac in mac_list)

def store_snmp_data(switch_id, snmp_data):
    if snmp_data is None:
        logging.error(f"SNMP data for switch_id {switch_id} is None, skipping storage.")
        return

    conn = db.get_db_connection()
    cursor = conn.cursor()
    logging.debug(f"Storing SNMP Data for switch_id {switch_id}: {snmp_data}")
    try:
        # Ensure the mac data fits within the column size constraints
        max_mac_length = 4096  # Adjust this value based on your actual column size
        mac_data = snmp_data['mac']
        if len(mac_data) > max_mac_length:
            mac_data = mac_data[:max_mac_length]
            logging.warning(f"MAC data truncated for switch_id {switch_id}")

        # Log the SQL query to check data insertion
        logging.debug(f"Executing SQL to store data: {snmp_data}")
        cursor.execute('''
            INSERT INTO SNMP_DATA_SWITCH (switch_id, numOf_int, int_names, int_status, interface_shutdown_status, vlan, mac)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                numOf_int = VALUES(numOf_int),
                int_names = VALUES(int_names),
                int_status = VALUES(int_status),
                interface_shutdown_status = VALUES(interface_shutdown_status),
                vlan = VALUES(vlan),
                mac = VALUES(mac)
        ''', (switch_id, snmp_data['numOf_int'], snmp_data['int_names'], snmp_data['int_status'], snmp_data['is_shutdown'], snmp_data['vlan'], mac_data))
        conn.commit()
        logging.debug(f"Successfully inserted SNMP data for switch_id {switch_id}")
    except Exception as e:
        logging.error(f"Error storing SNMP data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

async def snmp_switch():
    # Use the async fetch_switches to get the data
    switches = await db.fetch_switches()

    for switch in switches:
        if switch['toggle_SNMP'] == 1:
            ip = switch['ip_address']
            switch_id = switch['id']

            # Collect SNMP data asynchronously
            snmp_data = await gather_snmp_data(ip)

            # Log if SNMP data was gathered
            if snmp_data is not None:
                logging.debug(f"SNMP Data collected for switch {switch_id}: {snmp_data}")
                store_snmp_data(switch_id, snmp_data)  # Sync call, so no await here
            else:
                logging.error(f"No SNMP data was collected for switch_id {switch_id}")
        else:
            logging.debug(f"SNMP data collection is disabled for switch_id {switch['id']}")

    return switches

# For synchronous refresh of specific switch SNMP data
def refresh_snmp_data_for_switch(switch_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the IP address and toggle_SNMP value of the switch
    cursor.execute('SELECT ip_address, toggle_SNMP FROM SWITCHES WHERE id = %s', (switch_id,))
    switch = cursor.fetchone()
    
    if not switch:
        logging.error(f"No switch found with id {switch_id}")
        return
    
    if switch['toggle_SNMP'] == 0:
        logging.debug(f"SNMP data collection is disabled for switch_id {switch_id}")
        return
    
    ip = switch['ip_address']
    cursor.close()
    conn.close()
    
    # Gather SNMP data synchronously
    snmp_data = gather_snmp_data(ip)
    
    # Store SNMP data synchronously
    store_snmp_data(switch_id, snmp_data)
