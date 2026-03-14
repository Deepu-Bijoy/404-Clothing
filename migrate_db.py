"""
Database migration script to add order tracking fields
Run this once to update the database with new columns
"""
import sqlite3
import os

def migrate_database():
    # Path to database
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Adding new columns to Order table...")
    
    try:
        # Add tracking_number column
        cursor.execute('ALTER TABLE "order" ADD COLUMN tracking_number VARCHAR(50)')
        print("✓ Added tracking_number column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("- tracking_number column already exists")
        else:
            print(f"Error adding tracking_number: {e}")
    
    try:
        # Add dispatch_date column
        cursor.execute('ALTER TABLE "order" ADD COLUMN dispatch_date DATETIME')
        print("✓ Added dispatch_date column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("- dispatch_date column already exists")
        else:
            print(f"Error adding dispatch_date: {e}")
    
    try:
        # Add estimated_delivery_date column
        cursor.execute('ALTER TABLE "order" ADD COLUMN estimated_delivery_date DATETIME')
        print("✓ Added estimated_delivery_date column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("- estimated_delivery_date column already exists")
        else:
            print(f"Error adding estimated_delivery_date: {e}")
    
    try:
        # Add delivered_date column
        cursor.execute('ALTER TABLE "order" ADD COLUMN delivered_date DATETIME')
        print("✓ Added delivered_date column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("- delivered_date column already exists")
        else:
            print(f"Error adding delivered_date: {e}")

    try:
        # Add shipping_fee column
        cursor.execute('ALTER TABLE "order" ADD COLUMN shipping_fee FLOAT DEFAULT 50.0')
        print("✓ Added shipping_fee column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("- shipping_fee column already exists")
        else:
            print(f"Error adding shipping_fee: {e}")

    try:
        # Add is_featured column to product
        cursor.execute('ALTER TABLE product ADD COLUMN is_featured BOOLEAN DEFAULT 0')
        print("✓ Added is_featured column to product")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("- is_featured column already exists")
        else:
            print(f"Error adding is_featured: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database migration completed successfully!")
    print("You can now restart your Flask application.")

if __name__ == "__main__":
    migrate_database()
