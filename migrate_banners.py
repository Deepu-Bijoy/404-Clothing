import sqlite3
import os

def migrate_database():
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Creating Banner table...")
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS banner (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path VARCHAR(200) NOT NULL,
                title VARCHAR(100),
                subtitle VARCHAR(200),
                button_text VARCHAR(50),
                button_link VARCHAR(200),
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created Banner table")
    except sqlite3.OperationalError as e:
        print(f"Error creating Banner table: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Banner table migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
