from django.urls import path
from navigation import views

urlpatterns = [
    path("api/directory-import/", views.directory_import),
    path("api/session/", views.session),
    path("api/login/", views.sign_in),
    path("api/logout/", views.sign_out),
    path("api/dashboard/", views.dashboard),
    path("api/patients/<int:pk>/", views.workspace),
    path("api/patients/<int:pk>/actions/", views.action),
    path("api/patients/<int:pk>/export/", views.export_patient),
    path("api/organization/", views.organization),
    path("api/reports/", views.reports),
    path("api/audit/", views.audit_history),
]
