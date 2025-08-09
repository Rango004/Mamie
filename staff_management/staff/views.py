from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.template.loader import get_template
from .models import Staff, Department, School, Leave, Promotion, Retirement, Bereavement, HRMO, Notification, WorkflowAction
from .forms import (StaffForm, LeaveForm, PromotionForm, RetirementForm, BereavementForm, 
                   SchoolForm, DepartmentForm, LeaveApprovalForm, PromotionApprovalForm, 
                   StaffLeaveApplicationForm, HRMOForm)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.contrib.auth.models import User
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from PIL import Image

def dashboard(request):
    # Statistics
    total_staff = Staff.objects.filter(status='active').count()
    total_departments = Department.objects.count()
    total_schools = School.objects.count()
    pending_leaves = Leave.objects.filter(status='pending').count()
    pending_promotions = Promotion.objects.filter(status='pending').count()
    total_hrmos = HRMO.objects.filter(is_active=True).count()
    
    # Staff by department
    staff_by_dept = Department.objects.annotate(
        staff_count=Count('staff', filter=Q(staff__status='active'))
    ).order_by('-staff_count')[:5]
    
    # Recent activities
    recent_leaves = Leave.objects.select_related('staff').order_by('-applied_date')[:5]
    recent_promotions = Promotion.objects.select_related('staff').order_by('-created_at')[:5]
    
    # Workflow statistics
    approved_leaves_this_month = Leave.objects.filter(
        status='approved',
        approved_date__month=timezone.now().month
    ).count()
    
    context = {
        'total_staff': total_staff,
        'total_departments': total_departments,
        'total_schools': total_schools,
        'pending_leaves': pending_leaves,
        'pending_promotions': pending_promotions,
        'total_hrmos': total_hrmos,
        'approved_leaves_this_month': approved_leaves_this_month,
        'staff_by_dept': staff_by_dept,
        'recent_leaves': recent_leaves,
        'recent_promotions': recent_promotions,
    }
    return render(request, 'staff/dashboard.html', context)

def staff_list(request):
    staff = Staff.objects.select_related('department__school').filter(status='active')
    return render(request, 'staff/staff_list.html', {'staff': staff})

def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member added successfully!')
            return redirect('staff_list')
    else:
        form = StaffForm()
    return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Add Staff'})

def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully!')
            return redirect('staff_list')
    else:
        form = StaffForm(instance=staff)
    return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Update Staff'})

def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        staff.delete()
        messages.success(request, 'Staff member deleted successfully!')
        return redirect('staff_list')
    return render(request, 'staff/staff_confirm_delete.html', {'staff': staff})

def leave_list(request):
    leaves = Leave.objects.select_related('staff').order_by('-applied_date')
    return render(request, 'staff/leave_list.html', {'leaves': leaves})

