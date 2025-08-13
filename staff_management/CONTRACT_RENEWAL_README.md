# Employment Types and Contract Renewal System

## Overview
The staff management system now includes employment types and automated contract renewal notifications.

## Employment Types
The following employment types are available:

1. **Full Time** - Regular full-time employees
2. **Part Time** - Part-time employees
3. **Contract** - Contract-based employees
4. **Associate** - Associate staff members
5. **Employment Beyond Retirement** - Staff working beyond retirement age

## Contract Renewal Notifications

### Who Receives Notifications
- **Full Time** staff receive renewal notifications after 2 and 4 years
- **Employment Beyond Retirement** staff receive renewal notifications after 2 and 4 years
- **Part Time**, **Associate**, and **Contract** staff do NOT receive automatic renewal notifications

### Notification Schedule
- **2 Years**: First renewal notification sent
- **4 Years**: Second renewal notification sent

### How It Works
1. The system calculates years of service from either:
   - Contract Start Date (if specified)
   - Hire Date (if no contract start date)

2. Notifications are sent to:
   - The staff member via email
   - All active HRMOs via email

3. After sending, the system marks the notification as sent to prevent duplicates

## Usage

### Via Web Interface
1. Login as HRMO/Admin
2. Navigate to "Contract Renewals" in the sidebar
3. Click "Check Contract Renewals" to manually check and send notifications

### Via Management Command
Run the following command to check and send contract renewal notifications:

```bash
python manage.py check_contract_renewals
```

This command can be scheduled to run automatically using:
- Windows Task Scheduler
- Cron jobs (Linux/Mac)
- Django-cron or Celery for automated scheduling

### Dashboard Integration
- The dashboard shows staff requiring contract renewal notifications
- HRMO/Admin users can see contract renewal alerts alongside retirement notifications

## Database Fields Added
- `employment_type`: CharField with employment type choices
- `contract_start_date`: DateField (optional, defaults to hire_date)
- `contract_renewal_notification_sent`: BooleanField to track notification status

## Migration
The system includes migration `0006_add_employment_type_and_contract_fields.py` which adds the new fields to existing staff records with default values.

## Email Configuration
Ensure your Django settings include proper email configuration for notifications to work:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'hr@university.edu'
```

## Security Notes
- Only HRMO and Admin users can access contract renewal functions
- Email notifications are sent with `fail_silently=True` to prevent system errors
- Staff can only view their own contract information