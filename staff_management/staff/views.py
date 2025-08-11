from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Staff, Department, School, Leave, Promotion, Retirement, Bereavement, HRMO
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
        pending_leaves = Leave.objects.filter(status='pending').count()
        
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
        
        context = {
            'total_staff': total_staff,
            'total_departments': total_departments,
            'total_schools': total_schools,
            'pending_leaves': pending_leaves,
            'staff_by_dept': staff_by_dept,
            'leadership_roles': leadership_roles,
            'recent_leaves': recent_leaves,
            'recent_promotions': recent_promotions,
        }
    else:
        # Limited dashboard for regular staff
        try:
            staff = Staff.objects.get(email=request.user.email)
            my_leaves = Leave.objects.filter(staff=staff).order_by('-applied_date')[:5]
            my_promotions = Promotion.objects.filter(staff=staff).order_by('-created_at')[:3]
            pending_leaves = Leave.objects.filter(staff=staff, status='pending').count()
            
            context = {
                'staff': staff,
                'my_leaves': my_leaves,
                'my_promotions': my_promotions,
                'pending_leaves': pending_leaves,
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
    return render(request, 'staff/staff_list.html', {'staff': staff})

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
    return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Update Staff'})

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
    
    return render(request, 'staff/leave_list.html', {'leaves': leaves})

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
    
    return render(request, 'staff/promotion_list.html', {'promotions': promotions})

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
            messages.success(request, 'Retirement processed successfully!')
            return redirect('retirement_list')
    else:
        form = RetirementForm()
    return render(request, 'staff/retirement_form.html', {'form': form, 'title': 'Process Retirement'})

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
    if not (request.user.is_superuser or hasattr(request.user, 'hrmo')):
        messages.error(request, 'Access denied. HRMO privileges required.')
        return redirect('dashboard')
    
    promotion = get_object_or_404(Promotion, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            promotion.status = 'approved'
            promotion.approved_by = request.user
            promotion.approved_date = datetime.now()
            
            # Update staff record
            staff = promotion.staff
            staff.position = promotion.new_position
            staff.department = promotion.new_department
            staff.staff_grade = promotion.new_grade
            staff.save()
            
            messages.success(request, f'Promotion for {staff.full_name} approved successfully!')
        elif action == 'reject':
            promotion.status = 'rejected'
            promotion.rejection_reason = request.POST.get('rejection_reason', '')
            messages.success(request, f'Promotion for {promotion.staff.full_name} rejected.')
        
        promotion.save()
        return redirect('promotion_list')
    
    return render(request, 'staff/approve_promotion.html', {'promotion': promotion})

@login_required
def staff_profile_view(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    return render(request, 'staff/staff_profile_view.html', {'staff': staff})

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