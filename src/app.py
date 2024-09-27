from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from src.get_favorite_switch import get_favorite_switch
from src.snmp_switch import * 
from src.switch_data import *
from src.group_interfaces import *
import src.db as db
import logging
import src.subnets as subnets
from ipaddress import ip_network, IPv4Address  
from src.get_favorite_subnets import *
from src.get_favorite_ips import *
from src.ips import *
from flask_bcrypt import Bcrypt
from functools import wraps
from werkzeug.security import *
from collections import defaultdict
import asyncio
from asgiref.wsgi import WsgiToAsgi
from src.subnets import *
import math
import asyncio
# Configure logging
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'supersecretkey'
asgi_app = WsgiToAsgi(app)
bcrypt = Bcrypt(app)
available_ips = None  

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
    favorite_switches, count_favorite_switches = get_favorite_switch()
    num_switches = {'online': online_count, 'offline': offline_count}
    return dict(num_switches=num_switches, favorite_switches=favorite_switches, count_favorite_switches=count_favorite_switches)

def hash_password(plain_password):
    return bcrypt.generate_password_hash(plain_password).decode('utf-8')

# Function to check the password
def check_password(hashed_password, plain_password):
    return bcrypt.check_password_hash(hashed_password, plain_password)

def add_user(username, plain_password, name, lastname, is_admin=False, ro=False):
    hashed_password = hash_password(plain_password)
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO USERS (username, password, name, lastname, ro, is_admin) VALUES (%s, %s, %s, %s, %s, %s)',
        (username, hashed_password, name, lastname, int(ro), int(is_admin))
    )
    conn.commit()
    cursor.close()
    conn.close()


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Check if the logged-in user is an admin
    if not session.get('is_admin'):
        flash('You must be an admin to register new users.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=64)

        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO USERS (username, password, name, lastname) VALUES (%s, %s, %s, %s)', 
                       (username, hashed_password, request.form['name'], request.form['lastname']))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful! User added.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/add-subnet', methods=['GET', 'POST'])
@login_required
def add_subnet():
    if request.method == 'POST':
        data = request.form.to_dict()
        # Add the new subnet to the database
        add_new_subnet(**data)
        flash('Subnet added successfully!', 'success')
        return redirect(url_for('show_subnets'))
    return render_template('add-subnet.html', title='Add Subnet')

@app.route('/scan-ips', methods=['POST'])
@login_required
def scan_ips_route():
    subnet_id = request.form.get('subnet_id')
    logging.info(f"Received request to scan subnet ID: {subnet_id}")
    asyncio.run(scan_ips(subnet_id))
    flash('IP scan completed!', 'success')
    return redirect(url_for('show_subnet_ips', subnet_id=subnet_id) if subnet_id else url_for('index'))

@app.route('/detect-hosts', methods=['POST'])
@login_required
def detect_hosts_route():
    subnet_id = request.form.get('subnet_id')
    logging.info(f"Received request to detect hosts in subnet ID: {subnet_id}")
    asyncio.run(detect_hosts(subnet_id))
    flash('Host detection completed!', 'success')
    return redirect(url_for('show_subnet_ips', subnet_id=subnet_id) if subnet_id else url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM USERS WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            print(user)  # Debug: check what is fetched from the database

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])  # Store admin status in session as boolean
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/')
@login_required
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

@app.route('/collect_snmp_data', methods=['POST'])
@login_required
def collect_snmp_data():
    try:
        # Use asyncio.run() to execute the async function in a synchronous context
        asyncio.run(snmp_switch())  
        flash('SNMP data collected successfully!', 'success')
    except Exception as e:
        logging.error(f"Error collecting SNMP data: {e}")
        flash('Error collecting SNMP data. Check logs for details.', 'danger')
    
    # Ensure the response is returned synchronously
    return redirect(url_for('index'))


async def refresh_snmp_data_for_switch(switch_id):
    conn = await db.get_async_db_connection()
    async with conn.cursor() as cursor:
        # Get the IP address and toggle_SNMP value of the switch
        await cursor.execute('SELECT ip_address, toggle_SNMP FROM SWITCHES WHERE id = %s', (switch_id,))
        switch = await cursor.fetchone()

        if not switch:
            logging.error(f"No switch found with id {switch_id}")
            return

        if switch['toggle_SNMP'] == 0:
            logging.debug(f"SNMP data collection is disabled for switch_id {switch_id}")
            return

        ip = switch['ip_address']

    # Gather SNMP data
    snmp_data = await gather_snmp_data(ip)  # Await the async function

    # Store SNMP data
    await store_snmp_data(switch_id, snmp_data)  # Await the async function

