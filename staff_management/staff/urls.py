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
    
    # Workflow URLs
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('approve-leave/<int:pk>/', views.approve_leave, name='approve_leave'),
    path('approve-promotion/<int:pk>/', views.approve_promotion, name='approve_promotion'),
    path('apply-leave/', views.staff_apply_leave, name='staff_apply_leave'),
    path('my-leave-applications/', views.my_leave_applications, name='my_leave_applications'),
    path('workflow-history/', views.workflow_history, name='workflow_history'),
    path('notifications/', views.notifications, name='notifications'),
    
    # HRMO Management URLs
    path('hrmos/', views.hrmo_list, name='hrmo_list'),
    path('hrmos/add/', views.hrmo_create, name='hrmo_create'),
]