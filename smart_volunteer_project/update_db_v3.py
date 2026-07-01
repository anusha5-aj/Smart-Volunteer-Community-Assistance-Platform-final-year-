import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '4321', # Update with your MySQL password
    'database': 'smart_volunteer_db'
}

def migrate():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        print("Checking events table for timing and capacity columns...")
        
        # Add start_time
        cursor.execute("SHOW COLUMNS FROM events LIKE 'start_time'")
        if not cursor.fetchone():
            print("Adding start_time column to events...")
            cursor.execute("ALTER TABLE events ADD COLUMN start_time TIME")
            
        # Add end_time
        cursor.execute("SHOW COLUMNS FROM events LIKE 'end_time'")
        if not cursor.fetchone():
            print("Adding end_time column to events...")
            cursor.execute("ALTER TABLE events ADD COLUMN end_time TIME")
            
        # Add volunteer_limit
        cursor.execute("SHOW COLUMNS FROM events LIKE 'volunteer_limit'")
        if not cursor.fetchone():
            print("Adding volunteer_limit column to events...")
            # Using INT for capacity, default to 0 or NULL if not specified
            cursor.execute("ALTER TABLE events ADD COLUMN volunteer_limit INT DEFAULT 0")
        
        conn.commit()
        print("Schema update completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
