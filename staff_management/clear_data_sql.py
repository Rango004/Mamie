#!/usr/bin/env python
import os
import sys
import django
import sqlite3

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_staff.settings')
django.setup()

from django.db import connection

def clear_all_data_sql():
    """Clear all data using raw SQL"""
    print("Clearing all data using SQL...")
    
    with connection.cursor() as cursor:
        # Disable foreign key checks
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'django_%' AND name NOT LIKE 'auth_%';")
        tables = cursor.fetchall()
        
        # Delete data from all tables
        for table in tables:
            table_name = table[0]
            print(f"Clearing table: {table_name}")
            cursor.execute(f"DELETE FROM {table_name};")
        
        # Re-enable foreign key checks
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        print("All data cleared successfully!")

if __name__ == '__main__':
    clear_all_data_sql()