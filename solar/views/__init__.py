# solar/views/__init__.py
# Subpacote de views — re-exporta tudo para compatibilidade com urls.py
#
# urls.py continua usando `from . import views` e `views.NomeView` normalmente.

from .catalogo import (  # noqa: F401
    EstruturaCreateView,
    EstruturaDeleteView,
    EstruturaListView,
    EstruturaUpdateView,
    InversorCreateView,
    InversorDeleteView,
    InversorListView,
    InversorUpdateView,
    MateriaisCreateView,
    MateriaisDeleteView,
    MateriaisListView,
    MateriaisUpdateView,
    ModuloCreateView,
    ModuloDeleteView,
    ModuloListView,
    ModuloUpdateView,
)
from .precos import (  # noqa: F401
    estrutura_precos,
    inversor_precos,
    material_precos,
    modulo_precos,
)
from .propostas import (  # noqa: F401
    PropostaSolarCreateView,
    PropostaSolarDeleteView,
    PropostaSolarDetailView,
    PropostaSolarListView,
    PropostaSolarUpdateView,
    adicionar_item_solar,
    aprovar_proposta,
    calcular_total_equipamentos,
    cancelar_proposta,
    dimensionar,
    enviar_proposta,
    proposta_print,
    reabrir_proposta,
)
