"""Cria os grupos de acesso do ERP.

Idempotente: rodar de novo não duplica nem apaga usuários já vinculados.
O vínculo usuário -> grupo é feito no admin do Django (/admin/auth/user/).
"""

from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.permissoes import ACESSO_POR_MODULO, ACESSO_POR_ROTA, GRUPOS


class Command(BaseCommand):
    help = "Cria os grupos de acesso (Administrador, Vendedor, Técnico)."

    def handle(self, *args: Any, **options: Any) -> None:
        for nome in GRUPOS:
            _, criado = Group.objects.get_or_create(name=nome)
            situacao = "criado" if criado else "já existia"
            self.stdout.write(f"  {nome:15} — {situacao}")

        self.stdout.write("")
        self.stdout.write("Acesso por módulo:")
        for namespace, grupos in sorted(ACESSO_POR_MODULO.items()):
            self.stdout.write(f"  {namespace:16} {', '.join(sorted(grupos))}")

        self.stdout.write("")
        self.stdout.write("Exceções por rota:")
        for (namespace, prefixo), grupos in sorted(ACESSO_POR_ROTA.items()):
            self.stdout.write(f"  {namespace}:{prefixo + '*':14} {', '.join(sorted(grupos))}")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Grupos prontos. Vincule os usuários em /admin/auth/user/.")
        )
