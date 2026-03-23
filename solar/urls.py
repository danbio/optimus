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
]
