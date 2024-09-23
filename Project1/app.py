from flask import Flask, render_template, redirect, url_for, flash, request, session
from get_favorite_switch import get_favorite_switch
from snmp_switch import snmp_switch, refresh_snmp_data_for_switch
from switch_data import get_switch_data
from group_interfaces import group_interfaces_by_stack
import db
import ipaddress
import logging
from subnets import get_all_subnets, get_subnet, update_subnet
from ips import get_ips_for_subnet, get_ip, add_ip_to_subnet, update_ip, get_ips_for_availability, scan_and_insert_ip, detect_hosts, scan_ips
from ipaddress import ip_network, IPv4Address  
from get_favorite_subnets import get_favorite_subnets
from get_favorite_ips import get_favorite_ips
from flask_bcrypt import Bcrypt
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
import asyncio
from asgiref.wsgi import WsgiToAsgi
from subnets import add_new_subnet


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'supersecretkey'
asgi_app = WsgiToAsgi(app)

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
        snmp_switch()
        flash('SNMP data collected successfully!', 'success')
    except Exception as e:
        logging.error(f"Error collecting SNMP data: {e}")
        flash('Error collecting SNMP data. Check logs for details.', 'danger')
    return redirect(url_for('index'))

@app.route('/refresh_snmp_data_for_switch/<int:switch_id>')
@login_required
def refresh_snmp_data_for_switch_route(switch_id):
    try:
        refresh_snmp_data_for_switch(switch_id)
        flash('SNMP data refreshed successfully!', 'success')
    except Exception as e:
        logging.error(f"Error refreshing SNMP data for switch {switch_id}: {e}")
        flash('Error refreshing SNMP data. Check logs for details.', 'danger')
    return redirect(url_for('show_switch', switch_id=switch_id))

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


@app.route('/subnet/<int:subnet_id>', methods=['GET', 'POST'])
@login_required
def show_subnet_ips(subnet_id):
    if request.method == 'POST':
        ip_id = request.form.get('ip_id')
        if ip_id:
            data = request.form.to_dict()

            # Convert checkbox values to integers (0 or 1)
            checkbox_fields = ['is_resolvable', 'is_scannable', 'show_status', 'is_gateway', 'is_favorite']
            for field in checkbox_fields:
                data[field] = 1 if field in data else 0

            # Handle 'switch_id' separately
            switch_id = data.get('switch_id', '').strip()
            data['switch_id'] = int(switch_id) if switch_id.isdigit() else None

            # Handle optional fields
            optional_fields = ['hostname', 'mac', 'description', 'note', 'location', 'port']
            for field in optional_fields:
                data[field] = data.get(field) or None

            # Log the data for debugging
            logging.debug(f"Updating IP ID {ip_id} with data: {data}")

            # Update IP in the database
            update_ip(ip_id, **data)
            flash('IP updated successfully!', 'success')
            return redirect(url_for('show_subnet_ips', subnet_id=subnet_id))

    # Handle GET request
    subnet = get_subnet(subnet_id)
    if not subnet:
        flash('Subnet not found.', 'error')
        return redirect(url_for('home'))  # Replace 'home' with your desired route

    ips = get_ips_for_subnet(subnet_id)[1]  # Assuming get_ips_for_subnet returns (subnet, ips)
    used_ips = {str(ipaddress.IPv4Address(ip['address'])): ip['id'] for ip in ips if isinstance(ip, dict)}
    ip_data = {str(ipaddress.IPv4Address(ip['address'])): ip for ip in ips if isinstance(ip, dict)}

    # Fetch available IPs
    subnet_range = ip_network(subnet['range'])
    available_ips = [str(ip) for ip in subnet_range.hosts() if str(ip) not in used_ips]

    # Count statuses
    status_counts = {
        'Active': 0,
        'Down': 0,
        'Warning': 0,
        'Unknown': 0,
        'Available': len(available_ips)
    }
    for ip in ips:
        if isinstance(ip, dict):
            status = int(ip['status']) if ip.get('status') and str(ip['status']).isdigit() else -1
            if status == 1:
                status_counts['Active'] += 1
            elif status == 0:
                status_counts['Down'] += 1
            elif status == 3:
                status_counts['Warning'] += 1
            else:
                status_counts['Unknown'] += 1

    # Prepare chart data
    chart_series = [
        status_counts['Active'],
        status_counts['Down'],
        status_counts['Warning'],
        status_counts['Available']
    ]
    chart_labels = ['Active', 'Down', 'Warning', 'Available']
    chart_colors_list = ['#34d399', '#f87171', '#fbbf24', '#9ca3af']

    switches = get_all_switches()

    return render_template(
        'ips.html',
        title=f'IPs in Subnet {subnet["name"]}',
        subnet=subnet,
        ips=ips,
        available_ips=available_ips,
        used_ips=used_ips,
        ip_data=ip_data,
        subnet_range=subnet_range,
        status_counts=status_counts,
        chart_series=chart_series,
        chart_labels=chart_labels,
        chart_colors_list=chart_colors_list,
        switches=switches,
        ip=None  # Initialize ip as None for the Edit Modal
    )




@app.route('/edit-ip/<int:ip_id>', methods=['POST'])
@login_required
def edit_ip(ip_id):
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
    return render_template(
        'edit-ip.html',
        ip=current_ip,
        available_ips=available_ips,
        switches=all_switches
    )

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
    # Fetch all switches from the database
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM SWITCHES')  # Query to fetch all switches
    switches = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('switches.html', switches=switches)


if __name__ == '__main__':
    app.run(debug=True)