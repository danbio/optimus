from django.urls import path

from . import views

app_name = "balcao"

urlpatterns = [
    path("", views.VendaListView.as_view(), name="lista"),
    path("nova/", views.nova_venda, name="nova"),
    path("<int:pk>/", views.VendaDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.editar_venda, name="editar"),
    path("<int:pk>/finalizar/", views.finalizar_venda, name="finalizar"),
    path("<int:pk>/cancelar/", views.cancelar_venda, name="cancelar"),
    # HTMX endpoints
    path("<int:pk>/item/adicionar/", views.adicionar_item, name="item_adicionar"),
    path("<int:pk>/item/<int:item_pk>/remover/", views.remover_item, name="item_remover"),
    path("buscar-produto/", views.buscar_produto, name="buscar_produto"),
    path("buscar-cliente/", views.buscar_cliente, name="buscar_cliente"),
]
