from django.db import models
from django.contrib.auth.models import User
from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.mail import send_mail
from django.conf import settings

class School(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    DEPARTMENT_TYPES = [
        ('academic', 'Academic Department'),
        ('administrative', 'Administrative Department'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=10, unique=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    department_type = models.CharField(max_length=20, choices=DEPARTMENT_TYPES, default='academic')
    parent_department = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_departments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.school:
            return f"{self.name} - {self.school.name}"
        return self.name

class Staff(models.Model):
    STAFF_TYPES = [
        ('academic', 'Academic Staff'),
        ('administrative', 'Administrative Staff'),
        ('support', 'Support Staff'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('retired', 'Retired'),
        ('terminated', 'Terminated'),
    ]
    
    STAFF_CATEGORIES = [
        ('senior', 'Senior Staff'),
        ('senior_supporting', 'Senior Supporting Staff'),
        ('junior', 'Junior Staff'),
    ]
    
    GRADE_CHOICES = [
        # Senior Staff Grades
        ('1', 'Scale 1'),
        ('2', 'Scale 2'),
        ('3', 'Scale 3'),
        ('4', 'Scale 4'),
        ('5', 'Scale 5'),
        ('6', 'Scale 6'),
        ('7', 'Scale 7'),
        ('8.1', 'Scale 8.1'),
        ('8.2', 'Scale 8.2'),
        ('8.3', 'Scale 8.3'),
        ('8.4', 'Scale 8.4'),
        ('8.5', 'Scale 8.5'),
        ('8.6', 'Scale 8.6'),
        ('8.7', 'Scale 8.7'),
        ('8.8', 'Scale 8.8'),
        ('8.9', 'Scale 8.9'),
        ('8.10', 'Scale 8.10'),
        # Junior Staff Grades
        ('j1', 'Junior Scale 1'),
        ('j2', 'Junior Scale 2'),
        ('j3', 'Junior Scale 3'),
        ('j4', 'Junior Scale 4'),
        ('j5', 'Junior Scale 5'),
        ('j6', 'Junior Scale 6'),
        ('j7', 'Junior Scale 7'),
        ('j8', 'Junior Scale 8'),
    ]
    
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('associate', 'Associate'),
        ('beyond_retirement', 'Employment Beyond Retirement'),
    ]
    
    LEADERSHIP_ROLES = [
        ('none', 'No Leadership Role'),
        ('vice_chancellor', 'Vice Chancellor'),
        ('dvc_academic', 'Deputy Vice Chancellor (Academic)'),
        ('dvc_admin', 'Deputy Vice Chancellor (Administration)'),
        ('registrar', 'Registrar'),
        ('bursar', 'Bursar'),
        ('dean', 'Dean of School'),
        ('hod', 'Head of Department'),
        ('director', 'Director'),
        ('coordinator', 'Coordinator'),
        ('unit_head', 'Unit Head'),
        ('librarian', 'Chief Librarian'),
        ('security_head', 'Head of Security'),
        ('maintenance_head', 'Head of Maintenance'),
    ]

    # Basic Information
    staff_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    address = models.TextField()
    
    # Next of Kin Information
    next_of_kin_name = models.CharField(max_length=200)
    next_of_kin_relationship = models.CharField(max_length=100)
    next_of_kin_phone = models.CharField(max_length=15)
    next_of_kin_address = models.TextField()
    
    # Employment Information
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    position = models.CharField(max_length=100)
    staff_type = models.CharField(max_length=20, choices=STAFF_TYPES)
    staff_category = models.CharField(max_length=20, choices=STAFF_CATEGORIES)
    staff_grade = models.CharField(max_length=10, choices=GRADE_CHOICES)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    leadership_role = models.CharField(max_length=30, choices=LEADERSHIP_ROLES, default='none')
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_staff')
    hire_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    contract_start_date = models.DateField(null=True, blank=True, help_text="For contract and associate staff")
    contract_renewal_notification_sent = models.BooleanField(default=False)
    
    # Financial Information
    bank_name = models.CharField(max_length=100)
    bank_account_number = models.CharField(max_length=50)
    bank_sort_code = models.CharField(max_length=20, blank=True)
    nassit_number = models.CharField(max_length=50, unique=True)
    
    # Education and Qualifications
    highest_qualification = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    graduation_year = models.IntegerField()
    other_qualifications = models.TextField(blank=True)
    
    # Publications (for academic staff)
    publications = models.TextField(blank=True, help_text="List of publications, research papers, books, etc.")
    
    # Other
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.staff_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def retirement_date(self):
        """Calculate retirement date based on system settings"""
        settings = SystemSettings.get_settings()
        return self.date_of_birth + relativedelta(years=settings.retirement_age)
    
    @property
    def months_to_retirement(self):
        """Calculate months until retirement"""
        today = date.today()
        retirement_date = self.retirement_date
        if retirement_date <= today:
            return 0
        return (retirement_date.year - today.year) * 12 + (retirement_date.month - today.month)
    
    @property
    def is_retirement_due(self):
        """Check if retirement notification should be sent"""
        settings = SystemSettings.get_settings()
        return self.months_to_retirement <= settings.retirement_notification_months and self.months_to_retirement > 0
    
    @property
    def age(self):
        """Calculate current age"""
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def get_supervisor(self):
        """Get staff supervisor - either assigned supervisor or HOD"""
        if self.supervisor:
            return self.supervisor
        # If no supervisor assigned, find HOD of department
        hod = Staff.objects.filter(department=self.department, leadership_role='hod').first()
        return hod
    
    @property
    def needs_contract_renewal_notification(self):
        """Check if contract renewal notification should be sent"""
        if self.employment_type in ['part_time', 'associate', 'contract']:
            return False  # These types don't get renewal notifications
        
        if not self.contract_start_date:
            contract_date = self.hire_date
        else:
            contract_date = self.contract_start_date
        
        today = date.today()
        years_since_contract = (today - contract_date).days / 365.25
        
        # Check if 2 years or 4 years have passed and notification not sent
        if ((years_since_contract >= 2 and years_since_contract < 2.1 and not self.contract_renewal_notification_sent) or 
           (years_since_contract >= 4 and years_since_contract < 4.1)):
            return True
        return False

class StaffGrade(models.Model):
    """Editable staff grades/scales"""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=[
        ('senior', 'Senior Staff'),
        ('junior', 'Junior Staff'),
        ('supporting', 'Supporting Staff')
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class SystemSettings(models.Model):
    """System-wide settings"""
    retirement_age = models.IntegerField(default=65, help_text="Retirement age in years")
    retirement_notification_months = models.IntegerField(default=6, help_text="Months before retirement to send notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return f"Retirement Age: {self.retirement_age} years"
    
    @classmethod
    def get_settings(cls):
        """Get or create system settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

class Announcement(models.Model):
    """Announcements and letters to staff"""
    ANNOUNCEMENT_TYPES = [
        ('announcement', 'General Announcement'),
        ('letter', 'Official Letter'),
        ('notice', 'Notice'),
        ('memo', 'Memorandum'),
    ]
    
    TARGET_AUDIENCE = [
        ('all', 'All Staff'),
        ('academic', 'Academic Staff'),
        ('administrative', 'Administrative Staff'),
        ('support', 'Support Staff'),
        ('senior', 'Senior Staff'),
        ('junior', 'Junior Staff'),
        ('leadership', 'Leadership Roles'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    announcement_type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPES, default='announcement')
    target_audience = models.CharField(max_length=20, choices=TARGET_AUDIENCE, default='all')
    specific_departments = models.ManyToManyField(Department, blank=True, help_text="Leave empty to target all departments")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    send_email = models.BooleanField(default=False, help_text="Send via email to targeted staff")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_target_audience_display()}"
    
    def get_target_staff(self):
        """Get staff members based on target audience"""
        staff_queryset = Staff.objects.filter(status='active')
        
        if self.target_audience == 'all':
            pass  # Keep all active staff
        elif self.target_audience in ['academic', 'administrative', 'support']:
            staff_queryset = staff_queryset.filter(staff_type=self.target_audience)
        elif self.target_audience in ['senior', 'junior']:
            staff_queryset = staff_queryset.filter(staff_category=self.target_audience)
        elif self.target_audience == 'leadership':
            staff_queryset = staff_queryset.exclude(leadership_role='none')
        
        # Filter by specific departments if selected
        if self.specific_departments.exists():
            staff_queryset = staff_queryset.filter(department__in=self.specific_departments.all())
        
        return staff_queryset

class HRMO(models.Model):
    """Human Resource Management Officer"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"HRMO: {self.staff.full_name}"
    
    class Meta:
        verbose_name = "HRMO"
        verbose_name_plural = "HRMOs"

class Leave(models.Model):
    LEAVE_TYPES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('study', 'Study Leave'),
        ('emergency', 'Emergency Leave'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Supervisor Approval'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'HR Approved'),
        ('rejected', 'Rejected'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    applied_date = models.DateTimeField(auto_now_add=True)
    supervisor_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervisor_approved_leaves')
    supervisor_approved_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_approved_leaves')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.staff.full_name} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
    def send_application_notification(self):
        """Send email notification to HRMOs when leave is applied"""
        hrmos = HRMO.objects.filter(is_active=True)
        hrmo_emails = [hrmo.user.email for hrmo in hrmos if hrmo.user.email]
        
        if hrmo_emails:
            subject = f'New Leave Application - {self.staff.full_name}'
            message = f'''
            A new leave application has been submitted:
            
            Staff: {self.staff.full_name} ({self.staff.staff_id})
            Leave Type: {self.get_leave_type_display()}
            Start Date: {self.start_date}
            End Date: {self.end_date}
            Days Requested: {self.days_requested}
            Reason: {self.reason}
            
            Please log in to the system to review and approve/reject this application.
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                hrmo_emails,
                fail_silently=True,
            )
    
    def send_approval_notification(self):
        """Send email notification to staff when leave is approved/rejected"""
        if self.staff.email:
            if self.status == 'approved':
                subject = 'Leave Application Approved'
                message = f'''
                Dear {self.staff.full_name},
                
                Your leave application has been APPROVED.
                
                Leave Type: {self.get_leave_type_display()}
                Start Date: {self.start_date}
                End Date: {self.end_date}
                Days Approved: {self.days_requested}
                Approved by: {self.approved_by.get_full_name() if self.approved_by else 'HRMO'}
                
                Please ensure proper handover before your leave begins.
                
                Best regards,
                Human Resources
                '''
            else:
                subject = 'Leave Application Rejected'
                message = f'''
                Dear {self.staff.full_name},
                
                Your leave application has been REJECTED.
                
                Leave Type: {self.get_leave_type_display()}
                Start Date: {self.start_date}
                End Date: {self.end_date}
                Reason for Rejection: {self.rejection_reason}
                
                Please contact HR for more information.
                
                Best regards,
                Human Resources
                '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.staff.email],
                fail_silently=True,
            )

class Promotion(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Supervisor Approval'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'HR Approved'),
        ('rejected', 'Rejected'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    old_position = models.CharField(max_length=100)
    new_position = models.CharField(max_length=100)
    old_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='old_promotions')
    new_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='new_promotions')
    old_grade = models.CharField(max_length=10)
    new_grade = models.CharField(max_length=10)
    effective_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    supervisor_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervisor_approved_promotions')
    supervisor_approved_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_approved_promotions')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.full_name} - {self.old_position} to {self.new_position}"
    
    def send_application_notification(self):
        """Send email notification to HRMOs when promotion is submitted"""
        hrmos = HRMO.objects.filter(is_active=True)
        hrmo_emails = [hrmo.user.email for hrmo in hrmos if hrmo.user.email]
        
        if hrmo_emails:
            subject = f'New Promotion Application - {self.staff.full_name}'
            message = f'''
            A new promotion application has been submitted:
            
            Staff: {self.staff.full_name} ({self.staff.staff_id})
            Current Position: {self.old_position}
            Proposed Position: {self.new_position}
            Current Department: {self.old_department.name}
            New Department: {self.new_department.name}
            Effective Date: {self.effective_date}
            
            Please log in to the system to review and approve/reject this promotion.
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                hrmo_emails,
                fail_silently=True,
            )
    
    def send_approval_notification(self):
        """Send email notification to staff when promotion is approved/rejected"""
        if self.staff.email:
            if self.status == 'approved':
                subject = 'Promotion Application Approved'
                message = f'''
                Dear {self.staff.full_name},
                
                Congratulations! Your promotion has been APPROVED.
                
                New Position: {self.new_position}
                New Department: {self.new_department.name}
                New Grade: {self.new_grade}
                Effective Date: {self.effective_date}
                Approved by: {self.approved_by.get_full_name() if self.approved_by else 'HRMO'}
                
                Please report to your new department on the effective date.
                
                Best regards,
                Human Resources
                '''
            else:
                subject = 'Promotion Application Rejected'
                message = f'''
                Dear {self.staff.full_name},
                
                Your promotion application has been REJECTED.
                
                Proposed Position: {self.new_position}
                Reason for Rejection: {self.rejection_reason}
                
                Please contact HR for more information.
                
                Best regards,
                Human Resources
                '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.staff.email],
                fail_silently=True,
            )

class Retirement(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    retirement_date = models.DateField()
    retirement_type = models.CharField(max_length=50, choices=[
        ('voluntary', 'Voluntary'),
        ('mandatory', 'Mandatory'),
        ('early', 'Early Retirement'),
    ])
    benefits_info = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.full_name} - Retirement ({self.retirement_date})"
    
    def send_retirement_notification(self):
        """Send retirement notification to HRMOs and staff"""
        # Send to HRMOs
        hrmos = HRMO.objects.filter(is_active=True)
        hrmo_emails = [hrmo.user.email for hrmo in hrmos if hrmo.user.email]
        
        if hrmo_emails:
            subject = f'Retirement Notification - {self.staff.full_name}'
            message = f'''
            A retirement has been processed:
            
            Staff: {self.staff.full_name} ({self.staff.staff_id})
            Department: {self.staff.department.name}
            Position: {self.staff.position}
            Retirement Date: {self.retirement_date}
            Retirement Type: {self.get_retirement_type_display()}
            
            Please ensure all necessary retirement procedures are completed.
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                hrmo_emails,
                fail_silently=True,
            )
        
        # Send to staff
        if self.staff.email:
            subject = 'Retirement Confirmation'
            message = f'''
            Dear {self.staff.full_name},
            
            Your retirement has been processed with the following details:
            
            Retirement Date: {self.retirement_date}
            Retirement Type: {self.get_retirement_type_display()}
            
            Benefits Information:
            {self.benefits_info}
            
            Please contact HR for any questions regarding your retirement benefits.
            
            Thank you for your years of service to the university.
            
            Best regards,
            Human Resources
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.staff.email],
                fail_silently=True,
            )
        
        self.notification_sent = True
        self.save()

class Bereavement(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    deceased_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    days_granted = models.IntegerField()
    status = models.CharField(max_length=20, choices=[
        ('approved', 'Approved'),
        ('pending', 'Pending'),
    ], default='approved')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.full_name} - Bereavement Leave ({self.deceased_name})"

class WorkflowAction(models.Model):
    """Track workflow actions for audit purposes"""
    ACTION_TYPES = [
        ('leave_applied', 'Leave Applied'),
        ('leave_approved', 'Leave Approved'),
        ('leave_rejected', 'Leave Rejected'),
        ('promotion_applied', 'Promotion Applied'),
        ('promotion_approved', 'Promotion Approved'),
        ('promotion_rejected', 'Promotion Rejected'),
    ]
    
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    staff_affected = models.ForeignKey(Staff, on_delete=models.CASCADE)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Generic foreign key fields
    content_type = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    
    def __str__(self):
        return f"{self.action_type} - {self.staff_affected.full_name} by {self.performed_by.username}"
    
    class Meta:
        ordering = ['-timestamp']

class Notification(models.Model):
    """System notifications for workflow events"""
    NOTIFICATION_TYPES = [
        ('leave_applied', 'Leave Applied'),
        ('leave_approved', 'Leave Approved'),
        ('leave_rejected', 'Leave Rejected'),
        ('promotion_applied', 'Promotion Applied'),
        ('promotion_approved', 'Promotion Approved'),
        ('promotion_rejected', 'Promotion Rejected'),
        ('retirement_processed', 'Retirement Processed'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Generic foreign key fields for linking to different models
    content_type = models.CharField(max_length=50, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    class Meta:
        ordering = ['-created_at']
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, content_type=None, object_id=None):
        """Helper method to create notifications"""
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            content_type=content_type,
            object_id=object_id
        )