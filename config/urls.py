from django.conf import settings
from django.conf.urls.static import static
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
    path("estoque/", include("estoque.urls")),
    path("solar/", include("solar.urls")),
    path("servicos/", include("servicos.urls")),
    path("os/", include("ordens_servico.urls")),
    # Raiz redireciona para dashboard (exige login)
    path("", DashboardView.as_view(), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
