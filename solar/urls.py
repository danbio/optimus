from django.urls import path

from . import views

app_name = "solar"

urlpatterns = [
    path("", views.PropostaSolarListView.as_view(), name="lista"),
    path("nova/", views.PropostaSolarCreateView.as_view(), name="nova"),
    path("<int:pk>/", views.PropostaSolarDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.PropostaSolarUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.PropostaSolarDeleteView.as_view(), name="excluir"),
    # Transições de status
    path("<int:pk>/enviar/", views.enviar_proposta, name="enviar"),
    path("<int:pk>/aprovar/", views.aprovar_proposta, name="aprovar"),
    path("<int:pk>/cancelar/", views.cancelar_proposta, name="cancelar"),
    path("<int:pk>/reabrir/", views.reabrir_proposta, name="reabrir"),
    # HTMX
    path("dimensionar/", views.dimensionar, name="dimensionar"),
    path("adicionar-item/", views.adicionar_item_solar, name="adicionar_item"),
    path("calcular-total/", views.calcular_total_equipamentos, name="calcular_total"),
    # Catálogo — Módulos
    path("modulos/", views.ModuloListView.as_view(), name="modulos"),
    path("modulos/novo/", views.ModuloCreateView.as_view(), name="modulo_novo"),
    path("modulos/<int:pk>/editar/", views.ModuloUpdateView.as_view(), name="modulo_editar"),
    path("modulos/<int:pk>/excluir/", views.ModuloDeleteView.as_view(), name="modulo_excluir"),
    path("modulos/<int:pk>/precos/", views.modulo_precos, name="modulo_precos"),
    # Catálogo — Inversores
    path("inversores/", views.InversorListView.as_view(), name="inversores"),
    path("inversores/novo/", views.InversorCreateView.as_view(), name="inversor_novo"),
    path("inversores/<int:pk>/editar/", views.InversorUpdateView.as_view(), name="inversor_editar"),
    path("inversores/<int:pk>/excluir/", views.InversorDeleteView.as_view(), name="inversor_excluir"),
    path("inversores/<int:pk>/precos/", views.inversor_precos, name="inversor_precos"),
    # Catálogo — Estruturas
    path("estruturas/", views.EstruturaListView.as_view(), name="estruturas"),
    path("estruturas/novo/", views.EstruturaCreateView.as_view(), name="estrutura_nova"),
    path("estruturas/<int:pk>/editar/", views.EstruturaUpdateView.as_view(), name="estrutura_editar"),
    path("estruturas/<int:pk>/excluir/", views.EstruturaDeleteView.as_view(), name="estrutura_excluir"),
    path("estruturas/<int:pk>/precos/", views.estrutura_precos, name="estrutura_precos"),
    # Catálogo — Materiais Elétricos
    path("materiais/", views.MateriaisListView.as_view(), name="materiais"),
    path("materiais/novo/", views.MateriaisCreateView.as_view(), name="material_novo"),
    path("materiais/<int:pk>/editar/", views.MateriaisUpdateView.as_view(), name="material_editar"),
    path("materiais/<int:pk>/excluir/", views.MateriaisDeleteView.as_view(), name="material_excluir"),
    path("materiais/<int:pk>/precos/", views.material_precos, name="material_precos"),
]
