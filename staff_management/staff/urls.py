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

]