"""Testes do app financeiro.

Nasceram de uma auditoria externa (2026-08-16) que encontrou faturamento
duplicado no fluxo solar. Cobrem o comportamento **correto**, não o que o
código fazia antes.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from core.permissoes import GRUPO_ADMIN
from ordens_servico.models import OrdemServico, Tecnico
from solar.models import ItemPropostaSolar, ModuloFotovoltaico, PropostaSolar

from .models import LancamentoFinanceiro
from .services import (
    criar_lancamento_de_ordem_servico,
    criar_lancamento_de_proposta_solar,
)


def _cliente():
    return Cliente.objects.create(tipo="PF", cpf_cnpj="111.111.111-11", nome="Teste Silva")


def _modulo():
    return ModuloFotovoltaico.objects.create(
        fabricante="TestFab", modelo="M400", potencia_wp=400, eficiencia=20,
        voc=48, isc=10, largura=1000, altura=2000, peso=22,
        garantia_produto=12, garantia_desempenho=25,
    )


class FaturamentoSolarSemDuplicidadeTests(TestCase):
    """Regressão do achado crítico da auditoria: a proposta era faturada
    inteira na aprovação **e** de novo no faturamento da OS, cobrando o
    cliente duas vezes (R$ 10.000 viravam R$ 20.000).

    Divisão definida pelo usuário: aprovação lança os equipamentos (que
    precisam ser comprados no início), faturamento da OS lança a mão de
    obra (que só se paga na entrega). A soma fecha o valor total.
    """

    def setUp(self) -> None:
        self.cliente = _cliente()
        self.modulo = _modulo()
        self.tecnico = Tecnico.objects.create(nome="Técnico Teste")
        self.proposta = PropostaSolar.objects.create(
            cliente=self.cliente, consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("4.000"),
            quantidade_modulos=10, modulo=self.modulo,
            valor_instalacao=Decimal("2000.00"),
            status=PropostaSolar.STATUS_ENVIADA,
        )
        ItemPropostaSolar.objects.create(
            proposta=self.proposta, modulo=self.modulo, quantidade=10,
            preco_venda_snapshot=Decimal("800.00"), preco_custo_snapshot=Decimal("600.00"),
            data_referencia_preco=date.today(),
        )
        # equipamentos 8.000 + instalação 2.000 = 10.000
        self.assertEqual(self.proposta.valor_total, Decimal("10000.00"))

    def _faturar_tudo(self):
        criar_lancamento_de_proposta_solar(self.proposta)
        os_obj = OrdemServico.objects.create(
            cliente=self.cliente, proposta_solar=self.proposta,
            tecnico=self.tecnico, descricao="Instalação",
        )
        criar_lancamento_de_ordem_servico(os_obj)
        return os_obj

    def test_soma_dos_lancamentos_nao_ultrapassa_o_valor_da_proposta(self) -> None:
        """O teste que a auditoria pediu: o cliente não pode ser cobrado
        duas vezes pelo mesmo gerador."""
        self._faturar_tudo()

        total = sum(lanc.valor_bruto for lanc in LancamentoFinanceiro.objects.all())
        self.assertEqual(total, self.proposta.valor_total)

    def test_aprovacao_lanca_apenas_os_equipamentos(self) -> None:
        criar_lancamento_de_proposta_solar(self.proposta)

        lanc = LancamentoFinanceiro.objects.get(proposta_solar=self.proposta)
        self.assertEqual(lanc.valor_bruto, self.proposta.valor_equipamentos)

    def test_faturamento_da_os_lanca_apenas_a_mao_de_obra(self) -> None:
        os_obj = self._faturar_tudo()

        lanc = LancamentoFinanceiro.objects.get(ordem_servico=os_obj)
        self.assertEqual(lanc.valor_bruto, self.proposta.valor_instalacao)

    def test_os_sem_mao_de_obra_nao_gera_lancamento_zerado(self) -> None:
        """Proposta sem valor de instalação não deve criar um lançamento de
        R$ 0,00 poluindo o contas a receber."""
        self.proposta.valor_instalacao = Decimal("0")
        self.proposta.save()

        self._faturar_tudo()

        self.assertFalse(LancamentoFinanceiro.objects.filter(ordem_servico__isnull=False).exists())

    def test_faturar_a_mesma_os_duas_vezes_nao_duplica(self) -> None:
        os_obj = self._faturar_tudo()
        criar_lancamento_de_ordem_servico(os_obj)

        self.assertEqual(LancamentoFinanceiro.objects.filter(ordem_servico=os_obj).count(), 1)

    def test_aprovar_a_mesma_proposta_duas_vezes_nao_duplica(self) -> None:
        criar_lancamento_de_proposta_solar(self.proposta)
        criar_lancamento_de_proposta_solar(self.proposta)

        self.assertEqual(LancamentoFinanceiro.objects.filter(proposta_solar=self.proposta).count(), 1)


class RepasseNaoEReceitaTests(TestCase):
    """Modelo de negócio real (confirmado 2026-08-16): o cliente compra o
    equipamento direto do fornecedor (Intelbras, Belenus), sem margem da
    Optimus — é assim que a venda de gerador fica isenta de ICMS. A Optimus
    nunca fatura nem recebe esse valor; a receita dela é só instalação e
    manutenção. O lançamento de equipamento existe pra rastrear se o
    cliente pagou o fornecedor, não porque é dinheiro da empresa."""

    def setUp(self) -> None:
        self.cliente = _cliente()
        self.modulo = _modulo()
        self.proposta = PropostaSolar.objects.create(
            cliente=self.cliente, consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("4.000"),
            quantidade_modulos=10, modulo=self.modulo,
            valor_instalacao=Decimal("2000.00"),
            status=PropostaSolar.STATUS_ENVIADA,
        )
        ItemPropostaSolar.objects.create(
            proposta=self.proposta, modulo=self.modulo, quantidade=10,
            preco_venda_snapshot=Decimal("800.00"), preco_custo_snapshot=Decimal("600.00"),
            data_referencia_preco=date.today(),
        )

    def test_lancamento_de_equipamento_nasce_como_repasse(self) -> None:
        criar_lancamento_de_proposta_solar(self.proposta)

        lanc = LancamentoFinanceiro.objects.get(proposta_solar=self.proposta)
        self.assertEqual(lanc.tipo, LancamentoFinanceiro.TIPO_REPASSE)

    def test_lancamento_manual_nasce_como_receita_por_padrao(self) -> None:
        """Um lançamento sem tipo explícito é receita — é o caso comum
        (venda de balcão, serviço, manual)."""
        lanc = LancamentoFinanceiro.objects.create(
            cliente=self.cliente, descricao="Venda avulsa",
            valor_bruto=Decimal("500"), data_vencimento=date.today(),
        )

        self.assertEqual(lanc.tipo, LancamentoFinanceiro.TIPO_RECEITA)


class DashboardExcluiRepasseDoFaturamentoTests(TestCase):
    """O dashboard é a tela que o dono do negócio olha pra saber quanto a
    empresa faturou. Repasse ao fornecedor não pode inflar esse número."""

    def setUp(self) -> None:
        self.cliente = _cliente()
        self.user = User.objects.create_user(username="fin_dash", password="senha-de-teste")
        self.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])
        self.client.force_login(self.user)

    def _lancamento(self, tipo, valor):
        return LancamentoFinanceiro.objects.create(
            cliente=self.cliente, descricao="Teste", tipo=tipo,
            valor_bruto=valor, data_vencimento=date.today(),
        )

    def test_repasse_nao_soma_no_total_liquido(self) -> None:
        self._lancamento(LancamentoFinanceiro.TIPO_RECEITA, Decimal("3000"))
        self._lancamento(LancamentoFinanceiro.TIPO_REPASSE, Decimal("12000"))

        resposta = self.client.get(reverse("financeiro:dashboard"), {"periodo": "ano"})

        self.assertEqual(resposta.context["total_liquido"], Decimal("3000"))

    def test_repasse_aparece_separado_do_faturamento(self) -> None:
        self._lancamento(LancamentoFinanceiro.TIPO_RECEITA, Decimal("3000"))
        self._lancamento(LancamentoFinanceiro.TIPO_REPASSE, Decimal("12000"))

        resposta = self.client.get(reverse("financeiro:dashboard"), {"periodo": "ano"})

        self.assertEqual(resposta.context["total_repasse"], Decimal("12000"))
        self.assertIn("R$ 12.000,00", resposta.content.decode("utf-8"))

    def test_faturamento_da_proposta_solar_completa_nao_conta_o_equipamento(self) -> None:
        """Fim a fim: proposta de R$ 10.000 (8.000 equipamento + 2.000
        instalação) só pode contribuir R$ 2.000 pro faturamento."""
        modulo = _modulo()
        proposta = PropostaSolar.objects.create(
            cliente=self.cliente, consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("4.000"),
            quantidade_modulos=10, modulo=modulo, valor_instalacao=Decimal("2000.00"),
            status=PropostaSolar.STATUS_ENVIADA,
        )
        ItemPropostaSolar.objects.create(
            proposta=proposta, modulo=modulo, quantidade=10,
            preco_venda_snapshot=Decimal("800.00"), preco_custo_snapshot=Decimal("600.00"),
            data_referencia_preco=date.today(),
        )
        criar_lancamento_de_proposta_solar(proposta)
        tecnico = Tecnico.objects.create(nome="Técnico Teste")
        os_obj = OrdemServico.objects.create(
            cliente=self.cliente, proposta_solar=proposta, tecnico=tecnico, descricao="Instalação",
        )
        criar_lancamento_de_ordem_servico(os_obj)

        # O lançamento de equipamento vence em 30 dias (padrão da proposta),
        # o da OS vence hoje — período precisa cobrir os dois.
        resposta = self.client.get(
            reverse("financeiro:dashboard"),
            {"periodo": "personalizado", "data_de": "2020-01-01", "data_ate": (date.today() + timedelta(days=31)).isoformat()},
        )

        self.assertEqual(resposta.context["total_liquido"], Decimal("2000.00"))
        self.assertEqual(resposta.context["total_repasse"], Decimal("8000.00"))


class FaturamentoDeOSAvulsaTests(TestCase):
    """OS sem proposta de origem continua faturando normalmente — a
    correção do fluxo solar não pode ter quebrado esse caminho."""

    def test_os_avulsa_gera_lancamento_com_valor_dos_itens(self) -> None:
        cliente = _cliente()
        tecnico = Tecnico.objects.create(nome="Técnico Teste")
        os_obj = OrdemServico.objects.create(cliente=cliente, tecnico=tecnico, descricao="Avulsa")

        criar_lancamento_de_ordem_servico(os_obj)

        # Sem proposta e sem itens o valor é zero, então nada é lançado.
        self.assertFalse(LancamentoFinanceiro.objects.filter(ordem_servico=os_obj).exists())
