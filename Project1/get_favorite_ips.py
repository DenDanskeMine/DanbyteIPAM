import db

def get_favorite_ips():
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM IPs WHERE is_favorite = TRUE")
    favorite_ips = cursor.fetchall()

    # Count the favorite IPs
    cursor.execute("SELECT COUNT(*) as count FROM IPs WHERE is_favorite = TRUE")
    count_favorite_ips = cursor.fetchone()['count']

    conn.close()
    return favorite_ips, count_favorite_ips
