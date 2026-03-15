from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    path("", views.ClienteListView.as_view(), name="lista"),
    path("novo/", views.ClienteCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.ClienteDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.ClienteDeleteView.as_view(), name="excluir"),
    path("buscar-cep/", views.buscar_cep, name="buscar_cep"),
    path("buscar-cnpj/", views.buscar_cnpj, name="buscar_cnpj"),
]
