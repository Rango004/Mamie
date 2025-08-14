from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.conf import settings
from .models import Staff, Department, School, Leave, Promotion, Retirement, Bereavement, HRMO
from datetime import date
from .forms import StaffForm, LeaveForm, PromotionForm, RetirementForm, BereavementForm, SchoolForm, DepartmentForm
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import csv
from datetime import datetime
import qrcode
from io import BytesIO
from PIL import Image

@login_required
def dashboard(request):
    # Check if user is HRMO or superuser
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if is_hrmo:
        # Full dashboard for HRMO/Admin
        total_staff = Staff.objects.filter(status='active').count()
        total_departments = Department.objects.count()
        total_schools = School.objects.count()
        pending_leaves = Leave.objects.filter(status__in=['pending', 'supervisor_approved']).count()
        
        staff_by_dept = Department.objects.annotate(
            staff_count=Count('staff', filter=Q(staff__status='active'))
        ).order_by('-staff_count')[:5]
        
        # Leadership roles summary
        leadership_roles_raw = Staff.objects.filter(
            status='active'
        ).exclude(
            leadership_role='none'
        ).values(
            'leadership_role'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Format leadership roles for display
        leadership_roles = []
        for role in leadership_roles_raw:
            role_display = role['leadership_role'].replace('_', ' ').title()
            leadership_roles.append({
                'leadership_role': role['leadership_role'],
                'leadership_role_display': role_display,
                'count': role['count']
            })
        
        recent_leaves = Leave.objects.select_related('staff').order_by('-applied_date')[:5]
        recent_promotions = Promotion.objects.select_related('staff').order_by('-created_at')[:5]
        
        # Get staff due for retirement
        staff_due_retirement = Staff.objects.filter(status='active')
        retirement_due = [staff for staff in staff_due_retirement if staff.is_retirement_due][:5]
        
        # Get staff needing contract renewal notifications
        staff_needing_renewal = Staff.objects.filter(status='active')
        contract_renewals_due = [staff for staff in staff_needing_renewal if staff.needs_contract_renewal_notification][:5]
        
        context = {
            'total_staff': total_staff,
            'total_departments': total_departments,
            'total_schools': total_schools,
            'pending_leaves': pending_leaves,
            'staff_by_dept': staff_by_dept,
            'leadership_roles': leadership_roles,
            'recent_leaves': recent_leaves,
            'recent_promotions': recent_promotions,
            'retirement_due': retirement_due,
            'contract_renewals_due': contract_renewals_due,
        }
    else:
        # Limited dashboard for regular staff
        try:
            staff = Staff.objects.get(email=request.user.email)
            my_leaves = Leave.objects.filter(staff=staff).order_by('-applied_date')[:5]
            my_promotions = Promotion.objects.filter(staff=staff).order_by('-created_at')[:3]
            pending_leaves = Leave.objects.filter(staff=staff, status__in=['pending', 'supervisor_approved']).count()
            
            # Check if user is a supervisor
            supervised_leaves = Leave.objects.filter(staff__supervisor=staff, status='pending').count()
            supervised_promotions = Promotion.objects.filter(staff__supervisor=staff, status='pending').count()
            
            context = {
                'staff': staff,
                'my_leaves': my_leaves,
                'my_promotions': my_promotions,
                'pending_leaves': pending_leaves,
                'supervised_leaves': supervised_leaves,
                'supervised_promotions': supervised_promotions,
                'is_staff_view': True,
            }
        except Staff.DoesNotExist:
            messages.error(request, 'Staff record not found. Please contact HR.')
            context = {'is_staff_view': True}
    
    return render(request, 'staff/dashboard.html', context)

@login_required
def staff_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    staff = Staff.objects.select_related('department__school').filter(status='active')
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    return render(request, 'staff/staff_list.html', {'staff': staff, 'is_hrmo': is_hrmo})

@login_required
def staff_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        
        # Validate photo if uploaded
        if request.FILES.get('photo'):
            photo = request.FILES['photo']
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            max_size = 1 * 1024 * 1024  # 1MB
            
            if photo.content_type not in allowed_types:
                messages.error(request, 'Only JPEG, PNG, and GIF images are allowed for photos.')
                return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Add Staff'})
            
            if photo.size > max_size:
                messages.error(request, 'Photo file size must be less than 1MB.')
                return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Add Staff'})
        
        if form.is_valid():
            try:
                staff = form.save()
                messages.success(request, f'Staff member {staff.full_name} added successfully!')
                return redirect('staff_list')
            except Exception as e:
                print(f"Error saving staff: {e}")
                messages.error(request, f'Error saving staff member: {str(e)}')
        else:
            print(f"Form validation errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = StaffForm()
    return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Add Staff'})

@login_required
def staff_update(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, pk=pk)
    
    # Handle HRMO assignment/removal
    if request.method == 'POST' and request.POST.get('hrmo_action'):
        action = request.POST.get('hrmo_action')
        if action == 'assign':
            try:
                user, created = User.objects.get_or_create(
                    email=staff.email,
                    defaults={
                        'username': staff.staff_id,
                        'first_name': staff.first_name,
                        'last_name': staff.last_name
                    }
                )
                HRMO.objects.create(user=user, staff=staff)
                messages.success(request, f'{staff.full_name} assigned as HRMO successfully!')
            except Exception as e:
                messages.error(request, f'Error assigning HRMO: {str(e)}')
        elif action == 'toggle':
            try:
                hrmo = HRMO.objects.get(staff=staff)
                hrmo.is_active = not hrmo.is_active
                hrmo.save()
                status = 'activated' if hrmo.is_active else 'deactivated'
                messages.success(request, f'HRMO status {status} for {staff.full_name}!')
            except HRMO.DoesNotExist:
                messages.error(request, 'HRMO record not found.')
        return redirect('staff_update', pk=pk)
    
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff)
        
        # Validate photo if uploaded
        if request.FILES.get('photo'):
            photo = request.FILES['photo']
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            max_size = 1 * 1024 * 1024  # 1MB
            
            if photo.content_type not in allowed_types:
                messages.error(request, 'Only JPEG, PNG, and GIF images are allowed for photos.')
                return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Update Staff'})
            
            if photo.size > max_size:
                messages.error(request, 'Photo file size must be less than 1MB.')
                return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Update Staff'})
        
        if form.is_valid():
            try:
                updated_staff = form.save()
                messages.success(request, f'Staff member {updated_staff.full_name} updated successfully!')
                return redirect('staff_list')
            except Exception as e:
                print(f"Error updating staff: {e}")
                messages.error(request, f'Error updating staff member: {str(e)}')
        else:
            print(f"Form validation errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = StaffForm(instance=staff)
    
    # Check if staff has HRMO role
    try:
        hrmo = HRMO.objects.get(staff=staff)
    except HRMO.DoesNotExist:
        hrmo = None
    
    is_admin_or_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    return render(request, 'staff/staff_form.html', {
        'form': form, 
        'title': 'Update Staff',
        'hrmo': hrmo,
        'is_admin_or_hrmo': is_admin_or_hrmo
    })

@login_required
def staff_delete(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        staff.delete()
        messages.success(request, 'Staff member deleted successfully!')
        return redirect('staff_list')
    return render(request, 'staff/staff_confirm_delete.html', {'staff': staff})

@login_required
def leave_list(request):
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if is_hrmo:
        leaves = Leave.objects.select_related('staff').order_by('-applied_date')
    else:
        # Regular staff can only see their own leaves
        try:
            staff = Staff.objects.get(email=request.user.email)
            leaves = Leave.objects.filter(staff=staff).order_by('-applied_date')
        except Staff.DoesNotExist:
            messages.error(request, 'Staff record not found.')
            return redirect('dashboard')
    
    return render(request, 'staff/leave_list.html', {'leaves': leaves, 'is_hrmo': is_hrmo})

@login_required
def leave_create(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            # If not HRMO, set staff to current user's staff record
            if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
                try:
                    staff = Staff.objects.get(email=request.user.email)
                    leave.staff = staff
                except Staff.DoesNotExist:
                    messages.error(request, 'Staff record not found.')
                    return redirect('dashboard')
            leave.save()
            messages.success(request, 'Leave application submitted successfully!')
            return redirect('leave_list')
    else:
        form = LeaveForm()
        # If not HRMO, hide staff field
        if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
            form.fields.pop('staff', None)
    
    return render(request, 'staff/leave_form.html', {'form': form, 'title': 'Apply for Leave'})

@login_required
def promotion_list(request):
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if is_hrmo:
        promotions = Promotion.objects.select_related('staff').order_by('-created_at')
    else:
        # Regular staff can only see their own promotions
        try:
            staff = Staff.objects.get(email=request.user.email)
            promotions = Promotion.objects.filter(staff=staff).order_by('-created_at')
        except Staff.DoesNotExist:
            messages.error(request, 'Staff record not found.')
            return redirect('dashboard')
    
    return render(request, 'staff/promotion_list.html', {'promotions': promotions, 'is_hrmo': is_hrmo})

@login_required
def promotion_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            try:
                promotion = form.save(commit=False)
                promotion.status = 'approved'  # Auto-approve for HRMO
                promotion.approved_by = request.user
                promotion.approved_date = datetime.now()
                promotion.save()
                
                # Update staff position, department, and grade
                staff = promotion.staff
                staff.position = promotion.new_position
                staff.department = promotion.new_department
                staff.staff_grade = promotion.new_grade
                staff.save()
                
                messages.success(request, f'Promotion for {staff.full_name} processed successfully!')
                return redirect('promotion_list')
            except Exception as e:
                print(f"Error processing promotion: {e}")
                messages.error(request, f'Error processing promotion: {str(e)}')
        else:
            print(f"Promotion form validation errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PromotionForm()
    return render(request, 'staff/promotion_form.html', {'form': form, 'title': 'Process Promotion'})

@login_required
def retirement_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    retirements = Retirement.objects.select_related('staff').order_by('-created_at')
    return render(request, 'staff/retirement_list.html', {'retirements': retirements})

@login_required
def retirement_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RetirementForm(request.POST)
        if form.is_valid():
            retirement = form.save()
            # Update staff status
            staff = retirement.staff
            staff.status = 'retired'
            staff.save()
            messages.success(request, f'Retirement for {staff.full_name} processed successfully!')
            return redirect('retirement_list')
    else:
        form = RetirementForm()
        
    # Get staff due for retirement for dropdown
    from .models import SystemSettings
    staff_due_retirement = Staff.objects.filter(status='active')
    retirement_due = [staff for staff in staff_due_retirement if staff.is_retirement_due]
    return render(request, 'staff/retirement_form.html', {
        'form': form, 
        'title': 'Process Retirement',
        'retirement_due': retirement_due
    })

@login_required
def bereavement_list(request):
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if is_hrmo:
        bereavements = Bereavement.objects.select_related('staff').order_by('-created_at')
    else:
        # Regular staff can only see their own bereavement records
        try:
            staff = Staff.objects.get(email=request.user.email)
            bereavements = Bereavement.objects.filter(staff=staff).order_by('-created_at')
        except Staff.DoesNotExist:
            messages.error(request, 'Staff record not found.')
            return redirect('dashboard')
    
    return render(request, 'staff/bereavement_list.html', {'bereavements': bereavements})

@login_required
def bereavement_create(request):
    if request.method == 'POST':
        form = BereavementForm(request.POST)
        if form.is_valid():
            bereavement = form.save(commit=False)
            # If not HRMO, set staff to current user's staff record
            if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
                try:
                    staff = Staff.objects.get(email=request.user.email)
                    bereavement.staff = staff
                except Staff.DoesNotExist:
                    messages.error(request, 'Staff record not found.')
                    return redirect('dashboard')
            bereavement.save()
            messages.success(request, 'Bereavement leave recorded successfully!')
            return redirect('bereavement_list')
    else:
        form = BereavementForm()
        # If not HRMO, hide staff field
        if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
            form.fields.pop('staff', None)
    
    return render(request, 'staff/bereavement_form.html', {'form': form, 'title': 'Record Bereavement Leave'})

@login_required
def my_profile(request):
    try:
        staff = Staff.objects.get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found. Please contact HR.')
        return redirect('dashboard')
    
    return render(request, 'staff/my_profile.html', {'staff': staff})

@login_required
def print_id_card(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    
    # Check if user can access this staff's ID card
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        try:
            user_staff = Staff.objects.get(email=request.user.email)
            if user_staff != staff:
                messages.error(request, 'Access denied.')
                return redirect('dashboard')
        except Staff.DoesNotExist:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
    
    # Create PDF - Standard ID card size (3.375" x 2.125")
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(3.375*72, 2.125*72))
    
    # Blue header background
    p.setFillColorRGB(0.1, 0.3, 0.6)  # Dark blue
    p.rect(0, 120, 3.375*72, 33, fill=1)
    
    # University name in header
    p.setFillColorRGB(1, 1, 1)  # White text
    p.setFont("Helvetica-Bold", 11)
    text_width = p.stringWidth("UNIVERSITY OF SIERRA LEONE", "Helvetica-Bold", 11)
    p.drawString((3.375*72 - text_width)/2, 135, "UNIVERSITY OF SIERRA LEONE")
    p.setFont("Helvetica", 8)
    text_width = p.stringWidth("STAFF IDENTIFICATION CARD", "Helvetica", 8)
    p.drawString((3.375*72 - text_width)/2, 125, "STAFF IDENTIFICATION CARD")
    
    # White background for main content
    p.setFillColorRGB(1, 1, 1)
    p.rect(0, 0, 3.375*72, 120, fill=1)
    
    # Photo section
    if staff.photo:
        try:
            # Draw actual photo
            p.drawImage(staff.photo.path, 15, 65, width=55, height=45, preserveAspectRatio=True, mask='auto')
        except:
            # Fallback to placeholder if photo can't be loaded
            p.setFillColorRGB(0.95, 0.95, 0.95)
            p.rect(15, 65, 55, 45, fill=1)
            p.setStrokeColorRGB(0.7, 0.7, 0.7)
            p.rect(15, 65, 55, 45, fill=0)
            p.setFillColorRGB(0.5, 0.5, 0.5)
            p.setFont("Helvetica", 8)
            text_width = p.stringWidth("NO PHOTO", "Helvetica", 8)
            p.drawString(42.5 - text_width/2, 85, "NO PHOTO")
    else:
        # Photo placeholder with border
        p.setFillColorRGB(0.95, 0.95, 0.95)
        p.rect(15, 65, 55, 45, fill=1)
        p.setStrokeColorRGB(0.7, 0.7, 0.7)
        p.rect(15, 65, 55, 45, fill=0)
        p.setFillColorRGB(0.5, 0.5, 0.5)
        p.setFont("Helvetica", 8)
        text_width = p.stringWidth("NO PHOTO", "Helvetica", 8)
        p.drawString(42.5 - text_width/2, 85, "NO PHOTO")
    
    # Staff details
    p.setFillColorRGB(0, 0, 0)  # Black text
    p.setFont("Helvetica-Bold", 10)
    p.drawString(80, 100, staff.full_name.upper())
    
    p.setFont("Helvetica", 8)
    p.drawString(80, 88, f"ID: {staff.staff_id}")
    p.drawString(80, 78, f"Dept: {staff.department.name}")
    p.drawString(80, 68, f"Position: {staff.position}")
    
    # Leadership role if applicable
    if staff.leadership_role != 'none':
        p.setFont("Helvetica-Bold", 7)
        p.setFillColorRGB(0.8, 0.2, 0.2)  # Red text for leadership
        role_display = staff.leadership_role.replace('_', ' ').title()
        p.drawString(15, 50, role_display)
    
    # Bottom section with blue accent
    p.setFillColorRGB(0.1, 0.3, 0.6)
    p.rect(0, 0, 3.375*72, 25, fill=1)
    
    # Footer text
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica", 6)
    p.drawString(15, 15, "This card is property of the University")
    p.drawString(15, 8, f"Valid from: {staff.hire_date}")
    p.drawString(130, 15, "Scan QR for profile")
    p.drawString(130, 8, f"ID: {staff.staff_id}")
    
    # Expiry date (5 years from hire date)
    from dateutil.relativedelta import relativedelta
    expiry_date = staff.hire_date + relativedelta(years=5)
    p.drawString(15, 2, f"Expires: {expiry_date}")
    
    # Generate QR code for staff profile
    profile_url = f"http://127.0.0.1:8000/staff/{staff.pk}/profile/"
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(profile_url)
    qr.make(fit=True)
    
    # Create QR code image and save to temporary file
    import tempfile
    import os
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    qr_img.save(temp_file.name)
    temp_file.close()
    
    # Draw QR code on card
    try:
        p.drawImage(temp_file.name, 200, 65, width=40, height=40)
        # Clean up temp file
        os.unlink(temp_file.name)
    except Exception as e:
        print(f"QR code error: {e}")
        # Clean up temp file even on error
        try:
            os.unlink(temp_file.name)
        except:
            pass
        # Fallback if QR code fails
        p.setFillColorRGB(0.8, 0.8, 0.8)
        p.rect(200, 65, 40, 40, fill=1)
        p.setFillColorRGB(0.5, 0.5, 0.5)
        p.setFont("Helvetica", 6)
        p.drawString(205, 85, "QR CODE")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{staff.staff_id}_id_card.pdf"'
    return response

# School Management Views
@login_required
def school_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    schools = School.objects.annotate(dept_count=Count('department')).order_by('name')
    return render(request, 'staff/school_list.html', {'schools': schools})

@login_required
def school_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'School added successfully!')
            return redirect('school_list')
    else:
        form = SchoolForm()
    return render(request, 'staff/school_form.html', {'form': form, 'title': 'Add School'})

@login_required
def school_update(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, 'School updated successfully!')
            return redirect('school_list')
    else:
        form = SchoolForm(instance=school)
    return render(request, 'staff/school_form.html', {'form': form, 'title': 'Update School'})

@login_required
def school_delete(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school.delete()
        messages.success(request, 'School deleted successfully!')
        return redirect('school_list')
    return render(request, 'staff/school_confirm_delete.html', {'school': school})

# Department Management Views
@login_required
def department_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    departments = Department.objects.select_related('school').annotate(staff_count=Count('staff')).order_by('name')
    return render(request, 'staff/department_list.html', {'departments': departments})

@login_required
def department_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully!')
            return redirect('department_list')
    else:
        form = DepartmentForm()
    return render(request, 'staff/department_form.html', {'form': form, 'title': 'Add Department'})

@login_required
def department_update(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully!')
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'staff/department_form.html', {'form': form, 'title': 'Update Department'})

@login_required
def department_delete(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully!')
        return redirect('department_list')
    return render(request, 'staff/department_confirm_delete.html', {'department': department})

# Export Views
@login_required
def export_staff_csv(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="staff_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Staff ID', 'Full Name', 'Email', 'Phone', 'Department', 'Position', 
        'Leadership Role', 'Staff Type', 'Grade', 'Hire Date', 'Status'
    ])
    
    staff_list = Staff.objects.select_related('department').filter(status='active')
    for staff in staff_list:
        writer.writerow([
            staff.staff_id,
            staff.full_name,
            staff.email,
            staff.phone,
            staff.department.name,
            staff.position,
            staff.get_leadership_role_display(),
            staff.get_staff_type_display(),
            staff.staff_grade,
            staff.hire_date,
            staff.get_status_display()
        ])
    
    return response

@login_required
def export_staff_pdf(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="staff_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph("University Staff Report", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Date
    date_para = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal'])
    story.append(date_para)
    story.append(Spacer(1, 12))
    
    # Staff data
    staff_list = Staff.objects.select_related('department').filter(status='active')
    
    data = [['Staff ID', 'Name', 'Department', 'Position', 'Leadership Role', 'Type']]
    for staff in staff_list:
        data.append([
            staff.staff_id,
            staff.full_name,
            staff.department.name,
            staff.position,
            staff.get_leadership_role_display(),
            staff.get_staff_type_display()
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    
    return response

# Staff self-service views
@login_required
def staff_apply_promotion(request):
    try:
        staff = Staff.objects.get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            try:
                promotion = form.save(commit=False)
                promotion.staff = staff
                promotion.old_position = staff.position
                promotion.old_department = staff.department
                promotion.old_grade = staff.staff_grade
                promotion.status = 'pending'
                promotion.save()
                messages.success(request, 'Promotion application submitted successfully!')
                return redirect('promotion_list')
            except Exception as e:
                print(f"Error applying for promotion: {e}")
                messages.error(request, f'Error submitting promotion application: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PromotionForm(initial={
            'staff': staff,
            'old_position': staff.position,
            'old_department': staff.department,
            'old_grade': staff.staff_grade
        })
        # Make fields readonly for staff
        form.fields['staff'].widget.attrs['readonly'] = True
        form.fields['staff'].initial = staff
        form.fields['old_position'].widget.attrs['readonly'] = True
        form.fields['old_department'].widget.attrs['readonly'] = True
        form.fields['old_grade'].widget.attrs['readonly'] = True
    
    return render(request, 'staff/staff_promotion_form.html', {'form': form, 'staff': staff})

@login_required
def update_profile_photo(request):
    try:
        staff = Staff.objects.get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found.')
        return redirect('dashboard')
    
    if request.method == 'POST' and request.FILES.get('photo'):
        photo = request.FILES['photo']
        
        # File validation
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
        max_size = 1 * 1024 * 1024  # 1MB
        
        if photo.content_type not in allowed_types:
            messages.error(request, 'Only JPEG, PNG, and GIF images are allowed.')
            return redirect('my_profile')
        
        if photo.size > max_size:
            messages.error(request, 'File size must be less than 1MB.')
            return redirect('my_profile')
        
        try:
            staff.photo = photo
            staff.save()
            messages.success(request, 'Profile photo updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating photo: {str(e)}')
    
    return redirect('my_profile')

@login_required
def approve_promotion(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)
    
    # Check if user can approve this promotion
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    is_supervisor = False
    
    try:
        user_staff = Staff.objects.get(email=request.user.email)
        supervisor = promotion.staff.get_supervisor()
        is_supervisor = supervisor and user_staff == supervisor
    except Staff.DoesNotExist:
        pass
    
    if not (is_hrmo or is_supervisor):
        messages.error(request, 'Access denied. Supervisor or HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            if is_supervisor and promotion.status == 'pending':
                promotion.status = 'supervisor_approved'
                promotion.supervisor_approved_by = request.user
                promotion.supervisor_approved_date = datetime.now()
                messages.success(request, f'Promotion for {promotion.staff.full_name} approved by supervisor!')
            elif is_hrmo and promotion.status == 'supervisor_approved':
                promotion.status = 'approved'
                promotion.approved_by = request.user
                promotion.approved_date = datetime.now()
                
                # Update staff record
                staff = promotion.staff
                staff.position = promotion.new_position
                staff.department = promotion.new_department
                staff.staff_grade = promotion.new_grade
                staff.save()
                
                messages.success(request, f'Promotion for {staff.full_name} approved by HR!')
        elif action == 'reject':
            promotion.status = 'rejected'
            promotion.rejection_reason = request.POST.get('rejection_reason', '')
            messages.success(request, f'Promotion for {promotion.staff.full_name} rejected.')
        
        promotion.save()
        return redirect('promotion_list')
    
    return render(request, 'staff/approve_promotion.html', {'promotion': promotion, 'is_supervisor': is_supervisor, 'is_hrmo': is_hrmo})

@login_required
def approve_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    
    # Check if user can approve this leave
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    is_supervisor = False
    
    try:
        user_staff = Staff.objects.get(email=request.user.email)
        supervisor = leave.staff.get_supervisor()
        is_supervisor = supervisor and user_staff == supervisor
    except Staff.DoesNotExist:
        pass
    
    if not (is_hrmo or is_supervisor):
        messages.error(request, 'Access denied. Supervisor or HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            if is_supervisor and leave.status == 'pending':
                leave.status = 'supervisor_approved'
                leave.supervisor_approved_by = request.user
                leave.supervisor_approved_date = datetime.now()
                messages.success(request, f'Leave for {leave.staff.full_name} approved by supervisor!')
            elif is_hrmo and leave.status == 'supervisor_approved':
                leave.status = 'approved'
                leave.approved_by = request.user
                leave.approved_date = datetime.now()
                messages.success(request, f'Leave for {leave.staff.full_name} approved by HR!')
        elif action == 'reject':
            leave.status = 'rejected'
            leave.rejection_reason = request.POST.get('rejection_reason', '')
            messages.success(request, f'Leave for {leave.staff.full_name} rejected.')
        
        leave.save()
        return redirect('leave_list')
    
    return render(request, 'staff/approve_leave.html', {'leave': leave, 'is_supervisor': is_supervisor, 'is_hrmo': is_hrmo})

@login_required
def staff_profile_view(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    
    # Handle HRMO assignment/removal
    if request.method == 'POST' and (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        action = request.POST.get('hrmo_action')
        if action == 'assign':
            try:
                user, created = User.objects.get_or_create(
                    email=staff.email,
                    defaults={
                        'username': staff.staff_id,
                        'first_name': staff.first_name,
                        'last_name': staff.last_name
                    }
                )
                HRMO.objects.create(user=user, staff=staff)
                messages.success(request, f'{staff.full_name} assigned as HRMO successfully!')
            except Exception as e:
                messages.error(request, f'Error assigning HRMO: {str(e)}')
        elif action == 'toggle':
            try:
                hrmo = HRMO.objects.get(staff=staff)
                hrmo.is_active = not hrmo.is_active
                hrmo.save()
                status = 'activated' if hrmo.is_active else 'deactivated'
                messages.success(request, f'HRMO status {status} for {staff.full_name}!')
            except HRMO.DoesNotExist:
                messages.error(request, 'HRMO record not found.')
        return redirect('staff_profile_view', pk=pk)
    
    # Check if staff has HRMO role
    try:
        hrmo = HRMO.objects.get(staff=staff)
    except HRMO.DoesNotExist:
        hrmo = None
    
    is_admin_or_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    return render(request, 'staff/staff_profile_view.html', {
        'staff': staff, 
        'hrmo': hrmo, 
        'is_admin_or_hrmo': is_admin_or_hrmo
    })

def staff_register(request):
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Input validation
        if not staff_id or not email or not password:
            messages.error(request, 'All fields are required.')
            return render(request, 'registration/staff_register.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'registration/staff_register.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'registration/staff_register.html')
        
        # Sanitize inputs
        import re
        if not re.match(r'^[A-Za-z0-9]+$', staff_id):
            messages.error(request, 'Staff ID can only contain letters and numbers.')
            return render(request, 'registration/staff_register.html')
        
        try:
            # Check if staff exists with this ID and email
            staff = Staff.objects.get(staff_id=staff_id, email=email)
            
            # Check if user already exists
            if User.objects.filter(Q(email=email) | Q(username=staff_id)).exists():
                messages.error(request, 'An account with this email or staff ID already exists.')
                return render(request, 'registration/staff_register.html')
            
            # Create user account
            user = User.objects.create_user(
                username=staff_id,
                email=email,
                password=password,
                first_name=staff.first_name,
                last_name=staff.last_name
            )
            
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('login')
            
        except Staff.DoesNotExist:
            messages.error(request, 'Invalid staff ID or email. Please contact HR.')
        except Exception as e:
            messages.error(request, 'Registration failed. Please try again.')
    
    return render(request, 'registration/staff_register.html')

# Bulk upload views
@login_required
def bulk_upload_staff(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # Validate CSV file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return render(request, 'staff/bulk_upload_staff.html')
        
        if csv_file.size > 10 * 1024 * 1024:  # 10MB limit
            messages.error(request, 'File size must be less than 10MB.')
            return render(request, 'staff/bulk_upload_staff.html')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    department = Department.objects.get(code=row['department_code'])
                    
                    Staff.objects.create(
                        staff_id=row['staff_id'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        email=row['email'],
                        phone=row['phone'],
                        date_of_birth=datetime.strptime(row['date_of_birth'], '%Y-%m-%d').date(),
                        address=row['address'],
                        next_of_kin_name=row['next_of_kin_name'],
                        next_of_kin_relationship=row['next_of_kin_relationship'],
                        next_of_kin_phone=row['next_of_kin_phone'],
                        next_of_kin_address=row['next_of_kin_address'],
                        department=department,
                        position=row['position'],
                        staff_type=row['staff_type'],
                        staff_category=row['staff_category'],
                        staff_grade=row['staff_grade'],
                        leadership_role=row.get('leadership_role', 'none'),
                        hire_date=datetime.strptime(row['hire_date'], '%Y-%m-%d').date(),
                        bank_name=row['bank_name'],
                        bank_account_number=row['bank_account_number'],
                        nassit_number=row['nassit_number'],
                        highest_qualification=row['highest_qualification'],
                        institution=row['institution'],
                        graduation_year=int(row['graduation_year'])
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
            
            messages.success(request, f'Successfully uploaded {success_count} staff records.')
            if error_count > 0:
                messages.warning(request, f'{error_count} records failed.')
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return render(request, 'staff/bulk_upload_staff.html')

@login_required
def bulk_upload_departments(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    school = None
                    if row.get('school_code'):
                        school = School.objects.get(code=row['school_code'])
                    
                    Department.objects.create(
                        name=row['name'],
                        code=row['code'],
                        school=school,
                        department_type=row.get('department_type', 'academic')
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
            
            messages.success(request, f'Successfully uploaded {success_count} departments.')
            if error_count > 0:
                messages.warning(request, f'{error_count} departments failed.')
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return render(request, 'staff/bulk_upload_departments.html')

@login_required
def bulk_upload_schools(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    School.objects.create(
                        name=row['name'],
                        code=row['code']
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
            
            messages.success(request, f'Successfully uploaded {success_count} schools.')
            if error_count > 0:
                messages.warning(request, f'{error_count} schools failed.')
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return render(request, 'staff/bulk_upload_schools.html')

@login_required
def retirement_settings(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import SystemSettings
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        retirement_age = request.POST.get('retirement_age')
        notification_months = request.POST.get('notification_months')
        
        try:
            settings.retirement_age = int(retirement_age)
            settings.retirement_notification_months = int(notification_months)
            settings.save()
            messages.success(request, 'Retirement settings updated successfully!')
        except ValueError:
            messages.error(request, 'Please enter valid numbers.')
    
    return render(request, 'staff/retirement_settings.html', {'settings': settings})

@login_required
def check_retirement_notifications(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import SystemSettings
    staff_due_retirement = Staff.objects.filter(status='active')
    retirement_due = [staff for staff in staff_due_retirement if staff.is_retirement_due]
    
    # Send notifications
    for staff in retirement_due:
        send_retirement_notification(staff)
    
    messages.success(request, f'Checked retirement notifications. {len(retirement_due)} staff due for retirement.')
    return render(request, 'staff/retirement_notifications.html', {'staff_list': retirement_due})

def send_retirement_notification(staff):
    """Send retirement notification to staff and HRMO"""
    from .models import SystemSettings
    system_settings = SystemSettings.get_settings()
    
    # Send to staff
    if staff.email:
        subject = 'Retirement Notification'
        message = f'''
        Dear {staff.full_name},
        
        This is to notify you that your retirement date is approaching.
        
        Retirement Date: {staff.retirement_date}
        Months Remaining: {staff.months_to_retirement}
        
        Please contact HR to discuss your retirement plans and benefits.
        
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
        subject = f'Staff Retirement Due - {staff.full_name}'
        message = f'''
        Staff retirement notification:
        
        Staff: {staff.full_name} ({staff.staff_id})
        Department: {staff.department.name}
        Position: {staff.position}
        Retirement Date: {staff.retirement_date}
        Months Remaining: {staff.months_to_retirement}
        
        Please initiate retirement processing procedures.
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            hrmo_emails,
            fail_silently=True,
        )

@login_required
def staff_grade_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import StaffGrade
    grades = StaffGrade.objects.filter(is_active=True).order_by('category', 'code')
    return render(request, 'staff/staff_grade_list.html', {'grades': grades})

@login_required
def staff_grade_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        code = request.POST.get('code')
        name = request.POST.get('name')
        category = request.POST.get('category')
        
        try:
            from .models import StaffGrade
            StaffGrade.objects.create(code=code, name=name, category=category)
            messages.success(request, 'Staff grade added successfully!')
            return redirect('staff_grade_list')
        except Exception as e:
            messages.error(request, f'Error adding grade: {str(e)}')
    
    return render(request, 'staff/staff_grade_form.html', {'title': 'Add Staff Grade'})

@login_required
def staff_grade_update(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import StaffGrade
    grade = get_object_or_404(StaffGrade, pk=pk)
    
    if request.method == 'POST':
        grade.code = request.POST.get('code')
        grade.name = request.POST.get('name')
        grade.category = request.POST.get('category')
        
        try:
            grade.save()
            messages.success(request, 'Staff grade updated successfully!')
            return redirect('staff_grade_list')
        except Exception as e:
            messages.error(request, f'Error updating grade: {str(e)}')
    
    return render(request, 'staff/staff_grade_form.html', {'grade': grade, 'title': 'Update Staff Grade'})

@login_required
def announcement_list(request):
    from .models import Announcement
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if is_hrmo:
        announcements = Announcement.objects.filter(is_active=True)
    else:
        # Show announcements targeted to this staff member
        try:
            staff = Staff.objects.get(email=request.user.email)
            announcements = []
            for announcement in Announcement.objects.filter(is_active=True):
                if staff in announcement.get_target_staff():
                    announcements.append(announcement)
        except Staff.DoesNotExist:
            announcements = []
    
    return render(request, 'staff/announcement_list.html', {'announcements': announcements, 'is_hrmo': is_hrmo})

@login_required
def announcement_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        announcement_type = request.POST.get('announcement_type')
        target_audience = request.POST.get('target_audience')
        send_email = request.POST.get('send_email') == 'on'
        department_ids = request.POST.getlist('departments')
        
        try:
            from .models import Announcement
            announcement = Announcement.objects.create(
                title=title,
                content=content,
                announcement_type=announcement_type,
                target_audience=target_audience,
                send_email=send_email,
                created_by=request.user
            )
            
            # Add specific departments if selected
            if department_ids:
                departments = Department.objects.filter(id__in=department_ids)
                announcement.specific_departments.set(departments)
            
            # Send emails if requested
            if send_email:
                target_staff = announcement.get_target_staff()
                staff_emails = [staff.email for staff in target_staff if staff.email]
                
                if staff_emails:
                    send_mail(
                        subject=f"{announcement.get_announcement_type_display()}: {title}",
                        message=content,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=staff_emails,
                        fail_silently=True,
                    )
                    messages.success(request, f'Announcement created and sent to {len(staff_emails)} staff members!')
                else:
                    messages.success(request, 'Announcement created successfully!')
            else:
                messages.success(request, 'Announcement created successfully!')
            
            return redirect('announcement_list')
        except Exception as e:
            messages.error(request, f'Error creating announcement: {str(e)}')
    
    departments = Department.objects.all()
    return render(request, 'staff/announcement_form.html', {'departments': departments})

@login_required
def announcement_detail(request, pk):
    from .models import Announcement
    announcement = get_object_or_404(Announcement, pk=pk)
    
    # Check if user can view this announcement
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    can_view = is_hrmo
    
    if not is_hrmo:
        try:
            staff = Staff.objects.get(email=request.user.email)
            can_view = staff in announcement.get_target_staff()
        except Staff.DoesNotExist:
            can_view = False
    
    if not can_view:
        messages.error(request, 'Access denied.')
        return redirect('announcement_list')
    
    return render(request, 'staff/announcement_detail.html', {'announcement': announcement})

@login_required
def hrmo_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. Admin/HRMO privileges required.')
        return redirect('dashboard')
    
    hrmos = HRMO.objects.select_related('staff', 'user').all()
    return render(request, 'staff/hrmo_list.html', {'hrmos': hrmos})

@login_required
def hrmo_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. Admin/HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        staff_id = request.POST.get('staff')
        try:
            staff = Staff.objects.get(id=staff_id)
            user, created = User.objects.get_or_create(
                email=staff.email,
                defaults={
                    'username': staff.staff_id,
                    'first_name': staff.first_name,
                    'last_name': staff.last_name
                }
            )
            HRMO.objects.create(user=user, staff=staff)
            messages.success(request, f'{staff.full_name} assigned as HRMO successfully!')
            return redirect('hrmo_list')
        except Exception as e:
            messages.error(request, f'Error assigning HRMO: {str(e)}')
    
    staff_list = Staff.objects.filter(status='active').exclude(hrmo__isnull=False)
    return render(request, 'staff/hrmo_form.html', {'staff_list': staff_list})

@login_required
def hrmo_toggle(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. Admin/HRMO privileges required.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, pk=pk)
    
    try:
        hrmo = HRMO.objects.get(staff=staff)
        hrmo.is_active = not hrmo.is_active
        hrmo.save()
        status = 'activated' if hrmo.is_active else 'deactivated'
        messages.success(request, f'HRMO {staff.full_name} {status} successfully!')
    except HRMO.DoesNotExist:
        # Create new HRMO
        user, created = User.objects.get_or_create(
            email=staff.email,
            defaults={
                'username': staff.staff_id,
                'first_name': staff.first_name,
                'last_name': staff.last_name
            }
        )
        HRMO.objects.create(user=user, staff=staff)
        messages.success(request, f'{staff.full_name} assigned as HRMO successfully!')
    
    return redirect('staff_list')

@login_required
def check_contract_renewals(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    staff_needing_renewal = Staff.objects.filter(status='active')
    renewal_due = [staff for staff in staff_needing_renewal if staff.needs_contract_renewal_notification]
    
    # Send notifications
    for staff in renewal_due:
        send_contract_renewal_notification(staff)
    
    messages.success(request, f'Checked contract renewals. {len(renewal_due)} staff need contract renewal notifications.')
    return render(request, 'staff/contract_renewal_notifications.html', {'staff_list': renewal_due})

def send_contract_renewal_notification(staff):
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

@login_required
def reset_user_password(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. Admin/HRMO privileges required.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, pk=pk)
    
    if request.method == 'POST':
        try:
            # Find user by email or staff_id
            user = None
            try:
                user = User.objects.get(email=staff.email)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(username=staff.staff_id)
                except User.DoesNotExist:
                    messages.error(request, 'User account not found for this staff member.')
                    return render(request, 'staff/reset_password.html', {'staff': staff})
            
            # Generate temporary password
            import random
            import string
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            user.set_password(temp_password)
            user.save()
            
            # Create or update user profile to mark password change required
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.must_change_password = True
            profile.save()
            
            # Send notification email with temporary password
            if staff.email:
                send_mail(
                    subject='Temporary Password - Action Required',
                    message=f'''
                    Dear {staff.full_name},
                    
                    Your account password has been reset by HR administration.
                    
                    Temporary Password: {temp_password}
                    
                    IMPORTANT: You must change this password when you first log in.
                    This temporary password will expire after your first login.
                    
                    Please log in to the system and change your password immediately.
                    If you did not request this change, please contact HR immediately.
                    
                    Best regards,
                    Human Resources
                    ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[staff.email],
                    fail_silently=True,
                )
            
            messages.success(request, f'Temporary password generated and sent to {staff.full_name}!')
            return redirect('staff_list')
            
        except Exception as e:
            messages.error(request, f'Error resetting password: {str(e)}')
    
    return render(request, 'staff/reset_password.html', {'staff': staff})

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'staff/change_password.html')
        
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return render(request, 'staff/change_password.html')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'staff/change_password.html')
        
        try:
            request.user.set_password(new_password)
            request.user.save()
            
            # Update profile to remove password change requirement
            from .models import UserProfile
            try:
                profile = UserProfile.objects.get(user=request.user)
                profile.must_change_password = False
                profile.save()
            except UserProfile.DoesNotExist:
                pass
            
            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Password changed successfully!')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')
    
    return render(request, 'staff/change_password.html')

# Payroll Management Views
@login_required
def payroll_dashboard(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import PayrollPeriod, Payslip, SalaryStructure
    
    current_period = PayrollPeriod.objects.filter(is_processed=False).first()
    recent_periods = PayrollPeriod.objects.all()[:5]
    total_staff = Staff.objects.filter(status='active').count()
    salary_structures = SalaryStructure.objects.filter(is_active=True).count()
    
    context = {
        'current_period': current_period,
        'recent_periods': recent_periods,
        'total_staff': total_staff,
        'salary_structures': salary_structures,
    }
    return render(request, 'staff/payroll_dashboard.html', context)

@login_required
def process_payroll(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        from .models import PayrollPeriod, Payslip, SalaryStructure, LoanRecord
        from datetime import datetime
        from decimal import Decimal
        
        period_id = request.POST.get('period_id')
        try:
            period = PayrollPeriod.objects.get(id=period_id)
            if period.is_processed:
                messages.error(request, 'This payroll period has already been processed.')
                return redirect('payroll_dashboard')
            
            active_staff = Staff.objects.filter(status='active')
            processed_count = 0
            
            for staff in active_staff:
                try:
                    salary_structure = SalaryStructure.objects.get(
                        staff_category=staff.staff_category,
                        staff_grade=staff.staff_grade,
                        employment_type=staff.employment_type,
                        is_active=True
                    )
                except SalaryStructure.DoesNotExist:
                    continue
                
                active_loans = LoanRecord.objects.filter(
                    staff=staff, 
                    status='active',
                    start_deduction_date__lte=period.end_date,
                    end_deduction_date__gte=period.start_date
                )
                loan_deduction = sum(loan.monthly_deduction for loan in active_loans)
                
                income_tax = salary_structure.basic_salary * Decimal('0.10')
                nassit = salary_structure.basic_salary * Decimal('0.05')
                
                payslip, created = Payslip.objects.get_or_create(
                    staff=staff,
                    payroll_period=period,
                    defaults={
                        'basic_salary': salary_structure.basic_salary,
                        'housing_allowance': salary_structure.housing_allowance,
                        'transport_allowance': salary_structure.transport_allowance,
                        'medical_allowance': salary_structure.medical_allowance,
                        'other_allowances': salary_structure.other_allowances,
                        'income_tax': income_tax,
                        'nassit_contribution': nassit,
                        'loan_deduction': loan_deduction,
                        'gross_pay': Decimal('0.00'),
                        'total_deductions': Decimal('0.00'),
                        'net_pay': Decimal('0.00'),
                    }
                )
                
                payslip.calculate_totals()
                payslip.save()
                processed_count += 1
            
            period.is_processed = True
            period.processed_by = request.user
            period.processed_date = datetime.now()
            period.save()
            
            messages.success(request, f'Payroll processed successfully for {processed_count} staff members!')
            
        except Exception as e:
            messages.error(request, f'Error processing payroll: {str(e)}')
    
    return redirect('payroll_dashboard')

@login_required
def generate_payslip_pdf(request, pk):
    from .models import Payslip
    payslip = get_object_or_404(Payslip, pk=pk)
    
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    is_own_payslip = False
    
    if not is_hrmo:
        try:
            user_staff = Staff.objects.get(email=request.user.email)
            is_own_payslip = user_staff == payslip.staff
        except Staff.DoesNotExist:
            pass
    
    if not (is_hrmo or is_own_payslip):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    title = Paragraph("UNIVERSITY OF SIERRA LEONE - PAYSLIP", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    info_data = [
        ['Staff:', payslip.staff.full_name, 'ID:', payslip.staff.staff_id],
        ['Department:', payslip.staff.department.name, 'Period:', payslip.payroll_period.name],
    ]
    
    info_table = Table(info_data)
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    pay_data = [
        ['EARNINGS', '', 'DEDUCTIONS', ''],
        ['Basic Salary', f'{payslip.basic_salary:,.2f}', 'Income Tax', f'{payslip.income_tax:,.2f}'],
        ['Allowances', f'{payslip.housing_allowance + payslip.transport_allowance + payslip.medical_allowance + payslip.other_allowances:,.2f}', 'NASSIT', f'{payslip.nassit_contribution:,.2f}'],
        ['', '', 'Loans', f'{payslip.loan_deduction:,.2f}'],
        ['GROSS PAY', f'{payslip.gross_pay:,.2f}', 'TOTAL DEDUCTIONS', f'{payslip.total_deductions:,.2f}'],
        ['NET PAY', f'{payslip.net_pay:,.2f}', '', ''],
    ]
    
    pay_table = Table(pay_data)
    pay_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    
    story.append(pay_table)
    doc.build(story)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payslip_{payslip.staff.staff_id}.pdf"'
    return response

@login_required
def my_payslips(request):
    try:
        staff = Staff.objects.get(email=request.user.email)
        from .models import Payslip
        payslips = Payslip.objects.filter(staff=staff).order_by('-payroll_period__start_date')
        return render(request, 'staff/my_payslips.html', {'payslips': payslips, 'staff': staff})
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found.')
        return redirect('dashboard')

@login_required
def create_payroll_period(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        from .models import PayrollPeriod
        from datetime import datetime
        
        name = request.POST.get('name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            PayrollPeriod.objects.create(
                name=name,
                start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
                end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            )
            messages.success(request, f'Payroll period "{name}" created successfully!')
            return redirect('payroll_dashboard')
        except Exception as e:
            messages.error(request, f'Error creating payroll period: {str(e)}')
    
    return render(request, 'staff/create_payroll_period.html')

@login_required
def salary_structure_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import SalaryStructure
    structures = SalaryStructure.objects.filter(is_active=True).order_by('staff_category', 'staff_grade')
    return render(request, 'staff/salary_structure_list.html', {'structures': structures})

@login_required
def payslip_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import Payslip
    payslips = Payslip.objects.select_related('staff', 'payroll_period').order_by('-payroll_period__start_date')
    return render(request, 'staff/payslip_list.html', {'payslips': payslips})

@login_required
def leave_balance_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import LeaveBalance
    balances = LeaveBalance.objects.select_related('staff').order_by('staff__first_name')
    return render(request, 'staff/leave_balance_list.html', {'balances': balances})

@login_required
def my_leave_balance(request):
    try:
        staff = Staff.objects.get(email=request.user.email)
        from .models import LeaveBalance
        balance, created = LeaveBalance.objects.get_or_create(
            staff=staff, 
            year=2025,
            defaults={
                'annual_leave_balance': 21,
                'sick_leave_balance': 10,
                'maternity_leave_balance': 90,
                'paternity_leave_balance': 7,
                'emergency_leave_balance': 3,
            }
        )
        return render(request, 'staff/my_leave_balance.html', {'balance': balance, 'staff': staff})
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found.')
        return redirect('dashboard')

@login_required
def salary_structure_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        from .models import SalaryStructure
        from decimal import Decimal
        
        try:
            SalaryStructure.objects.create(
                staff_category=request.POST['staff_category'],
                staff_grade=request.POST['staff_grade'],
                employment_type=request.POST['employment_type'],
                basic_salary=Decimal(request.POST['basic_salary']),
                housing_allowance=Decimal(request.POST.get('housing_allowance', '0')),
                transport_allowance=Decimal(request.POST.get('transport_allowance', '0')),
                medical_allowance=Decimal(request.POST.get('medical_allowance', '0')),
                other_allowances=Decimal(request.POST.get('other_allowances', '0')),
            )
            messages.success(request, 'Salary structure created successfully!')
            return redirect('salary_structure_list')
        except Exception as e:
            messages.error(request, f'Error creating salary structure: {str(e)}')
    
    return render(request, 'staff/salary_structure_form.html', {'title': 'Create Salary Structure'})

@login_required
def loan_list(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import LoanRecord
    loans = LoanRecord.objects.select_related('staff').order_by('-application_date')
    return render(request, 'staff/loan_list.html', {'loans': loans})

@login_required
def loan_create(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        from .models import LoanRecord
        from decimal import Decimal
        
        try:
            staff_id = request.POST['staff']
            staff = Staff.objects.get(id=staff_id)
            amount = Decimal(request.POST['amount'])
            interest_rate = Decimal(request.POST.get('interest_rate', '0'))
            repayment_months = int(request.POST['repayment_months'])
            
            loan = LoanRecord.objects.create(
                staff=staff,
                loan_type=request.POST['loan_type'],
                amount=amount,
                interest_rate=interest_rate,
                repayment_months=repayment_months,
                monthly_deduction=Decimal('0'),
                balance=amount,
                status='pending',
                notes=request.POST.get('notes', '')
            )
            
            loan.calculate_monthly_payment()
            loan.save()
            
            messages.success(request, f'Loan application created for {staff.full_name}!')
            return redirect('loan_list')
        except Exception as e:
            messages.error(request, f'Error creating loan: {str(e)}')
    
    staff_list = Staff.objects.filter(status='active').order_by('first_name')
    return render(request, 'staff/loan_form.html', {'staff_list': staff_list, 'title': 'Create Loan'})

@login_required
def loan_approve(request, pk):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import LoanRecord
    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta
    
    loan = get_object_or_404(LoanRecord, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            loan.status = 'active'
            loan.approval_date = date.today()
            loan.approved_by = request.user
            loan.start_deduction_date = date.today() + timedelta(days=30)
            loan.end_deduction_date = loan.start_deduction_date + relativedelta(months=loan.repayment_months)
            messages.success(request, f'Loan approved for {loan.staff.full_name}!')
        elif action == 'reject':
            loan.status = 'rejected'
            messages.success(request, f'Loan rejected for {loan.staff.full_name}!')
        
        loan.save()
        return redirect('loan_list')
    
    return render(request, 'staff/loan_approve.html', {'loan': loan})

# Performance Evaluation Views
@login_required
def performance_review_list(request):
    from .models import PerformanceReview
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if is_hrmo:
        reviews = PerformanceReview.objects.select_related('staff', 'supervisor').order_by('-scheduled_date')
    else:
        try:
            staff = Staff.objects.get(email=request.user.email)
            reviews = PerformanceReview.objects.filter(
                Q(staff=staff) | Q(supervisor=staff)
            ).select_related('staff', 'supervisor').order_by('-scheduled_date')
        except Staff.DoesNotExist:
            reviews = PerformanceReview.objects.none()
    
    return render(request, 'staff/performance_review_list.html', {'reviews': reviews, 'is_hrmo': is_hrmo})

@login_required
def performance_review_create(request):
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    
    if not is_hrmo:
        try:
            user_staff = Staff.objects.get(email=request.user.email)
            if not user_staff.supervised_staff.exists():
                messages.error(request, 'Access denied. Supervisor privileges required.')
                return redirect('dashboard')
        except Staff.DoesNotExist:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
    
    if request.method == 'POST':
        from .models import PerformanceReview
        from datetime import datetime
        
        try:
            staff_id = request.POST['staff']
            staff = Staff.objects.get(id=staff_id)
            
            if not is_hrmo:
                user_staff = Staff.objects.get(email=request.user.email)
                if staff.supervisor != user_staff:
                    messages.error(request, 'You can only create reviews for your direct reports.')
                    return redirect('performance_review_list')
            
            review = PerformanceReview.objects.create(
                staff=staff,
                supervisor=staff.get_supervisor(),
                review_period_start=datetime.strptime(request.POST['review_period_start'], '%Y-%m-%d').date(),
                review_period_end=datetime.strptime(request.POST['review_period_end'], '%Y-%m-%d').date(),
                scheduled_date=datetime.strptime(request.POST['scheduled_date'], '%Y-%m-%dT%H:%M'),
                status='scheduled'
            )
            
            messages.success(request, f'Performance review scheduled for {staff.full_name}!')
            return redirect('performance_review_list')
        except Exception as e:
            messages.error(request, f'Error creating review: {str(e)}')
    
    if is_hrmo:
        staff_list = Staff.objects.filter(status='active').order_by('first_name')
    else:
        user_staff = Staff.objects.get(email=request.user.email)
        staff_list = user_staff.supervised_staff.filter(status='active')
    
    return render(request, 'staff/performance_review_form.html', {'staff_list': staff_list, 'title': 'Schedule Performance Review'})

@login_required
def performance_review_detail(request, pk):
    from .models import PerformanceReview, PerformanceGoal, StaffFeedback, SelfAssessment
    review = get_object_or_404(PerformanceReview, pk=pk)
    
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    can_edit = is_hrmo
    
    try:
        user_staff = Staff.objects.get(email=request.user.email)
        can_edit = can_edit or user_staff == review.supervisor or user_staff == review.staff
    except Staff.DoesNotExist:
        pass
    
    if not can_edit:
        messages.error(request, 'Access denied.')
        return redirect('performance_review_list')
    
    if request.method == 'POST':
        if request.POST.get('action') == 'complete_review':
            review.status = 'completed'
            review.completed_date = datetime.now()
            review.overall_rating = request.POST.get('overall_rating')
            review.strengths = request.POST.get('strengths', '')
            review.areas_for_improvement = request.POST.get('areas_for_improvement', '')
            review.supervisor_comments = request.POST.get('supervisor_comments', '')
            review.staff_comments = request.POST.get('staff_comments', '')
            review.save()
            messages.success(request, 'Performance review completed!')
        elif request.POST.get('action') == 'add_goal':
            PerformanceGoal.objects.create(
                review=review,
                title=request.POST['goal_title'],
                description=request.POST['goal_description'],
                target_date=datetime.strptime(request.POST['target_date'], '%Y-%m-%d').date()
            )
            messages.success(request, 'Goal added successfully!')
        return redirect('performance_review_detail', pk=pk)
    
    goals = review.goals.all()
    feedback = review.feedback.all()
    try:
        self_assessment = review.self_assessment
    except SelfAssessment.DoesNotExist:
        self_assessment = None
    
    context = {
        'review': review,
        'goals': goals,
        'feedback': feedback,
        'self_assessment': self_assessment,
        'is_hrmo': is_hrmo,
        'can_edit': can_edit
    }
    return render(request, 'staff/performance_review_detail.html', context)

@login_required
def submit_feedback(request, pk):
    from .models import PerformanceReview, StaffFeedback
    review = get_object_or_404(PerformanceReview, pk=pk)
    
    try:
        user_staff = Staff.objects.get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            StaffFeedback.objects.create(
                staff=user_staff,
                about_staff=review.staff,
                review=review,
                feedback_type=request.POST['feedback_type'],
                rating=int(request.POST['rating']),
                comments=request.POST['comments'],
                anonymous=request.POST.get('anonymous') == 'on'
            )
            messages.success(request, 'Feedback submitted successfully!')
            return redirect('performance_review_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'Error submitting feedback: {str(e)}')
    
    return render(request, 'staff/submit_feedback.html', {'review': review})

@login_required
def submit_self_assessment(request, pk):
    from .models import PerformanceReview, SelfAssessment
    review = get_object_or_404(PerformanceReview, pk=pk)
    
    try:
        user_staff = Staff.objects.get(email=request.user.email)
        if user_staff != review.staff:
            messages.error(request, 'You can only submit self-assessment for your own review.')
            return redirect('performance_review_list')
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            assessment, created = SelfAssessment.objects.get_or_create(
                staff=user_staff,
                review=review,
                defaults={
                    'achievements': request.POST['achievements'],
                    'challenges_faced': request.POST['challenges_faced'],
                    'skills_developed': request.POST['skills_developed'],
                    'training_needs': request.POST['training_needs'],
                    'career_goals': request.POST['career_goals'],
                    'self_rating': int(request.POST['self_rating'])
                }
            )
            
            if not created:
                assessment.achievements = request.POST['achievements']
                assessment.challenges_faced = request.POST['challenges_faced']
                assessment.skills_developed = request.POST['skills_developed']
                assessment.training_needs = request.POST['training_needs']
                assessment.career_goals = request.POST['career_goals']
                assessment.self_rating = int(request.POST['self_rating'])
                assessment.save()
            
            messages.success(request, 'Self-assessment submitted successfully!')
            return redirect('performance_review_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'Error submitting self-assessment: {str(e)}')
    
    try:
        existing_assessment = SelfAssessment.objects.get(staff=user_staff, review=review)
    except SelfAssessment.DoesNotExist:
        existing_assessment = None
    
    return render(request, 'staff/self_assessment_form.html', {'review': review, 'assessment': existing_assessment})

@login_required
def performance_reports(request):
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    from .models import PerformanceReview
    from django.db.models import Avg, Count
    
    # Performance metrics by department
    dept_performance = Department.objects.annotate(
        avg_rating=Avg('staff__performance_reviews__overall_rating'),
        review_count=Count('staff__performance_reviews')
    ).filter(avg_rating__isnull=False)
    
    # Recent completed reviews
    recent_reviews = PerformanceReview.objects.filter(
        status='completed'
    ).select_related('staff', 'supervisor').order_by('-completed_date')[:10]
    
    # Performance distribution
    rating_distribution = PerformanceReview.objects.filter(
        status='completed',
        overall_rating__isnull=False
    ).values('overall_rating').annotate(count=Count('id')).order_by('overall_rating')
    
    context = {
        'dept_performance': dept_performance,
        'recent_reviews': recent_reviews,
        'rating_distribution': rating_distribution,
    }
    return render(request, 'staff/performance_reports.html', context)

@login_required
def update_goal_progress(request, pk):
    from .models import PerformanceGoal
    goal = get_object_or_404(PerformanceGoal, pk=pk)
    
    is_hrmo = request.user.is_superuser or hasattr(request.user, 'hrmo')
    can_edit = is_hrmo
    
    try:
        user_staff = Staff.objects.get(email=request.user.email)
        can_edit = can_edit or user_staff == goal.review.supervisor or user_staff == goal.review.staff
    except Staff.DoesNotExist:
        pass
    
    if not can_edit:
        messages.error(request, 'Access denied.')
        return redirect('performance_review_list')
    
    if request.method == 'POST':
        goal.progress_percentage = int(request.POST['progress_percentage'])
        goal.status = request.POST['status']
        goal.notes = request.POST.get('notes', '')
        goal.save()
        messages.success(request, 'Goal progress updated!')
        return redirect('performance_review_detail', pk=goal.review.pk)
    
    return render(request, 'staff/update_goal_progress.html', {'goal': goal})