import src.db as db  # Assuming your database connection function is in db.py

def get_favorite_subnets():
    # Establish the connection to the database
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Select all details of favorite subnets
    cursor.execute('SELECT * FROM SUBNETS WHERE is_favorite = TRUE')
    favorite_subnets = cursor.fetchall()
    
    # Get the count of favorite subnets
    cursor.execute('SELECT COUNT(*) as count FROM SUBNETS WHERE is_favorite = TRUE')
    count_favorite_subnets = cursor.fetchone()['count']
    
    conn.close()
    
    return favorite_subnets, count_favorite_subnets