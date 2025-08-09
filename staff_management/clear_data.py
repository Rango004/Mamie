#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_staff.settings')
django.setup()

from staff.models import Staff, Leave, Promotion, Retirement, Bereavement, Department, School

def clear_all_data():
    """Clear all data from the database"""
    print("Clearing all data from the database...")
    
    # Delete in order to avoid foreign key constraints
    print("Deleting Bereavements...")
    Bereavement.objects.all().delete()
    
    print("Deleting Retirements...")
    Retirement.objects.all().delete()
    
    print("Deleting Promotions...")
    Promotion.objects.all().delete()
    
    print("Deleting Leaves...")
    Leave.objects.all().delete()
    
    print("Deleting Staff...")
    Staff.objects.all().delete()
    
    print("Deleting Departments...")
    Department.objects.all().delete()
    
    print("Deleting Schools...")
    School.objects.all().delete()
    
    print("All data cleared successfully!")

if __name__ == '__main__':
    clear_all_data()