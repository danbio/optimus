from django.urls import path

from . import views

app_name = "ordens_servico"

urlpatterns = [
    # Ordens de Serviço
    path("", views.OrdemServicoListView.as_view(), name="lista"),
    path("nova/", views.OrdemServicoCreateView.as_view(), name="nova"),
    path("<int:pk>/", views.OrdemServicoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.OrdemServicoUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.OrdemServicoDeleteView.as_view(), name="excluir"),
    # Transições de estado
    path("<int:pk>/agendar/", views.agendar_os, name="agendar"),
    path("<int:pk>/iniciar/", views.iniciar_os, name="iniciar"),
    path("<int:pk>/concluir/", views.concluir_os, name="concluir"),
    path("<int:pk>/suspender/", views.suspender_os, name="suspender"),
    path("<int:pk>/reagendar/", views.reagendar_os, name="reagendar"),
    # Checklist toggle
    path("<int:pk>/checklist/<int:item_pk>/toggle/", views.toggle_checklist_item, name="toggle_checklist"),
    # Fotos
    path("<int:pk>/foto/adicionar/", views.adicionar_foto, name="adicionar_foto"),
    path("<int:pk>/foto/<int:foto_pk>/remover/", views.remover_foto, name="remover_foto"),
    # Técnicos
    path("tecnicos/", views.TecnicoListView.as_view(), name="tecnicos"),
    path("tecnicos/novo/", views.TecnicoCreateView.as_view(), name="tecnico_novo"),
    path("tecnicos/<int:pk>/editar/", views.TecnicoUpdateView.as_view(), name="tecnico_editar"),
    path("tecnicos/<int:pk>/excluir/", views.TecnicoDeleteView.as_view(), name="tecnico_excluir"),
    # API
    path("carregar-checklist/", views.carregar_checklist_template, name="carregar_checklist"),
]
