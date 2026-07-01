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
        
        # Add description to ngos if not exists
        print("Checking ngos table...")
        cursor.execute("SHOW COLUMNS FROM ngos LIKE 'description'")
        if not cursor.fetchone():
            print("Adding description column to ngos...")
            cursor.execute("ALTER TABLE ngos ADD COLUMN description TEXT")
        
        # Add avatar_url, experience, availability to volunteers if not exists
        print("Checking volunteers table...")
        cursor.execute("SHOW COLUMNS FROM volunteers LIKE 'avatar_url'")
        if not cursor.fetchone():
            print("Adding avatar_url column to volunteers...")
            cursor.execute("ALTER TABLE volunteers ADD COLUMN avatar_url VARCHAR(255)")
            
        cursor.execute("SHOW COLUMNS FROM volunteers LIKE 'experience'")
        if not cursor.fetchone():
            print("Adding experience column to volunteers...")
            cursor.execute("ALTER TABLE volunteers ADD COLUMN experience TEXT")
            
        cursor.execute("SHOW COLUMNS FROM volunteers LIKE 'availability'")
        if not cursor.fetchone():
            print("Adding availability column to volunteers...")
            cursor.execute("ALTER TABLE volunteers ADD COLUMN availability VARCHAR(100)")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
