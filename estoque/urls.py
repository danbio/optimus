from django.urls import path

from . import views

app_name = "estoque"

urlpatterns = [
    path("", views.ProdutoListView.as_view(), name="lista"),
    path("novo/", views.ProdutoCreateView.as_view(), name="novo"),
    path("importar/", views.importar_tabela, name="importar"),
    path("<int:pk>/", views.ProdutoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ProdutoUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.ProdutoDeleteView.as_view(), name="excluir"),
]
