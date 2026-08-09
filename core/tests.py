"""Testes do app core — controle de acesso por grupo (RBAC)."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.permissoes import (
    GRUPO_ADMIN,
    GRUPO_TECNICO,
    GRUPO_VENDEDOR,
    GRUPOS,
    grupos_permitidos,
    usuario_pode_acessar,
)


class MatrizDeAcessoTests(TestCase):
    """Testa a matriz isoladamente, sem passar por HTTP."""

    @classmethod
    def setUpTestData(cls) -> None:
        for nome in GRUPOS:
            Group.objects.get_or_create(name=nome)

    def _usuario(self, grupo: str | None = None, superuser: bool = False) -> User:
        user = User.objects.create_user(
            username=f"u{User.objects.count()}", password="x", is_superuser=superuser
        )
        if grupo:
            user.groups.add(Group.objects.get(name=grupo))
        return user

    def test_financeiro_e_exclusivo_do_administrador(self) -> None:
        self.assertTrue(usuario_pode_acessar(self._usuario(GRUPO_ADMIN), "financeiro", "lista"))
        self.assertFalse(usuario_pode_acessar(self._usuario(GRUPO_VENDEDOR), "financeiro", "lista"))
        self.assertFalse(usuario_pode_acessar(self._usuario(GRUPO_TECNICO), "financeiro", "lista"))

    def test_tecnico_nao_entra_no_estoque_nem_no_balcao(self) -> None:
        tecnico = self._usuario(GRUPO_TECNICO)
        self.assertFalse(usuario_pode_acessar(tecnico, "estoque", "lista"))
        self.assertFalse(usuario_pode_acessar(tecnico, "balcao", "lista"))

    def test_tecnico_acessa_os_clientes_e_pos_venda(self) -> None:
        tecnico = self._usuario(GRUPO_TECNICO)
        self.assertTrue(usuario_pode_acessar(tecnico, "ordens_servico", "lista"))
        self.assertTrue(usuario_pode_acessar(tecnico, "clientes", "lista"))
        self.assertTrue(usuario_pode_acessar(tecnico, "pos_venda", "lista"))

    def test_vendedor_faz_proposta_solar_mas_nao_edita_catalogo(self) -> None:
        """O catálogo expõe preço de custo — exceção por rota dentro do app solar."""
        vendedor = self._usuario(GRUPO_VENDEDOR)
        self.assertTrue(usuario_pode_acessar(vendedor, "solar", "lista"))
        self.assertTrue(usuario_pode_acessar(vendedor, "solar", "dimensionar"))
        self.assertFalse(usuario_pode_acessar(vendedor, "solar", "modulos"))
        self.assertFalse(usuario_pode_acessar(vendedor, "solar", "inversor_precos"))
        self.assertFalse(usuario_pode_acessar(vendedor, "solar", "material_novo"))

    def test_administrador_acessa_o_catalogo(self) -> None:
        admin = self._usuario(GRUPO_ADMIN)
        self.assertTrue(usuario_pode_acessar(admin, "solar", "modulos"))
        self.assertTrue(usuario_pode_acessar(admin, "solar", "inversor_precos"))

    def test_superusuario_passa_em_tudo(self) -> None:
        """Conta de resgate: se a matriz travar todo mundo, o dono ainda entra."""
        root = self._usuario(superuser=True)
        self.assertTrue(usuario_pode_acessar(root, "financeiro", "lista"))
        self.assertTrue(usuario_pode_acessar(root, "solar", "modulos"))
        self.assertTrue(usuario_pode_acessar(root, "admin", "index"))

    def test_usuario_sem_grupo_nao_acessa_modulo_restrito(self) -> None:
        self.assertFalse(usuario_pode_acessar(self._usuario(), "financeiro", "lista"))

    def test_modulo_fora_da_matriz_fica_liberado(self) -> None:
        self.assertIsNone(grupos_permitidos("modulo_inexistente", "lista"))
        self.assertTrue(usuario_pode_acessar(self._usuario(), "modulo_inexistente", "lista"))


class MiddlewareDeAcessoTests(TestCase):
    """Testa o bloqueio de verdade, via requisição HTTP."""

    @classmethod
    def setUpTestData(cls) -> None:
        for nome in GRUPOS:
            Group.objects.get_or_create(name=nome)

    def test_vendedor_recebe_403_no_financeiro(self) -> None:
        user = User.objects.create_user(username="vendedor", password="senha-de-teste")
        user.groups.add(Group.objects.get(name=GRUPO_VENDEDOR))
        self.client.force_login(user)

        resposta = self.client.get(reverse("financeiro:lista"))

        self.assertEqual(resposta.status_code, 403)

    def test_administrador_entra_no_financeiro(self) -> None:
        user = User.objects.create_user(username="dono", password="senha-de-teste")
        user.groups.add(Group.objects.get(name=GRUPO_ADMIN))
        self.client.force_login(user)

        resposta = self.client.get(reverse("financeiro:lista"))

        self.assertEqual(resposta.status_code, 200)

    def test_anonimo_vai_para_login_e_nao_toma_403(self) -> None:
        """Middleware não deve sequestrar o fluxo de login."""
        resposta = self.client.get(reverse("financeiro:lista"))

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login/", resposta.url)

    def test_dashboard_sem_namespace_fica_liberado(self) -> None:
        user = User.objects.create_user(username="tecnico", password="senha-de-teste")
        user.groups.add(Group.objects.get(name=GRUPO_TECNICO))
        self.client.force_login(user)

        resposta = self.client.get(reverse("dashboard"))

        self.assertEqual(resposta.status_code, 200)
