import mysql.connector

# Establish the connection to the database
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",  # Adjust if your MariaDB host is different
        user="danbyte_admin",
        password="admin",
        database="DANBYTE"
    )
    return connection

# Example: Function to fetch data from the USERS table
def fetch_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM USERS')
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return users

# Example: Function to fetch data from the SWITCHES table
def fetch_switches():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM SWITCHES')
    switches = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return switches