@app.route('/switch/<int:switch_id>')
@login_required
def show_switch(switch_id):
    try:
        # Fetch data for the selected switch using switch_id
        switch_data = get_switch_data(switch_id)
        
        if switch_data:
            # Process interface data as before
            int_names = switch_data['switch']['int_names'].split(',')
            int_status = switch_data['switch']['int_status'].split(',')
            int_shutdown = switch_data['switch']['interface_shutdown_status'].split(',')
            interfaces = [{'name': name, 'status': status, 'shutdown': shutdown} 
                          for name, status, shutdown in zip(int_names, int_status, int_shutdown)]

            # Group interfaces by stack or other criteria if needed
            stack_groups, grouped_interfaces = group_interfaces_by_stack(interfaces)

            # Fetch the specific switch from the database using switch_id
            conn = db.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM SWITCHES WHERE id = %s', (switch_id,))  # Fetch only the selected switch
            switch = cursor.fetchone()  # Get the single switch
            cursor.close()
            conn.close()

            # Render the template with the single switch data
            return render_template(
                'switch.html',
                title=f'Switch {switch_data["switch"].get("hostname", "Unknown")}',
                switch=switch,  # Pass only the current switch
                stack_groups=stack_groups,
                grouped_interfaces=grouped_interfaces
            )
        else:
            flash(f"Switch with ID {switch_id} not found.", 'danger')
            return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"Error showing switch {switch_id}: {e}")
        flash('Error showing switch. Check logs for details.', 'danger')
        return redirect(url_for('index'))
    
@app.route('/subnets')
@login_required
def show_subnets():
    subnets = get_all_subnets()
    return render_template('subnets.html', title='Subnets', subnets=subnets)

@app.route('/subnet/<int:subnet_id>')
@login_required
def show_subnet_ips(subnet_id):
    # Fetch the subnet and IPs information
    subnet, ips = get_ips_for_subnet(subnet_id)
    
    # Create dictionaries for used IPs and their data
    used_ips = {IPv4Address(ip['address']): ip['id'] for ip in ips}
    ip_data = {IPv4Address(ip['address']): ip for ip in ips}
    
    # Calculate available IPs within the subnet range
    subnet_range = ip_network(subnet['range'])
    available_ips = [ip for ip in subnet_range.hosts() if ip not in used_ips]
    
    # Count used and available IPs for the chart
    used_ips_count = len(used_ips)
    available_ips_count = len(available_ips)
    
    # Count IPs by status
    status_counts = {
        'Active': 0,
        'Down': 0,
        'Warning': 0,
        'Unknown': 0
    }
    for ip in ips:
        status = int(ip['status']) if ip['status'] is not None else -1
        if status == 1:
            status_counts['Active'] += 1
        elif status == 0:
            status_counts['Down'] += 1
        elif status == 3:
            status_counts['Warning'] += 1
        else:
            status_counts['Unknown'] += 1

    
    # Add available IPs to the counts
    status_counts['Available'] = available_ips_count
    
    chart_series = [status_counts['Active'], status_counts['Down'], status_counts['Warning'], status_counts['Available']]
    chart_labels = ['Active', 'Down', 'Warning', 'Available']
    chart_colors_list = ['#34d399', '#f87171', '#fbbf24', '#9ca3af']
    
    # Render the template, passing the calculated values to the frontend
    return render_template(
        'ips.html', 
        title=f'IPs in Subnet {subnet["name"]}', 
        subnet=subnet, 
        ips=ips, 
        available_ips=available_ips, 
        used_ips=used_ips,
        ip_data=ip_data,
        subnet_range=subnet_range,
        used_ips_count=used_ips_count, 
        available_ips_count=available_ips_count,
        status_counts=status_counts,
        chart_series=chart_series,
        chart_labels=chart_labels,
        chart_colors_list=chart_colors_list
    )

