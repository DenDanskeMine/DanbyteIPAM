import random
import logging
from datetime import datetime
import sys

# Assuming you have a `db` module with `get_db_connection` function
import db  

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler("switch_creation.log"),
        logging.StreamHandler()
    ]
)

def add_new_switch(hostname, ip_address, location, community, model, firmware_version, port_count, is_online, is_favorite):
    """
    Inserts a new switch into the SWITCHES table.
    """
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            INSERT INTO SWITCHES (
                hostname, ip_address, location, community, 
                model, firmware_version, port_count, is_online, is_favorite
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                hostname, ip_address, location, community, 
                model, firmware_version, port_count, is_online, is_favorite
            )
        )
        conn.commit()
        logging.info(f"Switch {hostname} added successfully with IP {ip_address}.")
    except Exception as e:
        logging.error(f"Error adding switch {hostname}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def generate_unique_hostnames(count):
    """
    Generates a list of unique hostnames.
    """
    return [f"DB-SWITCH-MIL-{i:03d}" for i in range(1, count + 1)]

def generate_unique_ip_addresses(count):
    """
    Generates a list of unique IP addresses starting from 10.0.0.1.
    """
    ip_addresses = []
    octet2 = 5
    octet3 = 0
    octet4 = 1
    for _ in range(count):
        if octet4 > 254:
            octet4 = 1
            octet3 += 1
            if octet3 > 254:
                octet3 = 0
                octet2 += 1
                if octet2 > 254:
                    logging.error("Exceeded IP address range.")
                    sys.exit(1)
        ip = f"10.{octet2}.{octet3}.{octet4}"
        ip_addresses.append(ip)
        octet4 += 1
    return ip_addresses

def main():
    """
    Main function to generate and insert switches.
    """
    count = 1000000

    # Generate unique hostnames and IP addresses
    hostnames = generate_unique_hostnames(count)
    ip_addresses = generate_unique_ip_addresses(count)

    # Define possible values for other fields
    locations = [
        'Data Center A', 'Data Center B', 'Data Center C', 'Data Center D', 'Data Center E',
        'Data Center F', 'Data Center G', 'Data Center H', 'Data Center I', 'Data Center J',
        'Hosting Center 1', 'Hosting Center 2', 'Hosting Center 3', 'Hosting Center 4', 'Hosting Center 5',
        'Hosting Center 6', 'Hosting Center 7', 'Hosting Center 8', 'Hosting Center 9', 'Hosting Center 10',
        'Lab 1', 'Lab 2', 'Lab 3', 'Lab 4', 'Lab 5',
        'Lab 6', 'Lab 7', 'Lab 8', 'Lab 9', 'Lab 10',
        'Test Lab 1', 'Test Lab 2', 'Test Lab 3', 'Test Lab 4', 'Test Lab 5',
        'Test Lab 6', 'Test Lab 7', 'Test Lab 8', 'Test Lab 9', 'Test Lab 10',
        'Office 1', 'Office 2', 'Office 3', 'Office 4', 'Office 5',
        'Office 6', 'Office 7', 'Office 8', 'Office 9', 'Office 10',
        'Branch Office A', 'Branch Office B', 'Branch Office C', 'Branch Office D', 'Branch Office E',
        'Branch Office F', 'Branch Office G', 'Branch Office H', 'Branch Office I', 'Branch Office J',
        'Remote Office 1', 'Remote Office 2', 'Remote Office 3', 'Remote Office 4', 'Remote Office 5',
        'Remote Office 6', 'Remote Office 7', 'Remote Office 8', 'Remote Office 9', 'Remote Office 10',
        'Corporate Office 1', 'Corporate Office 2', 'Corporate Office 3', 'Corporate Office 4', 'Corporate Office 5',
        'Corporate Office 6', 'Corporate Office 7', 'Corporate Office 8', 'Corporate Office 9', 'Corporate Office 10',
        'Development Lab', 'Research Lab', 'QA Lab', 'Staging Lab', 'Production Lab',
        'Integration Lab', 'Simulation Lab', 'Analytics Lab', 'AI Lab', 'IoT Lab'
    ]
    communities = ['public', 'private']
    models = ['Cisco 2960', 'HP 1920', 'Cisco 3750', 'Brocade X66xx', 'DELL xxxx']
    firmware_versions = ['15.2(4)', '6.7.R', '12.2(55)', '15.2(4)', '6.7.R']
    port_counts = [24, 48, 12]
    is_online_options = [1, 0]
     
    is_favorite_options = [0, 0]
    toggle_SNMP_options = [0, 0]

    for i in range(count):
        hostname = hostnames[i]
        ip_address = ip_addresses[i]
        location = random.choice(locations)
        community = random.choice(communities)
        model = random.choice(models)
        firmware_version = random.choice(firmware_versions)
        port_count = random.choice(port_counts)
        is_online = random.choice(is_online_options)
        is_favorite = random.choice(is_favorite_options)
        toggle_SNMP = random.choice(toggle_SNMP_options)

        add_new_switch(
            hostname, ip_address, location, community, 
            model, firmware_version, port_count, is_online, is_favorite
        )

    logging.info("Completed adding all switches.")

if __name__ == "__main__":
    main()
