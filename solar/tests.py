"""Testes do app solar."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from clientes.models import Cliente

from .admin import PrecoEquipamentoSolarAdmin
from .models import (
    EstruturaFixacao,
    Inversor,
    ItemPropostaSolar,
    MateriaisEletricos,
    ModuloFotovoltaico,
    PrecoEquipamentoSolar,
    PropostaSolar,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _modulo():
    return ModuloFotovoltaico.objects.create(
        fabricante="TestFab",
        modelo="M400",
        potencia_wp=400,
        eficiencia=20,
        voc=48,
        isc=10,
        largura=1000,
        altura=2000,
        peso=22,
        garantia_produto=12,
        garantia_desempenho=25,
    )


def _inversor():
    return Inversor.objects.create(
        fabricante="TestFab",
        modelo="INV5K",
        potencia_kw=5,
        tipo=Inversor.TIPO_STRING,
        fase=Inversor.FASE_MONO,
        tensao_max_entrada=600,
        quantidade_mppt=2,
        garantia=5,
    )


def _estrutura():
    return EstruturaFixacao.objects.create(
        fabricante="TestFab",
        modelo="EST-C",
        tipo=EstruturaFixacao.TELHADO_CERAMICO,
        material=EstruturaFixacao.MATERIAL_ALUMINIO,
    )


def _cliente():
    return Cliente.objects.create(tipo="PF", cpf_cnpj="111.111.111-11", nome="Teste Silva")


def _preco(equipamento, venda, custo=None, desde=None, ate=None, user=None):
    if user is None:
        user = User.objects.get_or_create(username="admin_test")[0]
    kwargs = dict(
        preco_custo=custo or venda,
        preco_venda=venda,
        vigente_desde=desde or date.today(),
        vigente_ate=ate,
        criado_por=user,
    )
    if isinstance(equipamento, ModuloFotovoltaico):
        kwargs["modulo"] = equipamento
    elif isinstance(equipamento, Inversor):
        kwargs["inversor"] = equipamento
    elif isinstance(equipamento, EstruturaFixacao):
        kwargs["estrutura"] = equipamento
    else:
        kwargs["material"] = equipamento
    return PrecoEquipamentoSolar.objects.create(**kwargs)


def _proposta(modulo, inversor=None, estrutura=None, cliente=None):
    return PropostaSolar.objects.create(
        cliente=cliente or _cliente(),
        consumo_medio_kwh=350,
        hsp=Decimal("5.50"),
        fator_eficiencia=Decimal("0.75"),
        potencia_kwp=Decimal("5.000"),
        quantidade_modulos=10,
        modulo=modulo,
        valor_instalacao=Decimal("2000.00"),
    )


# ---------------------------------------------------------------------------
# Testes de PrecoEquipamentoSolar.get_preco_vigente
# ---------------------------------------------------------------------------


class GetPrecoVigenteTest(TestCase):
    def setUp(self):
        self.modulo = _modulo()
        self.user = User.objects.create_user("tester")

    def test_retorna_preco_atual(self):
        preco = _preco(self.modulo, venda=Decimal("5000"), user=self.user)
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.modulo, date.today())
        self.assertEqual(resultado, preco)

    def test_retorna_none_sem_preco(self):
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.modulo, date.today())
        self.assertIsNone(resultado)

    def test_ignora_preco_ainda_nao_vigente(self):
        _preco(self.modulo, venda=Decimal("5000"), desde=date.today() + timedelta(days=1), user=self.user)
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.modulo, date.today())
        self.assertIsNone(resultado)

    def test_ignora_preco_expirado(self):
        ontem = date.today() - timedelta(days=1)
        _preco(
            self.modulo,
            venda=Decimal("5000"),
            desde=date.today() - timedelta(days=30),
            ate=ontem,
            user=self.user,
        )
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.modulo, date.today())
        self.assertIsNone(resultado)

    def test_retorna_preco_correto_entre_dois(self):
        ontem = date.today() - timedelta(days=1)
        _preco(self.modulo, venda=Decimal("4000"), desde=date.today() - timedelta(days=60), ate=ontem, user=self.user)
        preco_atual = _preco(self.modulo, venda=Decimal("5000"), user=self.user)
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.modulo, date.today())
        self.assertEqual(resultado, preco_atual)

    def test_funciona_para_inversor(self):
        inversor = _inversor()
        preco = _preco(inversor, venda=Decimal("3000"), user=self.user)
        resultado = PrecoEquipamentoSolar.get_preco_vigente(inversor, date.today())
        self.assertEqual(resultado, preco)

    def test_funciona_para_estrutura(self):
        estrutura = _estrutura()
        preco = _preco(estrutura, venda=Decimal("800"), user=self.user)
        resultado = PrecoEquipamentoSolar.get_preco_vigente(estrutura, date.today())
        self.assertEqual(resultado, preco)


# ---------------------------------------------------------------------------
# Testes de PropostaSolar.valor_equipamentos (property calculada)
# ---------------------------------------------------------------------------


class ValorEquipamentosPropertyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester2")
        self.modulo = _modulo()
        self.inversor = _inversor()
        self.estrutura = _estrutura()

    def test_valor_zero_sem_itens(self):
        proposta = PropostaSolar.objects.create(
            cliente=_cliente(),
            consumo_medio_kwh=350,
            hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"),
            potencia_kwp=Decimal("5.000"),
            quantidade_modulos=10,
            modulo=self.modulo,
            valor_instalacao=Decimal("0"),
        )
        self.assertEqual(proposta.valor_equipamentos, Decimal("0.00"))

    def test_soma_itens(self):
        proposta = _proposta(self.modulo, self.inversor, self.estrutura)
        proposta.itens.all().delete()
        ItemPropostaSolar.objects.create(
            proposta=proposta,
            modulo=self.modulo,
            quantidade=10,
            preco_venda_snapshot=Decimal("600"),
            preco_custo_snapshot=Decimal("500"),
            data_referencia_preco=date.today(),
        )
        ItemPropostaSolar.objects.create(
            proposta=proposta,
            inversor=self.inversor,
            quantidade=1,
            preco_venda_snapshot=Decimal("4000"),
            preco_custo_snapshot=Decimal("3000"),
            data_referencia_preco=date.today(),
        )
        # 10 × 600 + 1 × 4000 = 10000
        self.assertEqual(proposta.valor_equipamentos, Decimal("10000.00"))

    def test_valor_total_inclui_instalacao(self):
        proposta = _proposta(self.modulo, self.inversor, self.estrutura)
        proposta.itens.all().delete()
        ItemPropostaSolar.objects.create(
            proposta=proposta,
            modulo=self.modulo,
            quantidade=1,
            preco_venda_snapshot=Decimal("1000"),
            preco_custo_snapshot=Decimal("800"),
            data_referencia_preco=date.today(),
        )
        # valor_equipamentos=1000, valor_instalacao=2000 → total=3000
        self.assertEqual(proposta.valor_total, Decimal("3000.00"))


# ---------------------------------------------------------------------------
# Testes de criação automática de itens ao salvar nova proposta
# ---------------------------------------------------------------------------


class SnapshotItemTest(TestCase):
    """Testa criação de ItemPropostaSolar com snapshot de preço correto."""

    def setUp(self):
        self.user = User.objects.create_user("tester3")
        self.modulo = _modulo()
        self.inversor = _inversor()
        _preco(self.modulo, venda=Decimal("600"), custo=Decimal("500"), user=self.user)
        _preco(self.inversor, venda=Decimal("4000"), custo=Decimal("3200"), user=self.user)
        self.proposta = _proposta(self.modulo)

    def _item(self, **kwargs):
        defaults = dict(
            proposta=self.proposta,
            quantidade=1,
            preco_venda_snapshot=Decimal("0"),
            preco_custo_snapshot=Decimal("0"),
            data_referencia_preco=date.today(),
        )
        defaults.update(kwargs)
        return ItemPropostaSolar.objects.create(**defaults)

    def test_item_modulo_snapshot_correto(self):
        preco = PrecoEquipamentoSolar.get_preco_vigente(self.modulo, date.today())
        item = self._item(
            modulo=self.modulo,
            quantidade=10,
            preco_venda_snapshot=preco.preco_venda,
            preco_custo_snapshot=preco.preco_custo,
        )
        self.assertEqual(item.preco_venda_snapshot, Decimal("600"))
        self.assertEqual(item.preco_custo_snapshot, Decimal("500"))
        self.assertEqual(item.quantidade, 10)

    def test_snapshot_zero_sem_preco_cadastrado(self):
        modulo_sem_preco = ModuloFotovoltaico.objects.create(
            fabricante="SemPreco",
            modelo="X100",
            potencia_wp=100,
            eficiencia=15,
            voc=30,
            isc=5,
            largura=800,
            altura=1600,
            peso=15,
            garantia_produto=5,
            garantia_desempenho=10,
        )
        preco = PrecoEquipamentoSolar.get_preco_vigente(modulo_sem_preco, date.today())
        snapshot = preco.preco_venda if preco else Decimal("0")
        item = self._item(modulo=modulo_sem_preco, preco_venda_snapshot=snapshot)
        self.assertEqual(item.preco_venda_snapshot, Decimal("0"))

    def test_valor_equipamentos_soma_itens(self):
        self._item(modulo=self.modulo, quantidade=10, preco_venda_snapshot=Decimal("600"), preco_custo_snapshot=Decimal("500"))
        self._item(inversor=self.inversor, quantidade=1, preco_venda_snapshot=Decimal("4000"), preco_custo_snapshot=Decimal("3200"))
        # 10 × 600 + 1 × 4000 = 10000
        self.assertEqual(self.proposta.valor_equipamentos, Decimal("10000.00"))


# ---------------------------------------------------------------------------
# Testes do Admin: auto-fechamento do preço anterior
# ---------------------------------------------------------------------------


class AdminAutoFechaPrecoAnteriorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin_adm", password="pass")
        self.modulo = _modulo()
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = PrecoEquipamentoSolarAdmin(PrecoEquipamentoSolar, self.site)

    def _request(self):
        req = self.factory.get("/admin/")
        req.user = self.user
        return req

    def test_fecha_preco_anterior_ao_salvar_novo(self):
        preco_antigo = _preco(self.modulo, venda=Decimal("5000"), user=self.user)
        self.assertIsNone(preco_antigo.vigente_ate)

        novo = PrecoEquipamentoSolar(
            modulo=self.modulo,
            preco_custo=Decimal("4500"),
            preco_venda=Decimal("5500"),
            vigente_desde=date.today(),
        )
        self.admin.save_model(self._request(), novo, form=None, change=False)
        novo.save()

        preco_antigo.refresh_from_db()
        self.assertEqual(preco_antigo.vigente_ate, date.today())

    def test_nao_altera_precos_de_outro_equipamento(self):
        outro_modulo = ModuloFotovoltaico.objects.create(
            fabricante="Outro",
            modelo="O200",
            potencia_wp=200,
            eficiencia=18,
            voc=40,
            isc=8,
            largura=900,
            altura=1800,
            peso=19,
            garantia_produto=10,
            garantia_desempenho=20,
        )
        preco_outro = _preco(outro_modulo, venda=Decimal("3000"), user=self.user)

        novo = PrecoEquipamentoSolar(
            modulo=self.modulo,
            preco_custo=Decimal("4500"),
            preco_venda=Decimal("5500"),
            vigente_desde=date.today(),
        )
        self.admin.save_model(self._request(), novo, form=None, change=False)
        novo.save()

        preco_outro.refresh_from_db()
        self.assertIsNone(preco_outro.vigente_ate)


# ---------------------------------------------------------------------------
# Testes de MateriaisEletricos em get_preco_vigente e admin auto-close
# ---------------------------------------------------------------------------


def _material():
    return MateriaisEletricos.objects.create(
        fabricante="TestFab",
        modelo="CBT-6mm",
        categoria=MateriaisEletricos.CATEGORIA_CABO,
        unidade=MateriaisEletricos.UNIDADE_METRO,
    )


class GetPrecoVigenteMateriaisTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester_mat")
        self.material = _material()

    def test_funciona_para_material(self):
        preco = _preco(self.material, venda=Decimal("15"), user=self.user)
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.material, date.today())
        self.assertEqual(resultado, preco)

    def test_retorna_none_sem_preco_material(self):
        resultado = PrecoEquipamentoSolar.get_preco_vigente(self.material, date.today())
        self.assertIsNone(resultado)


class AdminAutoFechaPrecoAnteriorMateriaisTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin_mat", password="pass")
        self.material = _material()
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = PrecoEquipamentoSolarAdmin(PrecoEquipamentoSolar, self.site)

    def _request(self):
        req = self.factory.get("/admin/")
        req.user = self.user
        return req

    def test_fecha_preco_anterior_material(self):
        preco_antigo = _preco(self.material, venda=Decimal("12"), user=self.user)
        self.assertIsNone(preco_antigo.vigente_ate)

        novo = PrecoEquipamentoSolar(
            material=self.material,
            preco_custo=Decimal("10"),
            preco_venda=Decimal("15"),
            vigente_desde=date.today(),
        )
        self.admin.save_model(self._request(), novo, form=None, change=False)
        novo.save()

        preco_antigo.refresh_from_db()
        self.assertEqual(preco_antigo.vigente_ate, date.today())
