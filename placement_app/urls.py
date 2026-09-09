from django.urls import path
from placement_app import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('students/', views.student_list_view, name='student_list'),
    path('students/add/', views.student_create_view, name='student_create'),
    path('students/import/', views.import_excel_view, name='import_excel'),
    path('students/<int:pk>/', views.student_detail_view, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_update_view, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete_view, name='student_delete'),
    path('students/bulk-delete/', views.student_bulk_delete_view, name='student_bulk_delete'),
    
    path('companies/', views.company_list_view, name='company_list'),
    path('companies/add/', views.company_create_view, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_update_view, name='company_edit'),
    path('companies/<int:pk>/delete/', views.company_delete_view, name='company_delete'),
    
    path('drives/', views.drive_list_view, name='drive_list'),
    path('drives/add/', views.drive_create_view, name='drive_create'),
    path('drives/<int:pk>/', views.drive_detail_view, name='drive_detail'),
    path('drives/<int:pk>/edit/', views.drive_update_view, name='drive_edit'),
    path('drives/<int:pk>/delete/', views.drive_delete_view, name='drive_delete'),
    path('drives/<int:pk>/complete/', views.drive_complete_view, name='drive_complete'),
    path('drives/<int:pk>/add-students/', views.drive_add_students_view, name='drive_add_students'),
    path('drives/<int:pk>/remove-student/<int:student_id>/', views.drive_remove_student_view, name='drive_remove_student'),
    
    path('departments/', views.department_list_view, name='department_list'),
    path('departments/<int:pk>/edit/', views.department_update_view, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete_view, name='department_delete'),
    path('departments/bulk-delete/', views.department_bulk_delete_view, name='department_bulk_delete'),

    path('reports/selection/', views.selection_report_view, name='selection_report'),
    path('reports/', views.reports_hub_view, name='reports_hub'),
    
    path('login/', views.login_user_view, name='login'),
    path('logout/', views.logout_user_view, name='logout'),
]
