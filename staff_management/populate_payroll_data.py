import os
import django
from datetime import date, datetime
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_staff.settings')
django.setup()

from staff.models import (
    Staff, SalaryStructure, PayrollPeriod, Payslip, 
    LeaveBalance, BenefitPlan, StaffBenefit, LoanRecord
)

def populate_payroll_data():
    print("Creating salary structures...")
    
    # Create salary structures for different categories and grades
    salary_data = [
        # Senior Staff
        ('senior', '1', 'full_time', 15000000, 3000000, 1500000, 1000000, 500000),
        ('senior', '2', 'full_time', 12000000, 2500000, 1200000, 800000, 400000),
        ('senior', '3', 'full_time', 10000000, 2000000, 1000000, 600000, 300000),
        ('senior', '4', 'full_time', 8000000, 1800000, 800000, 500000, 200000),
        ('senior', '5', 'full_time', 6000000, 1500000, 600000, 400000, 150000),
        
        # Junior Staff
        ('junior', 'j1', 'full_time', 4000000, 1000000, 400000, 300000, 100000),
        ('junior', 'j2', 'full_time', 3500000, 800000, 350000, 250000, 80000),
        ('junior', 'j3', 'full_time', 3000000, 600000, 300000, 200000, 60000),
        ('junior', 'j4', 'full_time', 2500000, 500000, 250000, 150000, 50000),
        ('junior', 'j5', 'full_time', 2000000, 400000, 200000, 100000, 40000),
        
        # Part-time (50% of full-time)
        ('senior', '3', 'part_time', 5000000, 1000000, 500000, 300000, 150000),
        ('junior', 'j3', 'part_time', 1500000, 300000, 150000, 100000, 30000),
    ]
    
    for category, grade, emp_type, basic, housing, transport, medical, other in salary_data:
        SalaryStructure.objects.get_or_create(
            staff_category=category,
            staff_grade=grade,
            employment_type=emp_type,
            defaults={
                'basic_salary': Decimal(str(basic)),
                'housing_allowance': Decimal(str(housing)),
                'transport_allowance': Decimal(str(transport)),
                'medical_allowance': Decimal(str(medical)),
                'other_allowances': Decimal(str(other)),
            }
        )
    
    print("Creating payroll periods...")
    
    # Create payroll periods
    periods = [
        ('January 2025', date(2025, 1, 1), date(2025, 1, 31)),
        ('February 2025', date(2025, 2, 1), date(2025, 2, 28)),
        ('March 2025', date(2025, 3, 1), date(2025, 3, 31)),
        ('April 2025', date(2025, 4, 1), date(2025, 4, 30)),
        ('May 2025', date(2025, 5, 1), date(2025, 5, 31)),
        ('June 2025', date(2025, 6, 1), date(2025, 6, 30)),
        ('July 2025', date(2025, 7, 1), date(2025, 7, 31)),
        ('August 2025', date(2025, 8, 1), date(2025, 8, 31)),
    ]
    
    for name, start, end in periods:
        PayrollPeriod.objects.get_or_create(
            name=name,
            defaults={
                'start_date': start,
                'end_date': end,
                'is_processed': name in ['January 2025', 'February 2025', 'March 2025']
            }
        )
    
    print("Creating leave balances...")
    
    # Create leave balances for all active staff
    for staff in Staff.objects.filter(status='active'):
        LeaveBalance.objects.get_or_create(
            staff=staff,
            year=2025,
            defaults={
                'annual_leave_balance': 21,
                'sick_leave_balance': 10,
                'maternity_leave_balance': 90 if staff.first_name.lower().endswith('a') else 0,
                'paternity_leave_balance': 7 if not staff.first_name.lower().endswith('a') else 0,
                'emergency_leave_balance': 3,
            }
        )
    
    print("Creating benefit plans...")
    
    # Create benefit plans
    benefits = [
        ('University Health Insurance', 'health', 'Comprehensive health coverage', 500000, 200000, True),
        ('Life Insurance Plan', 'life', 'Life insurance coverage', 100000, 50000, True),
        ('Pension Scheme', 'pension', 'University pension plan', 800000, 400000, True),
        ('Education Allowance', 'education', 'Children education support', 300000, 0, False),
        ('Transport Subsidy', 'transport', 'Monthly transport allowance', 150000, 0, False),
    ]
    
    for name, benefit_type, desc, employer, employee, mandatory in benefits:
        BenefitPlan.objects.get_or_create(
            name=name,
            defaults={
                'benefit_type': benefit_type,
                'description': desc,
                'employer_contribution': Decimal(str(employer)),
                'employee_contribution': Decimal(str(employee)),
                'is_mandatory': mandatory,
            }
        )
    
    print("Enrolling staff in mandatory benefits...")
    
    # Enroll all staff in mandatory benefits
    mandatory_benefits = BenefitPlan.objects.filter(is_mandatory=True)
    for staff in Staff.objects.filter(status='active'):
        for benefit in mandatory_benefits:
            StaffBenefit.objects.get_or_create(
                staff=staff,
                benefit_plan=benefit,
                defaults={
                    'enrollment_date': staff.hire_date,
                }
            )
    
    print("Creating sample loan records...")
    
    # Create some sample loans
    sample_staff = Staff.objects.filter(status='active')[:3]
    loan_types = ['salary_advance', 'emergency', 'housing']
    
    for i, staff in enumerate(sample_staff):
        LoanRecord.objects.get_or_create(
            staff=staff,
            loan_type=loan_types[i],
            defaults={
                'amount': Decimal('2000000'),
                'interest_rate': Decimal('5.0'),
                'repayment_months': 12,
                'monthly_deduction': Decimal('175000'),
                'balance': Decimal('2000000'),
                'status': 'active',
                'approval_date': date(2025, 1, 1),
                'start_deduction_date': date(2025, 2, 1),
                'end_deduction_date': date(2026, 1, 31),
            }
        )
    
    print("Payroll data populated successfully!")
    print(f"Created {SalaryStructure.objects.count()} salary structures")
    print(f"Created {PayrollPeriod.objects.count()} payroll periods")
    print(f"Created {LeaveBalance.objects.count()} leave balances")
    print(f"Created {BenefitPlan.objects.count()} benefit plans")
    print(f"Created {LoanRecord.objects.count()} loan records")

if __name__ == '__main__':
    populate_payroll_data()