@app.route('/edit-ip/<int:ip_id>', methods=['GET', 'POST'])
@login_required
def edit_ip(ip_id):
    if request.method == 'POST':
        data = request.form.to_dict()

        # Convert checkbox values to integers (0 or 1)
        data['is_resolvable'] = 1 if 'is_resolvable' in data else 0
        data['is_scannable'] = 1 if 'is_scannable' in data else 0
        data['show_status'] = 1 if 'show_status' in data else 0
        data['is_gateway'] = 1 if 'is_gateway' in data else 0
        data['is_favorite'] = 1 if 'is_favorite' in data else 0

        # Handle 'switch_id' separately
        switch_id = data.get('switch_id', '').strip()
        if switch_id == '':
            data['switch_id'] = None
        else:
            try:
                data['switch_id'] = int(switch_id)
            except ValueError:
                data['switch_id'] = None  # Or handle the error as needed
                logging.warning(f"Invalid switch_id value received: {switch_id}")

        # Handle optional fields
        optional_fields = ['hostname', 'mac', 'description', 'note', 'location', 'port']
        for field in optional_fields:
            if field not in data or data[field].strip() in ('', 'None'):
                data[field] = None

        # Debugging output
        logging.info(f"Updating IP with data: {data}")

        # Update IP and redirect
        update_ip(ip_id, **data)
        flash('IP updated successfully!', 'success')
        return redirect(url_for('show_subnet_ips', subnet_id=data['subnet_id']))

    # Fetch the current IP and available switches
    current_ip = get_ip(ip_id)
    available_ips = get_available_ips(current_ip['subnet_id'])

    # Ensure the current IP address is included in the available IPs
    if current_ip['address'] not in available_ips:
        available_ips.append(current_ip['address'])

    all_switches = get_all_switches()

    # Fetch the latest interface names for the selected switch
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT int_names 
        FROM SNMP_DATA_SWITCH 
        WHERE switch_id = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (current_ip['switch_id'],))
    switch_data = cursor.fetchone()
    cursor.close()
    conn.close()

    interface_names = switch_data['int_names'].split(',') if switch_data else []

    return render_template(
        'edit-ip.html',
        ip=current_ip,
        available_ips=available_ips,
        switches=all_switches,
        interface_names=interface_names
    )

@app.route('/get_interfaces/<int:switch_id>')
def get_interfaces(switch_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT int_names 
        FROM SNMP_DATA_SWITCH 
        WHERE switch_id = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (switch_id,))
    switch_data = cursor.fetchone()
    cursor.close()
    conn.close()

    interface_names = switch_data['int_names'].split(',') if switch_data else []
    return jsonify(interface_names)

@app.route('/edit-subnet/<int:subnet_id>', methods=['GET', 'POST'])
@login_required
def edit_subnet(subnet_id):
    if request.method == 'POST':
        data = request.form.to_dict()
        update_subnet(subnet_id, **data)
        flash('Subnet updated successfully!', 'success')
        return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))
    subnet = get_subnet(subnet_id)
    return render_template('edit-subnet.html', title=f'Edit Subnet {subnet["name"]}', subnet=subnet)

@app.route('/ip/<int:ip_id>')
@login_required
def show_ip(ip_id):
    ip = get_ip(ip_id)
    return render_template('ip.html', title=f'IP {ip["address"]}', ip=ip)


@app.route('/add-ip/<int:subnet_id>', methods=['POST'])
@login_required
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

@app.route('/switches')
@login_required
def show_switches():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Number of switches per page; adjust as needed

    # Search query
    search_query = request.args.get('search', '', type=str).strip()

    # Database connection
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Base query
    base_query = "SELECT * FROM SWITCHES"
    count_query = "SELECT COUNT(*) as count FROM SWITCHES"

    # Parameters for SQL queries
    params = []
    if search_query:
        base_query += " WHERE hostname LIKE %s OR ip_address LIKE %s OR location LIKE %s"
        count_query += " WHERE hostname LIKE %s OR ip_address LIKE %s OR location LIKE %s"
        like_query = f"%{search_query}%"
        params.extend([like_query, like_query, like_query])

    # Execute count query to get total number of switches
    cursor.execute(count_query, params)
    total_switches = cursor.fetchone()['count']
    total_pages = math.ceil(total_switches / per_page) if per_page else 1

    # Calculate offset
    offset = (page - 1) * per_page

    # Append ORDER BY, LIMIT, OFFSET to base query
    base_query += " ORDER BY id ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    # Execute main query to fetch switches for the current page
    cursor.execute(base_query, params)
    switches = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'switches.html',
        switches=switches,
        page=page,
        total_pages=total_pages,
        search_query=search_query
    )


