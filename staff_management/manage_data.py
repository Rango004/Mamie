#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_staff.settings')
django.setup()

from staff.models import School, Department, Staff

def create_sample_data():
    # Create Schools
    school1, _ = School.objects.get_or_create(
        name="School of Engineering",
        code="ENG"
    )
    
    school2, _ = School.objects.get_or_create(
        name="School of Business",
        code="BUS"
    )
    
    school3, _ = School.objects.get_or_create(
        name="School of Arts and Sciences",
        code="AS"
    )
    
    # Create Departments
    Department.objects.get_or_create(
        name="Computer Science",
        code="CS",
        school=school1
    )
    
    Department.objects.get_or_create(
        name="Electrical Engineering",
        code="EE",
        school=school1
    )
    
    Department.objects.get_or_create(
        name="Business Administration",
        code="BA",
        school=school2
    )
    
    Department.objects.get_or_create(
        name="Accounting",
        code="ACC",
        school=school2
    )
    
    Department.objects.get_or_create(
        name="Mathematics",
        code="MATH",
        school=school3
    )
    
    Department.objects.get_or_create(
        name="English Literature",
        code="ENG",
        school=school3
    )
    
    print("Sample data created successfully!")

if __name__ == "__main__":
    create_sample_data()