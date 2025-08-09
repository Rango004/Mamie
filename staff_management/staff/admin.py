from django.contrib import admin
from .models import School, Department, Staff, Leave, Promotion, Retirement, Bereavement, HRMO, Notification, WorkflowAction

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'school', 'created_at']
    list_filter = ['school']
    search_fields = ['name', 'code']

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'full_name', 'department', 'position', 'staff_type', 'status']
    list_filter = ['department', 'staff_type', 'status']
    search_fields = ['staff_id', 'first_name', 'last_name', 'email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ['staff', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status']
    list_filter = ['leave_type', 'status']
    search_fields = ['staff__first_name', 'staff__last_name']

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['staff', 'old_position', 'new_position', 'effective_date']
    search_fields = ['staff__first_name', 'staff__last_name']

@admin.register(Retirement)
class RetirementAdmin(admin.ModelAdmin):
    list_display = ['staff', 'retirement_date', 'retirement_type']
    list_filter = ['retirement_type']
    search_fields = ['staff__first_name', 'staff__last_name']

@admin.register(Bereavement)
class BereavementAdmin(admin.ModelAdmin):
    list_display = ['staff', 'deceased_name', 'relationship', 'start_date', 'days_granted']
    search_fields = ['staff__first_name', 'staff__last_name', 'deceased_name']

@admin.register(HRMO)
class HRMOAdmin(admin.ModelAdmin):
    list_display = ['staff', 'user', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['staff__first_name', 'staff__last_name', 'user__username']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'recipient__username']

@admin.register(WorkflowAction)
class WorkflowActionAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'performed_by', 'staff_affected', 'timestamp']
    list_filter = ['action_type']
    search_fields = ['performed_by__username', 'staff_affected__first_name', 'staff_affected__last_name']