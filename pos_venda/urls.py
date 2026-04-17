from django.urls import path

from . import views

app_name = "pos_venda"

urlpatterns = [
    path("", views.ChamadoListView.as_view(), name="lista"),
    path("novo/", views.ChamadoCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.ChamadoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ChamadoUpdateView.as_view(), name="editar"),
    path("<int:pk>/status/", views.mudar_status, name="mudar_status"),
    path("<int:pk>/interacao/", views.adicionar_interacao, name="adicionar_interacao"),
    path("cliente/<int:cliente_pk>/historico/", views.historico_cliente, name="historico_cliente"),
]
