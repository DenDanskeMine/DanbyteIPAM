from flask import Flask, render_template, redirect, url_for, flash
from get_favorite_switch import get_favorite_switch
from snmp_switch import snmp_switch, refresh_snmp_data_for_switch   # Import the SNMP functions
from switch_data import get_switch_data  # Import the switch data function
from group_interfaces import group_interfaces_by_stack
  # Import the grouping function
import db  # Assuming you have a db module for database connection
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages

@app.context_processor
def inject_switches():
    # Fetch the count of online and offline switches from the database
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Count online switches
    cursor.execute('SELECT COUNT(*) as count FROM SWITCHES WHERE is_online = TRUE')
    online_count = cursor.fetchone()['count']

    # Count offline switches
    cursor.execute('SELECT COUNT(*) as count FROM SWITCHES WHERE is_online = FALSE')
    offline_count = cursor.fetchone()['count']

    # Close the connection
    cursor.close()
    conn.close()

    # Pass the values to the template
    num_switches = {
        'online': online_count,
        'offline': offline_count,
    }

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

# Project1/app.py
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
        
        flash('Switch not found!', 'danger')
    except KeyError as e:
        logging.error(f"KeyError: {e}")
        flash(f"KeyError: {e}", 'danger')
    except Exception as e:
        logging.error(f"Error fetching switch data: {e}")
        flash('Error fetching switch data. Check logs for details.', 'danger')
    return redirect(url_for('index'))


@app.route('/refresh_status')
def refresh_status():
    # Logic to refresh the status
    return redirect(url_for('show_switch', switch_id=1))  # Adjust as needed



if __name__ == '__main__':
    app.run(debug=True)