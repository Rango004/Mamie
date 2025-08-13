from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
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