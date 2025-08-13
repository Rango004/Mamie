from django import forms
from .models import Staff, Leave, Promotion, Retirement, Bereavement, Department, School, School, HRMO
from django.contrib.auth.models import User

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['staff_id', 'first_name', 'last_name', 'email', 'phone', 'date_of_birth',
                 'address', 'next_of_kin_name', 'next_of_kin_relationship', 'next_of_kin_phone',
                 'next_of_kin_address', 'department', 'position', 'staff_type', 'staff_category',
                 'staff_grade', 'employment_type', 'leadership_role', 'supervisor', 'hire_date', 'contract_start_date',
                 'bank_name', 'bank_account_number', 'bank_sort_code', 'nassit_number', 'highest_qualification', 
                 'institution', 'graduation_year', 'other_qualifications', 'publications', 'photo']
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'graduation_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1950', 'max': '2030'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'staff_id': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'next_of_kin_name': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'staff_type': forms.Select(attrs={'class': 'form-control'}),
            'staff_category': forms.Select(attrs={'class': 'form-control'}),
            'staff_grade': forms.Select(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'leadership_role': forms.Select(attrs={'class': 'form-control'}),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'contract_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_sort_code': forms.TextInput(attrs={'class': 'form-control'}),
            'nassit_number': forms.TextInput(attrs={'class': 'form-control'}),
            'highest_qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'other_qualifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'publications': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contract_start_date'].required = False

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['staff', 'leave_type', 'start_date', 'end_date', 'days_requested', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'days_requested': forms.NumberInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['staff', 'old_position', 'new_position', 'old_department', 
                 'new_department', 'old_grade', 'new_grade', 'effective_date', 'notes']
        widgets = {
            'effective_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'old_position': forms.TextInput(attrs={'class': 'form-control'}),
            'new_position': forms.TextInput(attrs={'class': 'form-control'}),
            'old_department': forms.Select(attrs={'class': 'form-control'}),
            'new_department': forms.Select(attrs={'class': 'form-control'}),
            'old_grade': forms.TextInput(attrs={'class': 'form-control'}),
            'new_grade': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class RetirementForm(forms.ModelForm):
    class Meta:
        model = Retirement
        fields = ['staff', 'retirement_date', 'retirement_type', 'benefits_info', 'notes']
        widgets = {
            'retirement_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'retirement_type': forms.Select(attrs={'class': 'form-control'}),
            'benefits_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class BereavementForm(forms.ModelForm):
    class Meta:
        model = Bereavement
        fields = ['staff', 'deceased_name', 'relationship', 'start_date', 
                 'end_date', 'days_granted']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'deceased_name': forms.TextInput(attrs={'class': 'form-control'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'days_granted': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'school', 'department_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department_type': forms.Select(attrs={'class': 'form-control'}),
        }

class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'school', 'department_type', 'parent_department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department_type': forms.Select(attrs={'class': 'form-control'}),
            'parent_department': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['school'].required = False
        self.fields['parent_department'].required = False

class LeaveApprovalForm(forms.ModelForm):
    """Form for HRMO to approve/reject leave applications"""
    class Meta:
        model = Leave
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Required if rejecting'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [('approved', 'Approve'), ('rejected', 'Reject')]
        self.fields['rejection_reason'].required = False

class PromotionApprovalForm(forms.ModelForm):
    """Form for HRMO to approve/reject promotion applications"""
    class Meta:
        model = Promotion
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Required if rejecting'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [('approved', 'Approve'), ('rejected', 'Reject')]
        self.fields['rejection_reason'].required = False

class StaffLeaveApplicationForm(forms.ModelForm):
    """Simplified form for staff to apply for leave"""
    class Meta:
        model = Leave
        fields = ['leave_type', 'start_date', 'end_date', 'days_requested', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'days_requested': forms.NumberInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class HRMOForm(forms.ModelForm):
    """Form to create/manage HRMO accounts"""
    class Meta:
        model = HRMO
        fields = ['staff', 'is_active']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }