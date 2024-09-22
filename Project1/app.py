from flask import Flask, render_template, redirect, url_for, flash, request
from get_favorite_switch import get_favorite_switch
from snmp_switch import snmp_switch, refresh_snmp_data_for_switch
from switch_data import get_switch_data
from group_interfaces import group_interfaces_by_stack
from get_favorite_subnets import get_favorite_subnets
from show_subnets import get_all_subnets
from show_subnet_ips import get_ips_for_subnet, add_ip_to_subnet
from ipaddress import ip_network
from get_favorite_ips import get_favorite_ips
import db
import logging

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

    num_switches = {
        'online': online_count,
        'offline': offline_count,
    }

    return dict(num_switches=num_switches)

@app.route('/')
def index():
    favorite_switches, count_favorite_switches = get_favorite_switch()
    favorite_subnets, count_favorite_subnets = get_favorite_subnets()
    favorite_ips, count_favorite_ips = get_favorite_ips()

    return render_template('index.html', 
                           title='Home', 
                           favorite_switches=favorite_switches, 
                           count_favorite_switches=count_favorite_switches, 
                           favorite_subnets=favorite_subnets, 
                           count_favorite_subnets=count_favorite_subnets,
                           favorite_ips=favorite_ips, 
                           count_favorite_ips=count_favorite_ips)

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
            
            interfaces = switch_data['interfaces']
            logging.debug(f"Interfaces before grouping: {interfaces}")
            
            grouped_interfaces, stack_groups = group_interfaces_by_stack(interfaces)
            logging.debug(f"Grouped interfaces by stack: {stack_groups}")
            logging.debug(f"Grouped interfaces: {grouped_interfaces}")
            
            return render_template('switch.html', title=f'Switch {switch_id}', stack_groups=stack_groups, grouped_interfaces=grouped_interfaces, switch_id=switch_id, switch=switch_data['switch'], interfaces=interfaces)
        
        flash('Switch not found!', 'danger')
    except KeyError as e:
        logging.error(f"KeyError: {e}")
        flash(f"KeyError: {e}", 'danger')
    except Exception as e:
        logging.error(f"Error fetching switch data: {e}")
        flash('Error fetching switch data. Check logs for details.', 'danger')
    return redirect(url_for('index'))

@app.route('/subnet/<int:subnet_id>/ips')
def show_subnet_ips(subnet_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM SUBNETS WHERE id = %s', (subnet_id,))
    subnet = cursor.fetchone()

    cursor.execute('SELECT address FROM IPs WHERE subnet_id = %s', (subnet_id,))
    assigned_ips = [row['address'] for row in cursor.fetchall()]

    network = ip_network(subnet['range'])
    all_ips = [str(ip) for ip in network.hosts()]
    
    available_ips = [ip for ip in all_ips if ip not in assigned_ips]
    
    cursor.execute('SELECT * FROM IPs WHERE subnet_id = %s', (subnet_id,))
    ips = cursor.fetchall()

    conn.close()

    return render_template('view_subnet_ips.html', subnet=subnet, ips=ips, available_ips=available_ips)

@app.route('/subnets')
def show_subnets():
    subnets = get_all_subnets()
    return render_template('view_subnets.html', title='Subnets', subnets=subnets)

@app.route('/subnet/<int:subnet_id>/add_ip', methods=['POST'])
def add_ip(subnet_id):
    form_data = request.form.to_dict()
    form_data['subnet_id'] = subnet_id

    # Log the form data for debugging
    logging.debug(f"Form data: {form_data}")

    # Convert checkbox values to boolean
    for key in ['is_favorite', 'is_nested', 'is_scannable', 'is_resolvable', 'show_status', 'is_gateway']:
        form_data[key] = form_data.get(key) == 'on'

    columns = ', '.join(form_data.keys())
    placeholders = ', '.join(['%s'] * len(form_data))
    values = tuple(form_data.values())

    # Log the columns, placeholders, and values for debugging
    logging.debug(f"Columns: {columns}")
    logging.debug(f"Placeholders: {placeholders}")
    logging.debug(f"Values: {values}")

    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f'INSERT INTO IPs ({columns}) VALUES ({placeholders})', values)
        conn.commit()
        flash('IP added successfully!', 'success')
    except Exception as e:
        logging.error(f"Error adding IP: {e}")
        flash('Error adding IP. Check logs for details.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))

@app.route('/subnet/<int:subnet_id>/ip/<string:ip_address>/edit', methods=['GET', 'POST'])
def edit_ip(subnet_id, ip_address):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        new_status = request.form['status']
        new_owner = request.form['owner']
        is_favorite = 'is_favorite' in request.form
        is_nested = 'is_nested' in request.form
        is_scannable = 'is_scannable' in request.form
        is_resolvable = 'is_resolvable' in request.form
        show_status = 'show_status' in request.form
        is_gateway = request.form.get('is_gateway') == 'on'
        mac = request.form.get('mac')
        description = request.form.get('description')
        note = request.form.get('note')
        switch = request.form.get('switch')
        device = request.form.get('device')
        location = request.form.get('location')
        last_edited = request.form.get('last_edited')
        last_seen = request.form.get('last_seen')

        cursor.execute('''
            UPDATE IPs
            SET status = %s, owner = %s, is_favorite = %s, is_nested = %s, is_scannable = %s, is_resolvable = %s, show_status = %s
            WHERE address = %s AND subnet_id = %s
        ''', (new_status, new_owner, is_favorite, is_nested, is_scannable, is_resolvable, show_status, ip_address, subnet_id))
        
        conn.commit()
        flash('IP details updated successfully!', 'success')
        return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))

    cursor.execute('SELECT * FROM IPs WHERE address = %s AND subnet_id = %s', (ip_address, subnet_id))
    ip = cursor.fetchone()

    conn.close()

    return render_template('edit_ip.html', ip=ip)


@app.route('/subnet/<int:subnet_id>/delete_ip/<ip_address>', methods=['POST'])
def delete_ip(subnet_id, ip_address):
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM IPs WHERE subnet_id = %s AND address = %s', (subnet_id, ip_address))
    conn.commit()
    conn.close()
    return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))





if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')