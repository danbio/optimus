from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import DashboardView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # Apps
    path("clientes/", include("clientes.urls")),
    # Raiz redireciona para dashboard (exige login)
    path("", DashboardView.as_view(), name="home"),
]