@app.route('/delete_ip/<int:ip_id>', methods=['POST'])
def delete_ip(ip_id):
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM IPs WHERE id = %s', (ip_id,))
        conn.commit()
        flash('IP deleted successfully!', 'success')
    except Exception as e:
        logging.error(f"Error deleting IP ID {ip_id}: {e}")
        conn.rollback()
        flash('Error deleting IP.', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('show_subnet_ips', subnet_id=request.form['subnet_id']))

@app.route('/edit_switch/<int:switch_id>', methods=['POST'])
def edit_switch(switch_id):
    if request.method == 'POST':
        data = request.form.to_dict()

        # Convert checkbox values to integers (0 or 1)
        data['is_online'] = 1 if 'is_online' in data else 0
        data['is_favorite'] = 1 if 'is_favorite' in data else 0

        # Handle optional fields and validation
        required_fields = ['hostname', 'ip_address']
        for field in required_fields:
            if not data.get(field) or data[field].strip() == '':
                flash(f"Error: {field.replace('_', ' ').capitalize()} is required.", 'error')
                return redirect(url_for('show_switch', switch_id=switch_id))

        # Debugging output
        logging.info(f"Updating switch with data: {data}")

        try:
            # Update switch and redirect
            update_switch(switch_id, **data)
            flash('Switch updated successfully!', 'success')
            return redirect(url_for('show_switch', switch_id=switch_id))
        except Exception as e:
            logging.error(f"Error updating switch: {e}")
            flash(f"Error updating switch: {e}", 'error')
            return redirect(url_for('show_switch', switch_id=switch_id))

    # Fetch the current switch
    current_switch = get_switch(switch_id)

    return render_template(
        'edit-switch.html',
        switch=current_switch
    )

@app.route('/add_switch', methods=['POST'])
def add_switch():
    if request.method == 'POST':
        data = request.form.to_dict()

        # Convert checkbox values to integers (0 or 1)
        data['is_online'] = 1 if 'is_online' in data else 0
        data['is_favorite'] = 1 if 'is_favorite' in data else 0

        # Handle optional fields and validation
        required_fields = ['hostname', 'ip_address']
        for field in required_fields:
            if not data.get(field) or data[field].strip() == '':
                flash(f"Error: {field.replace('_', ' ').capitalize()} is required.", 'error')
                return redirect(url_for('show_switches'))

        logging.info(f"Adding switch with data: {data}")

        try:
            # Add switch and redirect
            add_new_switch(**data)
            flash('Switch added successfully!', 'success')
            return redirect(url_for('show_switches'))
        except Exception as e:
            logging.error(f"Error adding switch: {e}")
            flash(f"Error adding switch: {e}", 'error')
            return redirect(url_for('show_switches'))

    return render_template('switches.html')

@app.route('/check_hostname', methods=['POST'])
def check_hostname():
    hostname = request.form.get('hostname')

    if hostname:
        # Use the function to check if the hostname exists
        existing_switch = get_switch_by_hostname(hostname)
        if existing_switch:
            # Return a JSON response indicating the hostname is taken
            return jsonify({'status': 'taken', 'message': 'Hostname already exists'})
        else:
            # Return a JSON response indicating the hostname is available
            return jsonify({'status': 'available', 'message': 'Hostname is available'})
    else:
        # Handle the case where the hostname is empty
        return jsonify({'status': 'error', 'message': 'Hostname cannot be empty'})


@app.route('/delete_switch/<int:switch_id>', methods=['POST'])
def delete_switch(switch_id):
    # Fetch the switch using the ID
    switch = get_switch_by_id(switch_id)  # Make sure you have this helper function

    if not switch:
        flash('Switch not found', 'error')
        return redirect(url_for('show_switches'))

    try:
        # Perform deletion from the database
        delete_switch_by_id(switch_id)
        flash(f'Switch {switch["hostname"]} deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting switch: {e}', 'error')

    return redirect(url_for('show_switches'))

@app.route('/base1')
def base1():
    return render_template('base1.html')

if __name__ == '__main__':
    app.run(debug=True)