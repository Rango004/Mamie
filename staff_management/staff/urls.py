from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    
    # Staff URLs
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_update, name='staff_update'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),
    path('staff/<int:pk>/id-card/', views.print_id_card, name='print_id_card'),
    path('staff/<int:pk>/profile/', views.staff_profile_view, name='staff_profile_view'),
    path('register/', views.staff_register, name='staff_register'),
    
    # Leave URLs
    path('leaves/', views.leave_list, name='leave_list'),
    path('leaves/add/', views.leave_create, name='leave_create'),
    
    # Promotion URLs
    path('promotions/', views.promotion_list, name='promotion_list'),
    path('promotions/add/', views.promotion_create, name='promotion_create'),
    
    # Retirement URLs
    path('retirements/', views.retirement_list, name='retirement_list'),
    path('retirements/add/', views.retirement_create, name='retirement_create'),
    
    # Bereavement URLs
    path('bereavements/', views.bereavement_list, name='bereavement_list'),
    path('bereavements/add/', views.bereavement_create, name='bereavement_create'),
    
    # Staff self-service URLs
    path('my-profile/', views.my_profile, name='my_profile'),
    path('apply-promotion/', views.staff_apply_promotion, name='staff_apply_promotion'),
    path('update-photo/', views.update_profile_photo, name='update_profile_photo'),
    path('promotions/<int:pk>/approve/', views.approve_promotion, name='approve_promotion'),
    path('leaves/<int:pk>/approve/', views.approve_leave, name='approve_leave'),
    
    # School URLs
    path('schools/', views.school_list, name='school_list'),
    path('schools/add/', views.school_create, name='school_create'),
    path('schools/<int:pk>/edit/', views.school_update, name='school_update'),
    path('schools/<int:pk>/delete/', views.school_delete, name='school_delete'),
    
    # Department URLs
    path('departments/', views.department_list, name='department_list'),
    path('departments/add/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # Export URLs
    path('export/staff/csv/', views.export_staff_csv, name='export_staff_csv'),
    path('export/staff/pdf/', views.export_staff_pdf, name='export_staff_pdf'),
    
    # Bulk upload URLs
    path('bulk-upload/staff/', views.bulk_upload_staff, name='bulk_upload_staff'),
    path('bulk-upload/departments/', views.bulk_upload_departments, name='bulk_upload_departments'),
    path('bulk-upload/schools/', views.bulk_upload_schools, name='bulk_upload_schools'),
    
    # Retirement management URLs
    path('retirement/settings/', views.retirement_settings, name='retirement_settings'),
    path('retirement/notifications/', views.check_retirement_notifications, name='check_retirement_notifications'),
    
    # Contract renewal URLs
    path('contract-renewals/', views.check_contract_renewals, name='check_contract_renewals'),
    
    # Staff grade management URLs
    path('grades/', views.staff_grade_list, name='staff_grade_list'),
    path('grades/add/', views.staff_grade_create, name='staff_grade_create'),
    path('grades/<int:pk>/edit/', views.staff_grade_update, name='staff_grade_update'),
    
    # Announcement URLs
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    
    # HRMO Management URLs
    path('hrmo/', views.hrmo_list, name='hrmo_list'),
    path('hrmo/add/', views.hrmo_create, name='hrmo_create'),
    path('hrmo/<int:pk>/toggle/', views.hrmo_toggle, name='hrmo_toggle'),
]