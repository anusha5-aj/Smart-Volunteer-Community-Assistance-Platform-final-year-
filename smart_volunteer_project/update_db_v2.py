import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '4321', # Update with your MySQL password
    'database': 'smart_volunteer_db'
}

def migrate_v2():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Add status column to events table
        print("Checking events table for status column...")
        cursor.execute("SHOW COLUMNS FROM events LIKE 'status'")
        if not cursor.fetchone():
            print("Adding status column to events...")
            cursor.execute("ALTER TABLE events ADD COLUMN status ENUM('Open', 'Closed', 'Completed') DEFAULT 'Open'")
        
        # 2. Update status enum in applications table
        print("Updating status enum in applications table...")
        # Note: In MySQL, you usually have to redefine the whole ENUM
        cursor.execute("ALTER TABLE applications MODIFY COLUMN status ENUM('Pending', 'Accepted', 'Rejected', 'Invited') DEFAULT 'Pending'")
        
        # 3. Create notifications table
        print("Creating notifications table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(50) DEFAULT 'info',
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("Migration V2 completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate_v2()
