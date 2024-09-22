from flask import Flask, render_template, redirect, url_for, flash, request
from get_favorite_switch import get_favorite_switch
from snmp_switch import snmp_switch, refresh_snmp_data_for_switch
from switch_data import get_switch_data
from group_interfaces import group_interfaces_by_stack
import db
import logging
from subnets import get_all_subnets, get_subnet, update_subnet
from ips import get_ips_for_subnet, get_ip, add_ip_to_subnet, update_ip
from ipaddress import ip_network

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'supersecretkey'

@app.context_processor
def inject_switches():
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) as count FROM SWITCHES WHERE is_online = TRUE')
    online_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM SWITCHES WHERE is_online = FALSE')
    offline_count = cursor.fetchone()['count']
    cursor.close()
    conn.close()
    num_switches = {'online': online_count, 'offline': offline_count}
    return dict(num_switches=num_switches)

@app.route('/')
def index():
    favorite_switches, count_favorite_switches = get_favorite_switch()
    return render_template('index.html', title='Home', favorite_switches=favorite_switches, count_favorite_switches=count_favorite_switches)

@app.route('/tasks')
def show_tasks():
    tasks = ['Task 1', 'Task 2', 'Task 3']
    return render_template('tasks.html', title='Tasks', tasks=tasks)

@app.route('/collect_snmp_data', methods=['POST'])
def collect_snmp_data():
    try:
        snmp_switch()
        flash('SNMP data collected successfully!', 'success')
    except Exception as e:
        logging.error(f"Error collecting SNMP data: {e}")
        flash('Error collecting SNMP data. Check logs for details.', 'danger')
    return redirect(url_for('index'))

@app.route('/refresh_snmp_data_for_switch/<int:switch_id>')
def refresh_snmp_data_for_switch_route(switch_id):
    try:
        refresh_snmp_data_for_switch(switch_id)
        flash('SNMP data refreshed successfully!', 'success')
    except Exception as e:
        logging.error(f"Error refreshing SNMP data for switch {switch_id}: {e}")
        flash('Error refreshing SNMP data. Check logs for details.', 'danger')
    return redirect(url_for('show_switch', switch_id=switch_id))

@app.route('/switch/<int:switch_id>')
def show_switch(switch_id):
    try:
        switch_data = get_switch_data(switch_id)
        if switch_data:
            logging.debug(f"Switch data for switch_id {switch_id}: {switch_data}")
            int_names = switch_data['switch']['int_names'].split(',')
            int_status = switch_data['switch']['int_status'].split(',')
            int_shutdown = switch_data['switch']['interface_shutdown_status'].split(',')
            interfaces = [{'name': name, 'status': status, 'shutdown': shutdown} for name, status, shutdown in zip(int_names, int_status, int_shutdown)]
            logging.debug(f"Interfaces before grouping: {interfaces}")
            stack_groups, grouped_interfaces = group_interfaces_by_stack(interfaces)
            logging.debug(f"Grouped interfaces by stack: {stack_groups}")
            logging.debug(f"Grouped interfaces: {grouped_interfaces}")
            return render_template('switch.html', title=f'Switch {switch_id}', stack_groups=stack_groups, grouped_interfaces=grouped_interfaces, switch_id=switch_id, switch=switch_data['switch'])
    except Exception as e:
        logging.error(f"Error showing switch {switch_id}: {e}")
        flash('Error showing switch. Check logs for details.', 'danger')
        return redirect(url_for('index'))

@app.route('/subnets')
def show_subnets():
    subnets = get_all_subnets()
    return render_template('subnets.html', title='Subnets', subnets=subnets)

@app.route('/subnet/<int:subnet_id>')
def show_subnet_ips(subnet_id):
    subnet, ips = get_ips_for_subnet(subnet_id)
    
    # Calculate available IPs within the subnet range
    subnet_range = ip_network(subnet['range'])
    used_ips = {ip['address'] for ip in ips}
    available_ips = [str(ip) for ip in subnet_range.hosts() if str(ip) not in used_ips]
    
    return render_template('ips.html', title=f'IPs in Subnet {subnet["name"]}', subnet=subnet, ips=ips, available_ips=available_ips)

@app.route('/ip/<int:ip_id>')
def show_ip(ip_id):
    ip = get_ip(ip_id)
    return render_template('ip.html', title=f'IP {ip["address"]}', ip=ip)

@app.route('/edit-ip/<int:ip_id>', methods=['GET', 'POST'])
def edit_ip(ip_id):
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # Handle case where switch_id is not selected (set it to None)
        if not data.get('switch_id'):
            data['switch_id'] = None
        
        # Update IP and redirect
        update_ip(ip_id, **data)
        flash('IP updated successfully!', 'success')
        return redirect(url_for('show_subnet_ips', subnet_id=data['subnet_id']))

    # Fetch the current IP and available switches
    current_ip = get_ip(ip_id)
    all_switches = get_all_switches()

    return render_template(
        'edit-ip.html',
        ip=current_ip,
        available_ips=get_available_ips(current_ip['subnet_id']),
        switches=all_switches
    )


    return render_template(
        'edit-ip.html',
        title=f'Edit IP {current_ip["address"]}',
        ip=current_ip,
        available_ips=available_ips,
        switches=all_switches
    )

@app.route('/edit-subnet/<int:subnet_id>', methods=['GET', 'POST'])
def edit_subnet(subnet_id):
    if request.method == 'POST':
        data = request.form.to_dict()
        update_subnet(subnet_id, **data)
        flash('Subnet updated successfully!', 'success')
        return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))
    subnet = get_subnet(subnet_id)
    return render_template('edit-subnet.html', title=f'Edit Subnet {subnet["name"]}', subnet=subnet)

@app.route('/add-ip/<int:subnet_id>', methods=['POST'])
def add_ip(subnet_id):
    data = request.form.to_dict()
    add_ip_to_subnet(subnet_id, **data)
    flash('IP added successfully!', 'success')
    return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))


def get_all_switches():
    # Query the database for all switches
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, hostname FROM SWITCHES')
    switches = cursor.fetchall()
    conn.close()
    return switches

def get_available_ips(subnet_id):
    # Fetch the subnet range from the database
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Correct query with backticks around `range`
    cursor.execute('SELECT `range` FROM SUBNETS WHERE id = %s', (subnet_id,))
    subnet = cursor.fetchone()

    if not subnet:
        return []

    # Fetch used IPs from the IPs table for this subnet
    cursor.execute('SELECT address FROM IPs WHERE subnet_id = %s', (subnet_id,))
    used_ips = {row['address'] for row in cursor.fetchall()}
    
    conn.close()

    # Calculate the available IPs based on the subnet range
    subnet_range = ip_network(subnet['range'])
    available_ips = [str(ip) for ip in subnet_range.hosts() if str(ip) not in used_ips]

    return available_ips

def get_switch_details(switch_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM SWITCHES WHERE id = %s", (switch_id,))
    switch = cursor.fetchone()

    conn.close()
    return switch



if __name__ == '__main__':
    app.run(debug=True)