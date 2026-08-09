"""Controle de acesso por grupo (RBAC) do ERP Optimus.

A matriz de acesso vive **inteiramente neste arquivo**. Para mudar quem enxerga
qual módulo, edite `ACESSO_POR_MODULO` ou `ACESSO_POR_ROTA` — nenhuma view
precisa ser alterada. A checagem é feita pelo middleware
`core.middleware.ControleDeAcessoPorGrupoMiddleware`, que identifica o módulo
pelo namespace da URL (não pelo caminho em texto), então renomear uma rota não
quebra a regra.
"""

from django.contrib.auth.models import AbstractUser

GRUPO_ADMIN = "Administrador"
GRUPO_VENDEDOR = "Vendedor"
GRUPO_TECNICO = "Técnico"

GRUPOS: tuple[str, ...] = (GRUPO_ADMIN, GRUPO_VENDEDOR, GRUPO_TECNICO)

TODOS = frozenset(GRUPOS)
COMERCIAL = frozenset({GRUPO_ADMIN, GRUPO_VENDEDOR})
SOMENTE_ADMIN = frozenset({GRUPO_ADMIN})

# Namespace do app (app_name em <app>/urls.py) -> grupos com acesso.
# Módulo ausente desta tabela fica liberado para qualquer usuário autenticado.
ACESSO_POR_MODULO: dict[str, frozenset[str]] = {
    "clientes": TODOS,  # técnico precisa de endereço e contato para ir a campo
    "ordens_servico": TODOS,  # é o trabalho do técnico
    "pos_venda": TODOS,  # técnico atende chamado de garantia
    "estoque": COMERCIAL,  # expõe preço de custo (psd) e margem
    "solar": COMERCIAL,  # propostas; o catálogo é restrito abaixo
    "servicos": COMERCIAL,
    "balcao": COMERCIAL,
    "financeiro": SOMENTE_ADMIN,
    "admin": SOMENTE_ADMIN,  # admin do Django
}

# Exceções mais finas dentro de um módulo: (namespace, prefixo do nome da rota).
# O catálogo solar cadastra equipamento e preço de custo — só Administrador,
# mesmo que o Vendedor tenha acesso ao resto do app solar (propostas).
ACESSO_POR_ROTA: dict[tuple[str, str], frozenset[str]] = {
    ("solar", "modulo"): SOMENTE_ADMIN,
    ("solar", "inversor"): SOMENTE_ADMIN,
    ("solar", "estrutura"): SOMENTE_ADMIN,
    ("solar", "material"): SOMENTE_ADMIN,
}


def grupos_permitidos(namespace: str, url_name: str | None) -> frozenset[str] | None:
    """Grupos que podem acessar a rota. `None` significa sem restrição."""
    if url_name:
        for (ns, prefixo), grupos in ACESSO_POR_ROTA.items():
            if ns == namespace and url_name.startswith(prefixo):
                return grupos
    return ACESSO_POR_MODULO.get(namespace)


def usuario_pode_acessar(user: AbstractUser, namespace: str, url_name: str | None) -> bool:
    """Se o usuário pode acessar a rota indicada.

    Superusuário passa sempre — é a conta de resgate caso a matriz trave alguém
    para fora por engano.
    """
    if user.is_superuser:
        return True

    grupos = grupos_permitidos(namespace, url_name)
    if grupos is None:
        return True

    return user.groups.filter(name__in=grupos).exists()
