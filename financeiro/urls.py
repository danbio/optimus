from django.urls import path

from . import views

app_name = "financeiro"

urlpatterns = [
    path("", views.LancamentoListView.as_view(), name="lista"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("novo/", views.LancamentoCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.LancamentoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.LancamentoUpdateView.as_view(), name="editar"),
    path("<int:pk>/cancelar/", views.cancelar_lancamento, name="cancelar"),
    path("<int:pk>/baixa/", views.registrar_baixa, name="baixa"),
    path("<int:pk>/baixa/form/", views.form_baixa_htmx, name="baixa_form"),
]
