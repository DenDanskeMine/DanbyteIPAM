import db  # Assuming your database connection function is in db.py

def get_all_subnets():
    # Establish a connection to the database
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all subnets
    cursor.execute('SELECT * FROM SUBNETS')
    subnets = cursor.fetchall()

    conn.close()

    return subnets
