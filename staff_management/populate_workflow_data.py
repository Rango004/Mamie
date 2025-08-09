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

from staff.models import School, Department, Staff, HRMO, Leave, Promotion
from django.contrib.auth.models import User

def create_workflow_data():
    """Create sample data with workflow features"""
    print("Creating sample data with workflow features...")
    
    # Create Schools
    school1 = School.objects.create(name="School of Engineering", code="ENG")
    school2 = School.objects.create(name="School of Business", code="BUS")
    school3 = School.objects.create(name="School of Arts and Sciences", code="AS")
    
    print(f"Created {School.objects.count()} schools")
    
    # Create Departments
    dept1 = Department.objects.create(name="Computer Science", code="CS", school=school1, department_type="academic")
    dept2 = Department.objects.create(name="Mechanical Engineering", code="ME", school=school1, department_type="academic")
    dept3 = Department.objects.create(name="Business Administration", code="BA", school=school2, department_type="academic")
    dept4 = Department.objects.create(name="Mathematics", code="MATH", school=school3, department_type="academic")
    
    # Administrative Departments
    admin_dept1 = Department.objects.create(name="Human Resources", code="HR", department_type="administrative")
    admin_dept2 = Department.objects.create(name="Finance and Accounting", code="FIN", department_type="administrative")
    sub_dept1 = Department.objects.create(name="Payroll Services", code="PAY", department_type="administrative", parent_department=admin_dept1)
    
    print(f"Created {Department.objects.count()} departments")
    
    # Create Sample Staff with all required fields
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
        }
    ]
    
    # Create staff members
    staff_members = []
    for staff_info in staff_data:
        staff = Staff.objects.create(**staff_info)
        staff_members.append(staff)
    
    print(f"Created {Staff.objects.count()} staff members")
    
    # Create user accounts for staff members
    for staff in staff_members:
        try:
            user = User.objects.create_user(
                username=staff.staff_id,
                email=staff.email,
                first_name=staff.first_name,
                last_name=staff.last_name,
                password='password123'  # Default password
            )
            print(f"Created user account for {staff.full_name}")
        except Exception as e:
            print(f"Error creating user for {staff.full_name}: {e}")
    
    # Create HRMO for Emily Wilson
    emily = Staff.objects.get(staff_id='HR001')
    emily_user = User.objects.get(username='HR001')
    hrmo = HRMO.objects.create(
        user=emily_user,
        staff=emily,
        is_active=True
    )
    print(f"Created HRMO: {hrmo}")
    
    # Create some sample leave applications
    john = Staff.objects.get(staff_id='ENG001')
    sarah = Staff.objects.get(staff_id='ENG002')
    
    # Pending leave application
    leave1 = Leave.objects.create(
        staff=john,
        leave_type='annual',
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=37),
        days_requested=7,
        reason='Family vacation',
        status='pending'
    )
    
    # Approved leave application
    leave2 = Leave.objects.create(
        staff=sarah,
        leave_type='sick',
        start_date=date.today() - timedelta(days=5),
        end_date=date.today() - timedelta(days=3),
        days_requested=3,
        reason='Medical appointment',
        status='approved',
        approved_by=emily_user
    )
    
    print(f"Created {Leave.objects.count()} leave applications")
    
    # Create sample promotion application
    promotion = Promotion.objects.create(
        staff=sarah,
        old_position='Associate Professor',
        new_position='Professor',
        old_department=dept2,
        new_department=dept2,
        old_grade='4',
        new_grade='5',
        effective_date=date.today() + timedelta(days=60),
        status='pending',
        notes='Excellent performance and research contributions'
    )
    
    print(f"Created {Promotion.objects.count()} promotion applications")
    
    print("Sample workflow data creation completed!")
    print("\nLogin credentials:")
    print("Admin: username=admin, password=admin123")
    print("HRMO (Emily Wilson): username=HR001, password=password123")
    print("Staff (John Smith): username=ENG001, password=password123")
    print("Staff (Sarah Johnson): username=ENG002, password=password123")

if __name__ == '__main__':
    create_workflow_data()