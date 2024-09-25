import src.db as db  # Assuming your database connection function is in db.py

def get_favorite_switch():
    # Establish the connection to the database
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Select all details of favorite switches
    cursor.execute('SELECT * FROM SWITCHES WHERE is_favorite = TRUE')
    favorite_switches = cursor.fetchall()
    
    # Get the count of favorite switches
    cursor.execute('SELECT COUNT(*) as count FROM SWITCHES WHERE is_favorite = TRUE')
    count_favorite_switches = cursor.fetchone()['count']
    
    conn.close()
    
    return favorite_switches, count_favorite_switches