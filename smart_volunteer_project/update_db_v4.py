import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '4321', # Update with your MySQL password
    'database': 'smart_volunteer_db'
}

def migrate_v4():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Add attendance column to applications table
        print("Checking applications table for attendance column...")
        cursor.execute("SHOW COLUMNS FROM applications LIKE 'attendance'")
        if not cursor.fetchone():
            print("Adding attendance column to applications...")
            cursor.execute("ALTER TABLE applications ADD COLUMN attendance ENUM('present', 'absent') DEFAULT 'absent'")
        
        # Add certificate_status column to applications table
        print("Checking applications table for certificate_status column...")
        cursor.execute("SHOW COLUMNS FROM applications LIKE 'certificate_status'")
        if not cursor.fetchone():
            print("Adding certificate_status column to applications...")
            cursor.execute("ALTER TABLE applications ADD COLUMN certificate_status ENUM('eligible', 'not_eligible') DEFAULT 'not_eligible'")
        
        conn.commit()
        print("Migration V4 completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate_v4()
