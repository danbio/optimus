"""Middleware de controle de acesso por grupo.

Aplica a matriz de `core.permissoes` a todas as rotas de uma vez, em vez de
espalhar mixins por ~115 views. Views continuam responsáveis por exigir login
(LoginRequiredMixin / @login_required); este middleware cuida apenas de *qual
grupo* pode entrar em cada módulo.
"""

from collections.abc import Callable

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from core.permissoes import usuario_pode_acessar


class ControleDeAcessoPorGrupoMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., HttpResponse],
        view_args: tuple,
        view_kwargs: dict,
    ) -> None:
        # Anônimo é problema do LoginRequired, não daqui: deixar passar para que
        # o usuário seja redirecionado ao login em vez de tomar um 403 seco.
        if not request.user.is_authenticated:
            return None

        match = request.resolver_match
        if match is None:
            return None

        # Rotas sem namespace (dashboard, login, logout, home) são liberadas a
        # qualquer usuário autenticado.
        if not match.namespace:
            return None

        if not usuario_pode_acessar(request.user, match.namespace, match.url_name):
            raise PermissionDenied

        return None
