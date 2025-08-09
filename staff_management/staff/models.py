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
    hire_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
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
        """Calculate retirement date as date of birth + 65 years"""
        return self.date_of_birth + relativedelta(years=65)
    
    @property
    def age(self):
        """Calculate current age"""
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

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
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
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
        ('pending', 'Pending'),
        ('approved', 'Approved'),
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_promotions')
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