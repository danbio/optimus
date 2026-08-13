from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.permissoes import GRUPO_ADMIN, GRUPO_VENDEDOR

from .models import Configuracao


class ConfiguracaoSingletonTests(TestCase):
    def test_atual_cria_com_valores_padrao_na_primeira_chamada(self) -> None:
        self.assertEqual(Configuracao.objects.count(), 0)
        config = Configuracao.atual()
        self.assertEqual(config.pk, 1)
        self.assertEqual(config.desconto_maximo_balcao_pct, Decimal("20.00"))

    def test_atual_sempre_retorna_a_mesma_linha(self) -> None:
        primeira = Configuracao.atual()
        primeira.desconto_maximo_balcao_pct = Decimal("15.00")
        primeira.save()

        segunda = Configuracao.atual()

        self.assertEqual(segunda.pk, 1)
        self.assertEqual(segunda.desconto_maximo_balcao_pct, Decimal("15.00"))
        self.assertEqual(Configuracao.objects.count(), 1)

    def test_save_direto_sem_atual_ainda_cai_em_pk_1(self) -> None:
        """Mesmo bypassando atual() na primeira gravação (uso indevido, mas
        possível), não sobra criando linha com outro id."""
        self.assertEqual(Configuracao.objects.count(), 0)
        obj = Configuracao(desconto_maximo_balcao_pct=Decimal("5.00"))
        obj.save()

        self.assertEqual(obj.pk, 1)
        self.assertEqual(Configuracao.objects.count(), 1)
        self.assertEqual(Configuracao.atual().desconto_maximo_balcao_pct, Decimal("5.00"))

    def test_nao_pode_ser_excluida(self) -> None:
        config = Configuracao.atual()
        with self.assertRaises(Exception):
            config.delete()
        self.assertEqual(Configuracao.objects.count(), 1)


class ConfiguracaoAcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        Group.objects.get_or_create(name=GRUPO_ADMIN)
        Group.objects.get_or_create(name=GRUPO_VENDEDOR)

    def test_administrador_acessa_e_salva(self) -> None:
        user = User.objects.create_user(username="dono", password="senha-de-teste")
        user.groups.add(Group.objects.get(name=GRUPO_ADMIN))
        self.client.force_login(user)

        resposta = self.client.post(
            reverse("configuracoes:editar"), {"desconto_maximo_balcao_pct": "12.50"}
        )

        self.assertRedirects(resposta, reverse("configuracoes:editar"))
        self.assertEqual(Configuracao.atual().desconto_maximo_balcao_pct, Decimal("12.50"))

    def test_vendedor_nao_acessa(self) -> None:
        user = User.objects.create_user(username="vendedor", password="senha-de-teste")
        user.groups.add(Group.objects.get(name=GRUPO_VENDEDOR))
        self.client.force_login(user)

        resposta = self.client.get(reverse("configuracoes:editar"))

        self.assertEqual(resposta.status_code, 403)

    def test_valor_fora_de_0_a_100_e_rejeitado(self) -> None:
        user = User.objects.create_user(username="dono2", password="senha-de-teste")
        user.groups.add(Group.objects.get(name=GRUPO_ADMIN))
        self.client.force_login(user)

        resposta = self.client.post(
            reverse("configuracoes:editar"), {"desconto_maximo_balcao_pct": "150"}
        )

        self.assertEqual(resposta.status_code, 200)  # re-renderiza com erro, não redireciona
        self.assertContains(resposta, "form-error")
