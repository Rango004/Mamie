#!/usr/bin/env python
import os
import sys
import django
from datetime import date, timedelta

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_staff.settings')
django.setup()

from staff.models import School, Department, Staff

def create_sample_data():
    """Create sample schools, departments, and staff"""
    print("Creating sample data...")
    
    # Create Schools
    school1 = School.objects.create(
        name="School of Engineering",
        code="ENG"
    )
    
    school2 = School.objects.create(
        name="School of Business",
        code="BUS"
    )
    
    school3 = School.objects.create(
        name="School of Arts and Sciences",
        code="AS"
    )
    
    print(f"Created {School.objects.count()} schools")
    
    # Create Academic Departments
    dept1 = Department.objects.create(
        name="Computer Science",
        code="CS",
        school=school1,
        department_type="academic"
    )
    
    dept2 = Department.objects.create(
        name="Mechanical Engineering",
        code="ME",
        school=school1,
        department_type="academic"
    )
    
    dept3 = Department.objects.create(
        name="Business Administration",
        code="BA",
        school=school2,
        department_type="academic"
    )
    
    dept4 = Department.objects.create(
        name="Mathematics",
        code="MATH",
        school=school3,
        department_type="academic"
    )
    
    # Create Administrative Departments (no school)
    admin_dept1 = Department.objects.create(
        name="Human Resources",
        code="HR",
        department_type="administrative"
    )
    
    admin_dept2 = Department.objects.create(
        name="Finance and Accounting",
        code="FIN",
        department_type="administrative"
    )
    
    # Create sub-department under HR
    sub_dept1 = Department.objects.create(
        name="Payroll Services",
        code="PAY",
        department_type="administrative",
        parent_department=admin_dept1
    )
    
    print(f"Created {Department.objects.count()} departments")
    
    # Create Sample Staff
    staff_data = [
        {
            'staff_id': 'ENG001',
            'first_name': 'John',
            'last_name': 'Smith',
            'email': 'john.smith@university.edu',
            'phone': '+1234567890',
            'date_of_birth': date(1980, 5, 15),
            'address': '123 University Ave, City, State 12345',
            'next_of_kin_name': 'Jane Smith',
            'next_of_kin_relationship': 'Spouse',
            'next_of_kin_phone': '+1234567891',
            'next_of_kin_address': '123 University Ave, City, State 12345',
            'department': dept1,
            'position': 'Professor',
            'staff_type': 'academic',
            'staff_category': 'senior',
            'staff_grade': '5',
            'hire_date': date(2015, 8, 1),
            'bank_name': 'First National Bank',
            'bank_account_number': '1234567890',
            'bank_sort_code': '123456',
            'nassit_number': 'NS001234567',
            'highest_qualification': 'PhD in Computer Science',
            'institution': 'MIT',
            'graduation_year': 2010,
            'other_qualifications': 'MSc Computer Science, BSc Mathematics',
            'publications': 'Machine Learning Algorithms (2020), AI in Education (2019)'
        },
        {
            'staff_id': 'ENG002',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'email': 'sarah.johnson@university.edu',
            'phone': '+1234567892',
            'date_of_birth': date(1985, 3, 22),
            'address': '456 College St, City, State 12345',
            'next_of_kin_name': 'Michael Johnson',
            'next_of_kin_relationship': 'Spouse',
            'next_of_kin_phone': '+1234567893',
            'next_of_kin_address': '456 College St, City, State 12345',
            'department': dept2,
            'position': 'Associate Professor',
            'staff_type': 'academic',
            'staff_category': 'senior',
            'staff_grade': '4',
            'hire_date': date(2018, 1, 15),
            'bank_name': 'University Credit Union',
            'bank_account_number': '2345678901',
            'bank_sort_code': '234567',
            'nassit_number': 'NS002345678',
            'highest_qualification': 'PhD in Mechanical Engineering',
            'institution': 'Stanford University',
            'graduation_year': 2015,
            'other_qualifications': 'MSc Mechanical Engineering',
            'publications': 'Renewable Energy Systems (2021), Sustainable Engineering (2020)'
        },
        {
            'staff_id': 'BUS001',
            'first_name': 'Robert',
            'last_name': 'Davis',
            'email': 'robert.davis@university.edu',
            'phone': '+1234567894',
            'date_of_birth': date(1975, 11, 8),
            'address': '789 Business Blvd, City, State 12345',
            'next_of_kin_name': 'Linda Davis',
            'next_of_kin_relationship': 'Spouse',
            'next_of_kin_phone': '+1234567895',
            'next_of_kin_address': '789 Business Blvd, City, State 12345',
            'department': dept3,
            'position': 'Department Head',
            'staff_type': 'academic',
            'staff_category': 'senior',
            'staff_grade': '7',
            'hire_date': date(2010, 9, 1),
            'bank_name': 'Business Bank',
            'bank_account_number': '3456789012',
            'bank_sort_code': '345678',
            'nassit_number': 'NS003456789',
            'highest_qualification': 'PhD in Business Administration',
            'institution': 'Harvard Business School',
            'graduation_year': 2005,
            'other_qualifications': 'MBA, BSc Economics',
            'publications': 'Strategic Management (2019), Leadership in Business (2018)'
        },
        {
            'staff_id': 'HR001',
            'first_name': 'Emily',
            'last_name': 'Wilson',
            'email': 'emily.wilson@university.edu',
            'phone': '+1234567896',
            'date_of_birth': date(1990, 7, 12),
            'address': '321 Admin Way, City, State 12345',
            'next_of_kin_name': 'David Wilson',
            'next_of_kin_relationship': 'Brother',
            'next_of_kin_phone': '+1234567897',
            'next_of_kin_address': '654 Family Lane, City, State 12345',
            'department': admin_dept1,
            'position': 'HR Manager',
            'staff_type': 'administrative',
            'staff_category': 'senior_supporting',
            'staff_grade': '8.5',
            'hire_date': date(2020, 3, 1),
            'bank_name': 'Community Bank',
            'bank_account_number': '4567890123',
            'bank_sort_code': '456789',
            'nassit_number': 'NS004567890',
            'highest_qualification': 'MSc Human Resource Management',
            'institution': 'University of London',
            'graduation_year': 2018,
            'other_qualifications': 'BSc Psychology, CIPD Certification',
            'publications': ''
        },
        {
            'staff_id': 'PAY001',
            'first_name': 'Michael',
            'last_name': 'Brown',
            'email': 'michael.brown@university.edu',
            'phone': '+1234567898',
            'date_of_birth': date(1988, 9, 25),
            'address': '987 Payroll Plaza, City, State 12345',
            'next_of_kin_name': 'Susan Brown',
            'next_of_kin_relationship': 'Mother',
            'next_of_kin_phone': '+1234567899',
            'next_of_kin_address': '111 Parent St, City, State 12345',
            'department': sub_dept1,
            'position': 'Payroll Specialist',
            'staff_type': 'administrative',
            'staff_category': 'senior_supporting',
            'staff_grade': '8.2',
            'hire_date': date(2019, 6, 15),
            'bank_name': 'Payroll Bank',
            'bank_account_number': '5678901234',
            'bank_sort_code': '567890',
            'nassit_number': 'NS005678901',
            'highest_qualification': 'BSc Accounting',
            'institution': 'Local University',
            'graduation_year': 2016,
            'other_qualifications': 'Diploma in Payroll Management',
            'publications': ''
        },
        {
            'staff_id': 'SEC001',
            'first_name': 'James',
            'last_name': 'Thompson',
            'email': 'james.thompson@university.edu',
            'phone': '+1234567800',
            'date_of_birth': date(1992, 12, 3),
            'address': '555 Security Lane, City, State 12345',
            'next_of_kin_name': 'Mary Thompson',
            'next_of_kin_relationship': 'Wife',
            'next_of_kin_phone': '+1234567801',
            'next_of_kin_address': '555 Security Lane, City, State 12345',
            'department': admin_dept1,
            'position': 'Security Officer',
            'staff_type': 'support',
            'staff_category': 'junior',
            'staff_grade': 'j4',
            'hire_date': date(2021, 4, 1),
            'bank_name': 'Security Bank',
            'bank_account_number': '6789012345',
            'bank_sort_code': '678901',
            'nassit_number': 'NS006789012',
            'highest_qualification': 'High School Diploma',
            'institution': 'City High School',
            'graduation_year': 2010,
            'other_qualifications': 'Security Training Certificate',
            'publications': ''
        }
    ]
    
    for staff_info in staff_data:
        Staff.objects.create(**staff_info)
    
    print(f"Created {Staff.objects.count()} staff members")
    print("Sample data creation completed!")

if __name__ == '__main__':
    create_sample_data()