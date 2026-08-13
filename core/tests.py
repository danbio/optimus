"""Testes do app core — controle de acesso por grupo (RBAC) e settings."""

import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase, TestCase
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

    def test_sidebar_esconde_links_que_o_middleware_bloquearia(self) -> None:
        """Sem isso, quem não tem acesso via clica no link, chega até o
        middleware e só ali descobre que não pode — a navegação não avisa."""
        vendedor = User.objects.create_user(username="vend_side", password="senha-de-teste")
        vendedor.groups.add(Group.objects.get(name=GRUPO_VENDEDOR))
        self.client.force_login(vendedor)

        resposta = self.client.get(reverse("dashboard"))
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn("Financeiro", corpo)
        self.assertNotIn("Configurações", corpo)

    def test_sidebar_mostra_links_para_administrador(self) -> None:
        admin = User.objects.create_user(username="adm_side", password="senha-de-teste")
        admin.groups.add(Group.objects.get(name=GRUPO_ADMIN))
        self.client.force_login(admin)

        resposta = self.client.get(reverse("dashboard"))
        corpo = resposta.content.decode("utf-8")

        self.assertIn("Financeiro", corpo)
        self.assertIn("Configurações", corpo)


class DebugNuncaVazaParaProducaoTests(SimpleTestCase):
    """Trava a garantia de config/settings.py: DEBUG=True não pode chegar em
    produção, nem por variável de ambiente esquecida, nem por um .env de
    desenvolvimento parado no servidor por engano.

    Roda em subprocesso de propósito — settings já está carregado neste
    processo de teste, então é preciso um interpretador novo para observar o
    módulo sendo importado do zero sob variáveis de ambiente diferentes.
    """

    def _debug_em(self, env_extra: dict) -> bool:
        env = {**os.environ, **env_extra}
        # Isola de qualquer .env real do projeto: o teste decide sozinho o
        # ambiente, não deve depender do que estiver no disco.
        env.pop("DJANGO_ENV", None)
        env.update(env_extra)

        codigo = (
            "import django; django.setup(); "
            "from django.conf import settings; "
            "print('SIM' if settings.DEBUG else 'NAO')"
        )
        resultado = subprocess.run(
            [sys.executable, "-c", codigo],
            cwd=Path(settings.BASE_DIR),
            env={**env, "DJANGO_SETTINGS_MODULE": "config.settings"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            resultado.returncode, 0, f"settings.py falhou ao carregar: {resultado.stderr}"
        )
        return resultado.stdout.strip() == "SIM"

    def test_producao_normal_fica_com_debug_desligado(self) -> None:
        self.assertFalse(
            self._debug_em(
                {
                    "DJANGO_ENV": "production",
                    "SECRET_KEY": "x" * 50,
                    "ALLOWED_HOSTS": "erp.exemplo.com.br",
                }
            )
        )

    def test_producao_ignora_debug_true_setado_a_mao(self) -> None:
        """Reproduz o incidente real: alguém definiu DEBUG=True junto com
        DJANGO_ENV=production. A trava tem que vencer isso."""
        self.assertFalse(
            self._debug_em(
                {
                    "DJANGO_ENV": "production",
                    "SECRET_KEY": "x" * 50,
                    "ALLOWED_HOSTS": "erp.exemplo.com.br",
                    "DEBUG": "True",
                }
            )
        )

    def test_dev_sem_env_fica_com_debug_ligado(self) -> None:
        """Sem DJANGO_ENV=production, DEBUG é True por padrão — é o que faz
        o CSS/estáticos carregarem em dev sem precisar rodar collectstatic."""
        self.assertTrue(self._debug_em({}))
