import mysql.connector
import aiomysql


# Establish synchronous connection to the database
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",  # Adjust if your MariaDB host is different
        user="danbyte_admin",
        password="admin",
        database="DANBYTE"
    )
    return connection

# Establish asynchronous connection to the database using aiomysql
async def get_async_db_connection():
    connection = await aiomysql.connect(
        host="localhost",  # Adjust if your MariaDB host is different
        user="danbyte_admin",
        password="admin",
        db="DANBYTE"
    )
    return connection

# Example: Synchronous function to fetch users
def fetch_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM USERS')
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return users

# Example: Synchronous function to fetch switches
async def fetch_switches():
    conn = await get_async_db_connection()
    cursor = await conn.cursor()  # Remove 'dictionary=True'

    # Execute the query
    await cursor.execute('SELECT * FROM SWITCHES')
    
    # Fetch all rows
    switches = await cursor.fetchall()
    
    # Manually convert to dictionary
    columns = [col[0] for col in cursor.description]  # Get column names
    switches_dict = [dict(zip(columns, switch)) for switch in switches]  # Convert rows to dict

    # Close the cursor and connection
    await cursor.close()
    conn.close()

    # Return the result as a list of dictionaries
    return switches_dict


# Example: Asynchronous function to fetch users
async def fetch_async_users():
    conn = await get_async_db_connection()
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute('SELECT * FROM USERS')
        users = await cursor.fetchall()
    conn.close()
    return users

# Example: Asynchronous function to fetch switches
async def fetch_async_switches():
    conn = await get_async_db_connection()
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute('SELECT * FROM SWITCHES')
        switches = await cursor.fetchall()
    conn.close()
    return switches
