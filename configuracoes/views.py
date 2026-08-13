from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .forms import ConfiguracaoForm
from .models import Configuracao


@login_required
def editar(request: HttpRequest) -> HttpResponse:
    """Tela única de parâmetros de negócio. Acesso restrito ao grupo
    Administrador pelo middleware de RBAC (namespace 'configuracoes')."""
    config = Configuracao.atual()

    if request.method == "POST":
        form = ConfiguracaoForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configurações atualizadas.")
            return redirect("configuracoes:editar")
    else:
        form = ConfiguracaoForm(instance=config)

    return render(request, "configuracoes/configuracao_form.html", {"form": form})
