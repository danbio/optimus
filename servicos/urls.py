from django.urls import path

from . import views

app_name = "servicos"

urlpatterns = [
    # Propostas
    path("", views.PropostaListView.as_view(), name="lista"),
    path("nova/", views.PropostaCreateView.as_view(), name="nova"),
    path("<int:pk>/", views.PropostaDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.PropostaUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.PropostaDeleteView.as_view(), name="excluir"),
    # Transições de status
    path("<int:pk>/enviar/", views.enviar_proposta, name="enviar"),
    path("<int:pk>/aprovar/", views.aprovar_proposta, name="aprovar"),
    path("<int:pk>/cancelar/", views.cancelar_proposta, name="cancelar"),
    path("<int:pk>/reabrir/", views.reabrir_proposta, name="reabrir"),
    # Catálogo de serviços
    path("catalogo/", views.ServicoListView.as_view(), name="catalogo"),
    path("catalogo/novo/", views.ServicoCreateView.as_view(), name="catalogo_novo"),
    path("catalogo/<int:pk>/editar/", views.ServicoUpdateView.as_view(), name="catalogo_editar"),
    path(
        "catalogo/<int:pk>/excluir/",
        views.ServicoDeleteView.as_view(),
        name="catalogo_excluir",
    ),
    # API
    path("buscar-produtos/", views.buscar_produtos, name="buscar_produtos"),
]