def leave_create(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save()
            # Send notification to HRMOs
            leave.send_application_notification()
            
            # Create workflow action
            WorkflowAction.objects.create(
                action_type='leave_applied',
                performed_by=request.user,
                staff_affected=leave.staff,
                description=f'Leave application submitted for {leave.get_leave_type_display()}',
                content_type='leave',
                object_id=leave.id
            )
            
            messages.success(request, 'Leave application submitted successfully! HRMOs have been notified.')
            return redirect('leave_list')
    else:
        form = LeaveForm()
    return render(request, 'staff/leave_form.html', {'form': form, 'title': 'Apply for Leave'})

def promotion_list(request):
    promotions = Promotion.objects.select_related('staff').order_by('-created_at')
    return render(request, 'staff/promotion_list.html', {'promotions': promotions})

def promotion_create(request):
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            promotion = form.save()
            # Send notification to HRMOs
            promotion.send_application_notification()
            
            # Create workflow action
            WorkflowAction.objects.create(
                action_type='promotion_applied',
                performed_by=request.user,
                staff_affected=promotion.staff,
                description=f'Promotion application submitted: {promotion.old_position} to {promotion.new_position}',
                content_type='promotion',
                object_id=promotion.id
            )
            
            messages.success(request, 'Promotion application submitted successfully! HRMOs have been notified.')
            return redirect('promotion_list')
    else:
        form = PromotionForm()
    return render(request, 'staff/promotion_form.html', {'form': form, 'title': 'Submit Promotion Application'})

def retirement_list(request):
    retirements = Retirement.objects.select_related('staff').order_by('-created_at')
    return render(request, 'staff/retirement_list.html', {'retirements': retirements})

def retirement_create(request):
    if request.method == 'POST':
        form = RetirementForm(request.POST)
        if form.is_valid():
            retirement = form.save()
            # Update staff status
            staff = retirement.staff
            staff.status = 'retired'
            staff.save()
            
            # Send retirement notification (handled in form save method)
            messages.success(request, 'Retirement processed successfully! Notifications have been sent.')
            return redirect('retirement_list')
    else:
        form = RetirementForm()
    return render(request, 'staff/retirement_form.html', {'form': form, 'title': 'Process Retirement'})

def bereavement_list(request):
    bereavements = Bereavement.objects.select_related('staff').order_by('-created_at')
    return render(request, 'staff/bereavement_list.html', {'bereavements': bereavements})

def bereavement_create(request):
    if request.method == 'POST':
        form = BereavementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bereavement leave recorded successfully!')
            return redirect('bereavement_list')
    else:
        form = BereavementForm()
    return render(request, 'staff/bereavement_form.html', {'form': form, 'title': 'Record Bereavement Leave'})

def print_id_card(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    
    # Create PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(3.375*72, 2.125*72))  # Standard ID card size
    
    # Card background
    p.setFillColorRGB(0.9, 0.9, 0.9)
    p.rect(0, 0, 3.375*72, 2.125*72, fill=1)
    
    # University header
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(10, 140, "UNIVERSITY STAFF ID")
    
    # Staff photo placeholder
    p.setFillColorRGB(0.8, 0.8, 0.8)
    p.rect(10, 80, 50, 50, fill=1)
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 8)
    p.drawString(15, 100, "PHOTO")
    
    # Staff details
    p.setFont("Helvetica-Bold", 10)
    p.drawString(70, 120, staff.full_name)
    p.setFont("Helvetica", 8)
    p.drawString(70, 110, f"ID: {staff.staff_id}")
    p.drawString(70, 100, f"Dept: {staff.department.name}")
    p.drawString(70, 90, f"Position: {staff.position}")
    
    # Footer
    p.setFont("Helvetica", 6)
    p.drawString(10, 10, "This card is property of the University")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{staff.staff_id}_id_card.pdf"'
    return response

# School Management Views
def school_list(request):
    schools = School.objects.annotate(dept_count=Count('department')).order_by('name')
    return render(request, 'staff/school_list.html', {'schools': schools})

def school_create(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'School added successfully!')
            return redirect('school_list')
    else:
        form = SchoolForm()
    return render(request, 'staff/school_form.html', {'form': form, 'title': 'Add School'})

def school_update(request, pk):
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

def school_delete(request, pk):
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school.delete()
        messages.success(request, 'School deleted successfully!')
        return redirect('school_list')
    return render(request, 'staff/school_confirm_delete.html', {'school': school})

# Department Management Views
def department_list(request):
    departments = Department.objects.select_related('school', 'parent_department').annotate(staff_count=Count('staff')).order_by('name')
    return render(request, 'staff/department_list.html', {'departments': departments})

def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully!')
            return redirect('department_list')
    else:
        form = DepartmentForm()
    return render(request, 'staff/department_form.html', {'form': form, 'title': 'Add Department'})

def department_update(request, pk):
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

def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully!')
        return redirect('department_list')
    return render(request, 'staff/department_confirm_delete.html', {'department': department})

# Workflow Views
def is_hrmo(user):
    """Check if user is an HRMO"""
    try:
        return HRMO.objects.filter(user=user, is_active=True).exists()
    except:
        return False

@login_required
@user_passes_test(is_hrmo)
def pending_approvals(request):
    """Dashboard for HRMOs to see pending approvals"""
    pending_leaves = Leave.objects.filter(status='pending').select_related('staff')
    pending_promotions = Promotion.objects.filter(status='pending').select_related('staff')
    
    context = {
        'pending_leaves': pending_leaves,
        'pending_promotions': pending_promotions,
    }
    return render(request, 'staff/pending_approvals.html', context)

@login_required
@user_passes_test(is_hrmo)
def approve_leave(request, pk):
    """Approve or reject leave application"""
    leave = get_object_or_404(Leave, pk=pk, status='pending')
    
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.approved_by = request.user
            leave.approved_date = timezone.now()
            leave.save()
            
            # Send notification to staff
            leave.send_approval_notification()
            
            # Create workflow action
            action_type = 'leave_approved' if leave.status == 'approved' else 'leave_rejected'
            WorkflowAction.objects.create(
                action_type=action_type,
                performed_by=request.user,
                staff_affected=leave.staff,
                description=f'Leave application {leave.status}',
                content_type='leave',
                object_id=leave.id
            )
            
            messages.success(request, f'Leave application {leave.status} successfully!')
            return redirect('pending_approvals')
    else:
        form = LeaveApprovalForm(instance=leave)
    
    return render(request, 'staff/approve_leave.html', {'form': form, 'leave': leave})

@login_required
@user_passes_test(is_hrmo)
def approve_promotion(request, pk):
    """Approve or reject promotion application"""
    promotion = get_object_or_404(Promotion, pk=pk, status='pending')
    
    if request.method == 'POST':
        form = PromotionApprovalForm(request.POST, instance=promotion)
        if form.is_valid():
            promotion = form.save(commit=False)
            promotion.approved_by = request.user
            promotion.approved_date = timezone.now()
            promotion.save()
            
            # If approved, update staff details
            if promotion.status == 'approved':
                staff = promotion.staff
                staff.position = promotion.new_position
                staff.department = promotion.new_department
                staff.staff_grade = promotion.new_grade
                staff.save()
            
            # Send notification to staff
            promotion.send_approval_notification()
            
            # Create workflow action
            action_type = 'promotion_approved' if promotion.status == 'approved' else 'promotion_rejected'
            WorkflowAction.objects.create(
                action_type=action_type,
                performed_by=request.user,
                staff_affected=promotion.staff,
                description=f'Promotion application {promotion.status}',
                content_type='promotion',
                object_id=promotion.id
            )
            
            messages.success(request, f'Promotion application {promotion.status} successfully!')
            return redirect('pending_approvals')
    else:
        form = PromotionApprovalForm(instance=promotion)
    
    return render(request, 'staff/approve_promotion.html', {'form': form, 'promotion': promotion})

@login_required
def staff_apply_leave(request):
    """Staff self-service leave application"""
    try:
        staff = Staff.objects.get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found. Please contact HR.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StaffLeaveApplicationForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.staff = staff
            leave.save()
            
            # Send notification to HRMOs
            leave.send_application_notification()
            
            messages.success(request, 'Leave application submitted successfully!')
            return redirect('my_leave_applications')
    else:
        form = StaffLeaveApplicationForm()
    
    return render(request, 'staff/staff_apply_leave.html', {'form': form})

@login_required
def my_leave_applications(request):
    """Staff view their own leave applications"""
    try:
        staff = Staff.objects.get(email=request.user.email)
        leaves = Leave.objects.filter(staff=staff).order_by('-applied_date')
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found. Please contact HR.')
        return redirect('dashboard')
    
    return render(request, 'staff/my_leave_applications.html', {'leaves': leaves})

# HRMO Management Views
@login_required
@user_passes_test(lambda u: u.is_superuser)
def hrmo_list(request):
    """List all HRMOs"""
    hrmos = HRMO.objects.select_related('staff', 'user').all()
    return render(request, 'staff/hrmo_list.html', {'hrmos': hrmos})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def hrmo_create(request):
    """Create new HRMO"""
    if request.method == 'POST':
        form = HRMOForm(request.POST)
        if form.is_valid():
            hrmo = form.save(commit=False)
            # Create user account for the staff member if not exists
            staff = hrmo.staff
            try:
                user = User.objects.get(email=staff.email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=staff.staff_id,
                    email=staff.email,
                    first_name=staff.first_name,
                    last_name=staff.last_name
                )
            hrmo.user = user
            hrmo.save()
            messages.success(request, 'HRMO created successfully!')
            return redirect('hrmo_list')
    else:
        form = HRMOForm()
    
    return render(request, 'staff/hrmo_form.html', {'form': form, 'title': 'Create HRMO'})

@login_required
def workflow_history(request):
    """View workflow action history"""
    actions = WorkflowAction.objects.select_related('performed_by', 'staff_affected').order_by('-timestamp')[:50]
    return render(request, 'staff/workflow_history.html', {'actions': actions})

@login_required
def notifications(request):
    """View user notifications"""
    user_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    # Mark as read
    user_notifications.update(is_read=True)
    return render(request, 'staff/notifications.html', {'notifications': user_notifications})

@login_required
def my_promotions(request):
    """Staff view their own promotions"""
    try:
        staff = Staff.objects.get(email=request.user.email)
        promotions = Promotion.objects.filter(staff=staff).order_by('-created_at')
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found. Please contact HR.')
        return redirect('dashboard')
    
    return render(request, 'staff/my_promotions.html', {'promotions': promotions})

@login_required
def my_profile(request):
    """Staff view their own profile"""
    try:
        staff = Staff.objects.get(email=request.user.email)
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found. Please contact HR.')
        return redirect('dashboard')
    
    return render(request, 'staff/my_profile.html', {'staff': staff})

@login_required
def staff_dashboard(request):
    """Dashboard for regular staff members"""
    try:
        staff = Staff.objects.get(email=request.user.email)
        
        # Get staff's own data
        my_leaves = Leave.objects.filter(staff=staff).order_by('-applied_date')[:5]
        my_promotions = Promotion.objects.filter(staff=staff).order_by('-created_at')[:3]
        
        # Statistics for this staff member
        pending_leaves = Leave.objects.filter(staff=staff, status='pending').count()
        approved_leaves_this_year = Leave.objects.filter(
            staff=staff, 
            status='approved',
            start_date__year=timezone.now().year
        ).count()
        
        context = {
            'staff': staff,
            'my_leaves': my_leaves,
            'my_promotions': my_promotions,
            'pending_leaves': pending_leaves,
            'approved_leaves_this_year': approved_leaves_this_year,
            'is_staff_dashboard': True,
        }
        
    except Staff.DoesNotExist:
        messages.error(request, 'Staff record not found. Please contact HR.')
        return redirect('login')
    
    return render(request, 'staff/staff_dashboard.html', context)