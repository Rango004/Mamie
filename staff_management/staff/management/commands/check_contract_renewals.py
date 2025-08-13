from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from staff.models import Staff, HRMO
from datetime import date


class Command(BaseCommand):
    help = 'Check and send contract renewal notifications for eligible staff'

    def handle(self, *args, **options):
        staff_needing_renewal = Staff.objects.filter(status='active')
        renewal_due = [staff for staff in staff_needing_renewal if staff.needs_contract_renewal_notification]
        
        notifications_sent = 0
        
        for staff in renewal_due:
            self.send_contract_renewal_notification(staff)
            notifications_sent += 1
            self.stdout.write(
                self.style.SUCCESS(f'Sent contract renewal notification to {staff.full_name}')
            )
        
        if notifications_sent == 0:
            self.stdout.write(
                self.style.SUCCESS('No contract renewal notifications needed at this time.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent {notifications_sent} contract renewal notifications.')
            )

    def send_contract_renewal_notification(self, staff):
        """Send contract renewal notification to staff and HRMO"""
        contract_date = staff.contract_start_date if staff.contract_start_date else staff.hire_date
        today = date.today()
        years_since_contract = int((today - contract_date).days / 365.25)
        
        # Send to staff
        if staff.email:
            subject = 'Contract Renewal Notification'
            message = f'''
Dear {staff.full_name},

This is to notify you that your employment contract is due for renewal.

Contract Start Date: {contract_date}
Years of Service: {years_since_contract} years
Employment Type: {staff.get_employment_type_display()}

Please contact HR to discuss your contract renewal.

Best regards,
Human Resources
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [staff.email],
                fail_silently=True,
            )
        
        # Send to HRMOs
        hrmos = HRMO.objects.filter(is_active=True)
        hrmo_emails = [hrmo.user.email for hrmo in hrmos if hrmo.user.email]
        
        if hrmo_emails:
            subject = f'Staff Contract Renewal Due - {staff.full_name}'
            message = f'''
Staff contract renewal notification:

Staff: {staff.full_name} ({staff.staff_id})
Department: {staff.department.name}
Position: {staff.position}
Employment Type: {staff.get_employment_type_display()}
Contract Start Date: {contract_date}
Years of Service: {years_since_contract} years

Please initiate contract renewal procedures.
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                hrmo_emails,
                fail_silently=True,
            )
        
        # Mark notification as sent
        staff.contract_renewal_notification_sent = True
        staff.save()