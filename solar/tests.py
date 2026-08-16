"""Testes do app solar."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from clientes.models import Cliente
from core.permissoes import GRUPO_ADMIN

from .admin import PrecoEquipamentoSolarAdmin
from .aneel import consolidar_tarifas
from .forms import PropostaSolarForm
from .models import (
    Distribuidora,
    EstruturaFixacao,
    Inversor,
    ItemPropostaSolar,
    MateriaisEletricos,
    ModuloFotovoltaico,
    Municipio,
    PrecoEquipamentoSolar,
    PropostaSolar,
    TarifaDistribuidora,
    TaxaCartao,
)
from .services import (
    aplicar_tributos,
    formatar_prazo,
    grafico_economia_anual,
    grafico_geracao_mensal,
    percentual_fio_b,
    projetar_retorno,
)
from .views._helpers import calcular_parcela_cartao

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


class DimensionamentoConectadoAosItensTests(TestCase):
    """Regressão do bug: PropostaSolarForm não incluía o campo `modulo`, então
    o dropdown "Módulo de referência" renderizava vazio (label sem <select>),
    o botão Calcular nunca enviava o módulo escolhido, e o preview travava
    sempre em "selecione o módulo". Cobre a correção + a conexão nova entre
    calculadora e tabela de itens (botão "Usar este dimensionamento")."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.modulo = _modulo()  # 400 Wp, ver helper no topo do arquivo
        cls.user = User.objects.create_user(username="vend_solar", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_form_de_proposta_inclui_campo_modulo(self) -> None:
        from .forms import PropostaSolarForm

        self.assertIn("modulo", PropostaSolarForm.Meta.fields)

    def test_tela_de_nova_proposta_renderiza_o_select_de_modulo(self) -> None:
        resposta = self.client.get(reverse("solar:nova"))
        corpo = resposta.content.decode("utf-8")

        self.assertIn('id="id_modulo"', corpo)
        self.assertIn(f'value="{self.modulo.pk}"', corpo)

    def test_dimensionar_com_modulo_calcula_quantidade_sugerida(self) -> None:
        resposta = self.client.get(
            reverse("solar:dimensionar"),
            {"consumo_medio_kwh": "500", "hsp": "5.5", "fator_eficiencia": "0.75", "modulo": self.modulo.pk},
        )
        corpo = resposta.content.decode("utf-8")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("unidades", corpo)
        self.assertIn("Usar este dimensionamento", corpo)

    def test_dimensionar_sem_modulo_nao_calcula_quantidade(self) -> None:
        """Sem módulo selecionado, só dá pra saber o kWp necessário — não tem
        como sugerir quantidade (depende da potência do módulo)."""
        resposta = self.client.get(
            reverse("solar:dimensionar"),
            {"consumo_medio_kwh": "500", "hsp": "5.5", "fator_eficiencia": "0.75"},
        )
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn("unidades", corpo)
        self.assertIn("Selecione o módulo", corpo)

    def test_usar_dimensionamento_preenche_item_com_modulo_e_quantidade(self) -> None:
        resposta = self.client.get(
            reverse("solar:adicionar_item"),
            {"index": "0", "modulo": self.modulo.pk, "quantidade": "13"},
        )
        corpo = resposta.content.decode("utf-8")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('value="13"', corpo)
        self.assertIn(f'<option value="{self.modulo.pk}" selected>', corpo)
        self.assertIn('combo-modulo" style="display: block', corpo)

    def test_adicionar_item_sem_parametros_continua_vazio(self) -> None:
        """O botão manual "Adicionar Item" não deve ganhar pré-preenchimento
        por acidente. O "selected" na opção vazia é comportamento padrão do
        Django em <select> sem valor — o que não pode aparecer é o módulo
        marcado, nem quantidade diferente do default (1)."""
        resposta = self.client.get(reverse("solar:adicionar_item"), {"index": "0"})
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn(f'value="{self.modulo.pk}" selected', corpo)
        self.assertIn('name="itens-0-quantidade" value="1"', corpo)
        self.assertIn('combo-modulo" style="display: none', corpo)

    def test_criar_proposta_com_item_de_modulo_grava_modulo_e_quantidade(self) -> None:
        """Fim a fim: submete o form como o formulário real envia (dimensionamento
        + 1 item de módulo) e confirma que a proposta grava potencia_kwp,
        modulo e quantidade_modulos corretamente."""
        cliente = _cliente()
        dados = {
            "cliente": cliente.pk,
            "consumo_medio_kwh": "500",
            "modulo": self.modulo.pk,
            "hsp": "5.5",
            "fator_eficiencia": "0.75",
            "valor_instalacao": "0",
            "tipo_ligacao": PropostaSolar.LIGACAO_MONOFASICO,
            "autoconsumo_simultaneo_pct": "25",
            "validade": (date.today() + timedelta(days=30)).isoformat(),
            "observacoes": "",
            "itens-TOTAL_FORMS": "1",
            "itens-INITIAL_FORMS": "0",
            "itens-MIN_NUM_FORMS": "1",
            "itens-MAX_NUM_FORMS": "1000",
            "itens-0-modulo": self.modulo.pk,
            "itens-0-quantidade": "13",
        }

        resposta = self.client.post(reverse("solar:nova"), dados)

        self.assertEqual(resposta.status_code, 302, resposta.context["formset"].errors if resposta.status_code == 200 else "")
        proposta = PropostaSolar.objects.latest("criado_em")
        self.assertEqual(proposta.modulo_id, self.modulo.pk)
        self.assertEqual(proposta.quantidade_modulos, 13)
        self.assertGreater(proposta.potencia_kwp, 0)


# ---------------------------------------------------------------------------
# Sugestão automática de inversor compatível
# ---------------------------------------------------------------------------


class InversoresCompativeisHelperTests(TestCase):
    """Testa a função pura, sem HTTP — regra: potência do sistema ÷ potência
    do inversor precisa cair dentro da faixa configurada em Configuracao."""

    def setUp(self) -> None:
        from .views._helpers import inversores_compativeis

        self.fn = inversores_compativeis
        self.inv_5k = Inversor.objects.create(
            fabricante="TestFab", modelo="5K", potencia_kw=Decimal("5.00"),
            tensao_max_entrada=600, quantidade_mppt=2, garantia=5,
        )
        self.inv_2k = Inversor.objects.create(
            fabricante="TestFab", modelo="2K", potencia_kw=Decimal("2.00"),
            tensao_max_entrada=600, quantidade_mppt=2, garantia=5,
        )
        self.inv_inativo = Inversor.objects.create(
            fabricante="TestFab", modelo="INATIVO", potencia_kw=Decimal("5.00"),
            tensao_max_entrada=600, quantidade_mppt=2, garantia=5, ativo=False,
        )

    def test_marca_compativel_dentro_da_faixa(self) -> None:
        # 6.1 kWp / 5 kW = 122% — dentro de 80%-135%
        resultado = self.fn(Decimal("6.1"), Decimal("80"), Decimal("135"))
        item_5k = next(r for r in resultado if r["inversor"] == self.inv_5k)
        self.assertTrue(item_5k["compativel"])
        self.assertEqual(item_5k["ratio_pct"], Decimal("122.0"))

    def test_marca_incompativel_fora_da_faixa(self) -> None:
        # 6.1 kWp / 2 kW = 305% — muito acima de 135%
        resultado = self.fn(Decimal("6.1"), Decimal("80"), Decimal("135"))
        item_2k = next(r for r in resultado if r["inversor"] == self.inv_2k)
        self.assertFalse(item_2k["compativel"])

    def test_ignora_inversor_inativo(self) -> None:
        resultado = self.fn(Decimal("6.1"), Decimal("80"), Decimal("135"))
        pks = [r["inversor"].pk for r in resultado]
        self.assertNotIn(self.inv_inativo.pk, pks)

    def test_ordena_compativeis_primeiro_por_proximidade_de_100pct(self) -> None:
        resultado = self.fn(Decimal("6.1"), Decimal("80"), Decimal("135"))
        self.assertEqual(resultado[0]["inversor"], self.inv_5k)  # 122%, compatível
        self.assertEqual(resultado[-1]["inversor"], self.inv_2k)  # 305%, pior caso

    def test_kwp_zero_ou_negativo_retorna_lista_vazia(self) -> None:
        self.assertEqual(self.fn(Decimal("0"), Decimal("80"), Decimal("135")), [])
        self.assertEqual(self.fn(Decimal("-1"), Decimal("80"), Decimal("135")), [])

    def test_entrada_invalida_nao_quebra(self) -> None:
        self.assertEqual(self.fn("não é número", Decimal("80"), Decimal("135")), [])
        self.assertEqual(self.fn(None, Decimal("80"), Decimal("135")), [])


class DimensionarComInversorSugeridoTests(TestCase):
    """Integração via HTTP: o endpoint dimensionar precisa combinar o
    dimensionamento com a configuração salva em Configuracao."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.modulo = _modulo()  # 400 Wp
        cls.inversor = _inversor()  # 5 kW
        cls.user = User.objects.create_user(username="vend_inv", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_preview_mostra_inversor_dentro_da_faixa_padrao(self) -> None:
        # 700 kWh/mês, HSP 5.5, fator 0.75 -> 15 módulos de 400W = 6.0 kWp real.
        # 6.0 / 5 (potência do inversor) = 120% — dentro da faixa padrão 80%-135%.
        resposta = self.client.get(
            reverse("solar:dimensionar"),
            {"consumo_medio_kwh": "700", "hsp": "5.5", "fator_eficiencia": "0.75", "modulo": self.modulo.pk},
        )
        corpo = resposta.content.decode("utf-8")

        self.assertIn("Inversores compat", corpo)
        self.assertIn(self.inversor.modelo, corpo)
        self.assertIn('class="badge badge-verde"', corpo)

    def test_link_configuracoes_some_para_quem_nao_e_administrador(self) -> None:
        from core.permissoes import GRUPO_VENDEDOR

        vendedor = User.objects.create_user(username="vend_sem_admin", password="senha-de-teste")
        vendedor.groups.add(Group.objects.get_or_create(name=GRUPO_VENDEDOR)[0])
        self.client.force_login(vendedor)

        resposta = self.client.get(
            reverse("solar:dimensionar"),
            {"consumo_medio_kwh": "700", "hsp": "5.5", "fator_eficiencia": "0.75", "modulo": self.modulo.pk},
        )
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn('href="/configuracoes/"', corpo)

    def test_usar_este_inversor_preenche_item_com_o_inversor(self) -> None:
        resposta = self.client.get(
            reverse("solar:adicionar_item"), {"index": "0", "inversor": self.inversor.pk}
        )
        corpo = resposta.content.decode("utf-8")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'<option value="{self.inversor.pk}" selected>', corpo)
        self.assertIn('combo-inversor" style="display: block', corpo)


# ---------------------------------------------------------------------------
# Impressão / PDF da proposta (etapa 5 do fluxo)
# ---------------------------------------------------------------------------


class PropostaPrintTests(TestCase):
    """window.print() do navegador é o "gerador de PDF" — sem biblioteca
    externa. Ver .claude/skills/solar-domain.md §12."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.modulo = _modulo()
        cls.inversor = _inversor()
        cls.estrutura = _estrutura()
        # _proposta() só grava o módulo de referência (FK direta) — os itens
        # da tabela de equipamentos precisam ser criados à parte, senão o
        # teste só exercita o caminho "proposta vazia" do template.
        cls.proposta = _proposta(cls.modulo)
        ItemPropostaSolar.objects.create(
            proposta=cls.proposta, modulo=cls.modulo, quantidade=10,
            preco_venda_snapshot=Decimal("600"), preco_custo_snapshot=Decimal("500"),
            data_referencia_preco=date.today(),
        )
        ItemPropostaSolar.objects.create(
            proposta=cls.proposta, inversor=cls.inversor, quantidade=1,
            preco_venda_snapshot=Decimal("4000"), preco_custo_snapshot=Decimal("3000"),
            data_referencia_preco=date.today(),
        )
        cls.user = User.objects.create_user(username="vend_print", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_pagina_de_impressao_carrega(self) -> None:
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))

        self.assertEqual(resposta.status_code, 200)

    def test_nao_usa_o_layout_com_menu_lateral(self) -> None:
        """A página de impressão precisa ficar fora do base.html normal —
        imprimir a barra lateral e o menu junto com a proposta seria um
        documento inutilizável pro cliente."""
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn('class="sidebar"', corpo)
        self.assertNotIn('class="topbar"', corpo)
        self.assertNotIn("htmx.org", corpo)

    def test_sem_comentario_de_template_vazando_no_html(self) -> None:
        """Regressão: {# comentário #} multi-linha do Django NÃO é
        reconhecido como comentário (só funciona numa linha só — usar
        {% comment %}...{% endcomment %} pra várias linhas). O template
        antigo vazou o texto do comentário direto pro documento que iria
        pro cliente.

        Com tarifa preenchida de propósito: sem ela as seções de retorno e
        o gráfico nem renderizam, e foi exatamente por isso que este teste
        deixou passar um segundo vazamento no bloco do gráfico."""
        self.proposta.tarifa_kwh = Decimal("1.385750")
        self.proposta.save()

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn("{#", corpo)
        self.assertNotIn("#}", corpo)

    def test_sem_comentario_vazando_tambem_sem_tarifa(self) -> None:
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn("{#", corpo)
        self.assertNotIn("#}", corpo)

    def test_mostra_numero_cliente_e_total(self) -> None:
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn(self.proposta.numero, corpo)
        self.assertIn(self.proposta.cliente.nome, corpo)
        self.assertIn("R$ 12.000,00", corpo)  # valor total da proposta

    def test_tabela_de_equipamentos_lista_os_itens(self) -> None:
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn(self.modulo.modelo, corpo)
        self.assertIn(self.inversor.modelo, corpo)

    def test_tabela_de_equipamentos_nao_mostra_preco_por_item(self) -> None:
        """Preço só aparece no total (seção Investimento) — o cliente não
        vê a composição de preço por peça, decisão de negócio do usuário."""
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn("Vlr. unit", corpo)
        self.assertNotIn("Subtotal", corpo)
        # Preço por item seria 600 (módulo) ou 4000 (inversor) — nenhum dos
        # dois deve aparecer fora da seção de Investimento (que soma tudo).
        # Com USE_THOUSAND_SEPARATOR, 4000 renderiza "4.000,00": a asserção
        # antiga ("R$ 4000,00") passou a nunca casar, virando teste vazio.
        self.assertNotIn("R$ 600,00", corpo)
        self.assertNotIn("R$ 4.000,00", corpo)

    def test_investimento_mostra_so_o_total(self) -> None:
        """O cliente vê um preço único — sem quebra entre equipamento e mão
        de obra. Decisão de negócio do usuário."""
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        # itens: 10×600 + 1×4000 = 10.000 de equipamento, 2.000 de instalação
        self.assertEqual(self.proposta.valor_total, Decimal("12000.00"))
        self.assertIn("Valor do Investimento", corpo)
        self.assertIn("R$ 12.000,00", corpo)
        self.assertNotIn("R$ 10.000,00", corpo)
        self.assertNotIn("R$ 2.000,00", corpo)
        self.assertNotIn("Instalação e mão de obra", corpo)

    def test_proposta_inexistente_retorna_404(self) -> None:
        resposta = self.client.get(reverse("solar:imprimir", args=[99999]))

        self.assertEqual(resposta.status_code, 404)

    def test_vendedor_tambem_acessa_impressao(self) -> None:
        """Impressão segue o mesmo nível de acesso do resto do app solar
        (Administrador + Vendedor) — não é uma tela mais restrita."""
        from core.permissoes import GRUPO_VENDEDOR

        vendedor = User.objects.create_user(username="vend_print2", password="senha-de-teste")
        vendedor.groups.add(Group.objects.get_or_create(name=GRUPO_VENDEDOR)[0])
        self.client.force_login(vendedor)

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))

        self.assertEqual(resposta.status_code, 200)

    def test_link_imprimir_aparece_na_tela_de_detalhe(self) -> None:
        resposta = self.client.get(reverse("solar:detalhe", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn(reverse("solar:imprimir", args=[self.proposta.pk]), corpo)

    def test_retorno_financeiro_nao_aparece_sem_tarifa(self) -> None:
        """Sem tarifa_kwh informada, a seção some do PDF — não inventa
        número de payback/economia sem dado real do cliente."""
        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertNotIn("Retorno do investimento", corpo)

    def test_retorno_financeiro_aparece_com_tarifa_informada(self) -> None:
        self.proposta.tarifa_kwh = Decimal("1.385750")
        self.proposta.save()

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn("Retorno do investimento", corpo)
        self.assertIn("Investimento pago em", corpo)
        self.assertIn("Economia acumulada em 25 anos", corpo)

    def test_grafico_de_barras_e_svg_inline_sem_biblioteca(self) -> None:
        """O PDF sai por window.print(): o gráfico precisa ser SVG servido
        no próprio HTML, não um <script> de biblioteca que a janela de
        impressão pode não ter tempo de executar."""
        self.proposta.tarifa_kwh = Decimal("1.385750")
        self.proposta.save()

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn("Economia projetada ano a ano", corpo)
        self.assertIn("<svg", corpo)
        self.assertIn("doc-grafico", corpo)
        self.assertNotIn("<script", corpo)

    def test_rotulo_do_grafico_diz_que_o_valor_e_anual(self) -> None:
        """O usuário olhou o gráfico e não soube dizer se "R$ 12.355" era
        mensal, anual ou acumulado — valor sem unidade é ambíguo."""
        self.proposta.tarifa_kwh = Decimal("1.385750")
        self.proposta.save()

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertRegex(corpo, r"class=\"g-valor\"[^>]*>R\$ [\d.]+/ano<")
        self.assertIn("naquele ano", corpo)

    def test_svg_nao_sofre_localizacao_de_numero(self) -> None:
        """Regressão: com USE_THOUSAND_SEPARATOR=True o template localiza
        qualquer número que receba — o viewBox virou "680,0" e o ano virou
        "2.026", quebrando o gráfico. As coordenadas e os anos precisam sair
        de services.py já como string."""
        import re
        import xml.etree.ElementTree as ET

        self.proposta.tarifa_kwh = Decimal("1.385750")
        self.proposta.save()

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")
        svg = re.search(r"<svg.*?</svg>", corpo, re.S).group(0)

        ET.fromstring(svg)  # levanta se o SVG estiver malformado
        self.assertNotRegex(
            svg,
            r'(?:x|y|x1|y1|x2|y2|width|height)="[-\d]+,',
            msg="coordenada com vírgula decimal — número foi localizado",
        )
        self.assertRegex(svg, r'class="g-ano"[^>]*>\d{4}<', msg="ano não pode levar separador de milhar")

    def test_pdf_explica_a_memoria_de_calculo_da_lei_14300(self) -> None:
        """O cliente detalhista precisa ver de onde saiu o número — e o Fio B
        precisa estar explícito, não escondido dentro do total."""
        self.proposta.tarifa_kwh = Decimal("1.385750")
        self.proposta.save()

        resposta = self.client.get(reverse("solar:imprimir", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn("Como esta conta foi feita", corpo)
        self.assertIn("Fio B", corpo)
        self.assertIn("Lei 14.300/2022", corpo)
        self.assertIn("Mínimo faturado pela distribuidora", corpo)


# ---------------------------------------------------------------------------
# Resumo de fechamento (copiar/colar) — geracao_mensal_kwh, inversor_principal
# ---------------------------------------------------------------------------


class PropriedadesDeResumoTests(TestCase):
    def setUp(self) -> None:
        self.modulo = _modulo()  # 400 Wp
        self.inversor = _inversor()  # 5 kW

    def test_geracao_mensal_kwh_calcula_a_partir_de_kwp_hsp_e_fator(self) -> None:
        proposta = PropostaSolar.objects.create(
            cliente=_cliente(), consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("4.000"),
            quantidade_modulos=10, modulo=self.modulo, valor_instalacao=Decimal("0"),
        )
        # potencia_real_kwp = 10 * 400 / 1000 = 4.0 kWp
        # geracao = 4.0 * 5.5 * 30 * 0.75 = 495
        self.assertEqual(proposta.geracao_mensal_kwh, 495)

    def test_geracao_mensal_kwh_zero_sem_modulo(self) -> None:
        proposta = PropostaSolar.objects.create(
            cliente=_cliente(), consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("0"),
            quantidade_modulos=0, valor_instalacao=Decimal("0"),
        )
        self.assertEqual(proposta.geracao_mensal_kwh, 0)

    def test_inversor_principal_pega_o_primeiro_item_com_inversor(self) -> None:
        proposta = _proposta(self.modulo)
        self.assertIsNone(proposta.inversor_principal)

        ItemPropostaSolar.objects.create(
            proposta=proposta, inversor=self.inversor, quantidade=1,
            preco_venda_snapshot=Decimal("4000"), preco_custo_snapshot=Decimal("3000"),
            data_referencia_preco=date.today(),
        )
        self.assertEqual(proposta.inversor_principal, self.inversor)

    def test_quantidade_inversores_soma_os_itens_de_inversor(self) -> None:
        proposta = _proposta(self.modulo)
        self.assertEqual(proposta.quantidade_inversores, 0)

        ItemPropostaSolar.objects.create(
            proposta=proposta, inversor=self.inversor, quantidade=2,
            preco_venda_snapshot=Decimal("4000"), preco_custo_snapshot=Decimal("3000"),
            data_referencia_preco=date.today(),
        )
        self.assertEqual(proposta.quantidade_inversores, 2)


class PercentualFioBTests(TestCase):
    """Escala do art. 27 da Lei 14.300/2022."""

    def test_escala_legal_ano_a_ano(self) -> None:
        esperado = {
            2023: Decimal("0.15"), 2024: Decimal("0.30"), 2025: Decimal("0.45"),
            2026: Decimal("0.60"), 2027: Decimal("0.75"), 2028: Decimal("0.90"),
        }
        for ano, pct in esperado.items():
            self.assertEqual(percentual_fio_b(ano), pct, msg=f"ano {ano}")

    def test_antes_de_2023_nao_havia_cobranca(self) -> None:
        self.assertEqual(percentual_fio_b(2022), Decimal("0"))

    def test_de_2029_em_diante_assume_cobranca_integral(self) -> None:
        """A ANEEL redefine a metodologia a partir de 2029 (art. 28). Até
        haver regra publicada, assumir 100% é a hipótese conservadora —
        prometer menos que isso numa proposta seria arriscado."""
        self.assertEqual(percentual_fio_b(2029), Decimal("1"))
        self.assertEqual(percentual_fio_b(2040), Decimal("1"))


class FormatarPrazoTests(TestCase):
    """Payback em decimal ("1,1 anos") não comunica nada pro cliente — ele
    pensa em meses. Pedido explícito do usuário."""

    def test_anos_e_meses(self) -> None:
        self.assertEqual(formatar_prazo(Decimal("3.5")), "3 anos e 6 meses")

    def test_singular_de_ano_e_mes(self) -> None:
        self.assertEqual(formatar_prazo(Decimal("1.0833")), "1 ano e 1 mês")

    def test_ano_exato_nao_mostra_meses(self) -> None:
        self.assertEqual(formatar_prazo(Decimal("2.0")), "2 anos")

    def test_menos_de_um_ano_mostra_so_meses(self) -> None:
        self.assertEqual(formatar_prazo(Decimal("0.5")), "6 meses")

    def test_prazo_muito_curto(self) -> None:
        self.assertEqual(formatar_prazo(Decimal("0.01")), "menos de 1 mês")

    def test_sem_payback_nao_quebra(self) -> None:
        self.assertEqual(formatar_prazo(None), "—")

    def test_nao_sobra_decimal_no_texto(self) -> None:
        """Regressão do formato antigo, que saía como "1,1 anos"."""
        self.assertNotIn(",", formatar_prazo(Decimal("1.1")))


def _municipio(nome="Gurupi", uf="TO", codigo=1709500, hsp=None):
    """Município com HSP constante em todos os meses, salvo indicação."""
    if hsp is None:
        hsp = {str(m): "5.00" for m in range(1, 13)}
    return Municipio.objects.create(
        codigo_ibge=codigo, nome=nome, uf=uf,
        latitude=Decimal("-11.65"), longitude=Decimal("-48.84"),
        hsp_mensal=hsp, hsp_anual=Decimal("5.00"),
    )


class EdicaoDePropostaNaoCorrompeItensTests(TestCase):
    """Achados da auditoria externa de 2026-08-16.

    Causa-raiz comum: `formset.save(commit=False)` devolve **apenas** as
    linhas novas ou alteradas. Quem sup&otilde;e que ali est&aacute; o formset inteiro
    calcula errado.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="vend_edicao", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)
        self.modulo = _modulo()          # 400 Wp
        self.inversor = _inversor()      # 5 kW
        self.cliente = _cliente()
        _preco(self.modulo, Decimal("800"))
        _preco(self.inversor, Decimal("4000"))

    def _proposta_com(self, quantidades):
        proposta = PropostaSolar.objects.create(
            cliente=self.cliente, consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("4.000"),
            quantidade_modulos=sum(quantidades), modulo=self.modulo,
            valor_instalacao=Decimal("0"),
        )
        itens = [
            ItemPropostaSolar.objects.create(
                proposta=proposta, modulo=self.modulo, quantidade=q,
                preco_venda_snapshot=Decimal("800"), preco_custo_snapshot=Decimal("600"),
                data_referencia_preco=date.today(),
            )
            for q in quantidades
        ]
        return proposta, itens

    def _payload(self, proposta, linhas):
        dados = {
            "cliente": self.cliente.pk, "consumo_medio_kwh": "350", "modulo": self.modulo.pk,
            "hsp": "5.5", "fator_eficiencia": "0.75", "valor_instalacao": "0",
            "tipo_ligacao": PropostaSolar.LIGACAO_MONOFASICO,
            "autoconsumo_simultaneo_pct": "25",
            "validade": (date.today() + timedelta(days=30)).isoformat(), "observacoes": "",
            "itens-TOTAL_FORMS": str(len(linhas)), "itens-INITIAL_FORMS": str(len(linhas)),
            "itens-MIN_NUM_FORMS": "1", "itens-MAX_NUM_FORMS": "1000",
        }
        for indice, linha in enumerate(linhas):
            for campo, valor in linha.items():
                dados[f"itens-{indice}-{campo}"] = valor
        return dados

    def test_editar_uma_linha_nao_perde_a_contagem_das_outras(self) -> None:
        """O caso que quebrava: duas linhas de 6, o vendedor mexe só na
        primeira, e a proposta gravava 8 módulos em vez de 14 — derrubando
        a potência de 5,6 para 3,2 kWp na ficha que vai pro cliente."""
        proposta, (i1, i2) = self._proposta_com([6, 6])

        resposta = self.client.post(
            reverse("solar:editar", args=[proposta.pk]),
            self._payload(proposta, [
                {"id": i1.pk, "proposta": proposta.pk, "modulo": self.modulo.pk, "quantidade": "8"},
                {"id": i2.pk, "proposta": proposta.pk, "modulo": self.modulo.pk, "quantidade": "6"},
            ]),
        )
        proposta.refresh_from_db()

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(proposta.quantidade_modulos, 14)
        self.assertEqual(proposta.quantidade_modulos, sum(i.quantidade for i in proposta.itens.all()))

    def test_remover_a_linha_de_modulos_zera_o_dimensionamento(self) -> None:
        """Sem módulo orçado não pode sobrar usina fantasma na proposta.

        O formset exige ao menos uma linha (`min_num=1`), então o cenário
        real não é "apagar tudo": é sobrar só o inversor na proposta."""
        proposta, (i1,) = self._proposta_com([10])
        item_inversor = ItemPropostaSolar.objects.create(
            proposta=proposta, inversor=self.inversor, quantidade=1,
            preco_venda_snapshot=Decimal("4000"), preco_custo_snapshot=Decimal("3000"),
            data_referencia_preco=date.today(),
        )

        dados = self._payload(proposta, [
            {"id": i1.pk, "proposta": proposta.pk, "modulo": self.modulo.pk, "quantidade": "10", "DELETE": "on"},
            {"id": item_inversor.pk, "proposta": proposta.pk, "inversor": self.inversor.pk, "quantidade": "1"},
        ])
        resposta = self.client.post(reverse("solar:editar", args=[proposta.pk]), dados)
        proposta.refresh_from_db()

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(proposta.quantidade_modulos, 0)
        self.assertIsNone(proposta.modulo)
        self.assertEqual(proposta.potencia_real_kwp, 0)

    def test_trocar_equipamento_da_linha_atualiza_o_snapshot(self) -> None:
        """Trocar o inversor na mesma linha cobrava o preço do antigo."""
        proposta, (i1,) = self._proposta_com([10])
        item_inversor = ItemPropostaSolar.objects.create(
            proposta=proposta, modulo=None, inversor=self.inversor, quantidade=1,
            preco_venda_snapshot=Decimal("1"), preco_custo_snapshot=Decimal("1"),
            data_referencia_preco=date.today(),
        )
        outro = Inversor.objects.create(
            fabricante="TestFab", modelo="INV10K", potencia_kw=10, tipo=Inversor.TIPO_STRING,
            fase=Inversor.FASE_MONO, tensao_max_entrada=600, quantidade_mppt=2, garantia=5,
        )
        _preco(outro, Decimal("9999"))

        self.client.post(
            reverse("solar:editar", args=[proposta.pk]),
            self._payload(proposta, [
                {"id": i1.pk, "proposta": proposta.pk, "modulo": self.modulo.pk, "quantidade": "10"},
                {"id": item_inversor.pk, "proposta": proposta.pk, "inversor": outro.pk, "quantidade": "1"},
            ]),
        )
        item_inversor.refresh_from_db()

        self.assertEqual(item_inversor.inversor, outro)
        self.assertEqual(item_inversor.preco_venda_snapshot, Decimal("9999.00"))

    def test_editar_sem_mexer_nos_itens_preserva_a_contagem(self) -> None:
        """Mudar só um campo da proposta não pode zerar o dimensionamento."""
        proposta, (i1,) = self._proposta_com([12])

        dados = self._payload(proposta, [
            {"id": i1.pk, "proposta": proposta.pk, "modulo": self.modulo.pk, "quantidade": "12"},
        ])
        dados["observacoes"] = "só mudei isto"
        self.client.post(reverse("solar:editar", args=[proposta.pk]), dados)
        proposta.refresh_from_db()

        self.assertEqual(proposta.quantidade_modulos, 12)


class TravaDeEdicaoPorStatusTests(TestCase):
    """Proposta fechada não pode ser editada nem excluída: o lançamento
    financeiro e a OS já partiram dela."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="vend_trava", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)
        self.modulo = _modulo()

    def _proposta(self, status):
        proposta = _proposta(self.modulo)
        proposta.status = status
        proposta.save()
        return proposta

    def test_rascunho_continua_editavel(self) -> None:
        proposta = self._proposta(PropostaSolar.STATUS_RASCUNHO)

        resposta = self.client.get(reverse("solar:editar", args=[proposta.pk]))

        self.assertEqual(resposta.status_code, 200)

    def test_aprovada_nao_abre_o_formulario_de_edicao(self) -> None:
        proposta = self._proposta(PropostaSolar.STATUS_APROVADA)

        resposta = self.client.get(reverse("solar:editar", args=[proposta.pk]))

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(str(proposta.pk), resposta.url)

    def test_aprovada_tambem_rejeita_post_direto(self) -> None:
        """Bloquear só o GET deixaria a porta aberta pra POST na mão."""
        proposta = self._proposta(PropostaSolar.STATUS_APROVADA)
        consumo_antes = proposta.consumo_medio_kwh

        self.client.post(reverse("solar:editar", args=[proposta.pk]), {"consumo_medio_kwh": "9999"})
        proposta.refresh_from_db()

        self.assertEqual(proposta.consumo_medio_kwh, consumo_antes)

    def test_concluida_nao_pode_ser_excluida(self) -> None:
        proposta = self._proposta(PropostaSolar.STATUS_CONCLUIDA)

        resposta = self.client.post(reverse("solar:excluir", args=[proposta.pk]))

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(PropostaSolar.objects.filter(pk=proposta.pk).exists())

    def test_rascunho_continua_excluivel(self) -> None:
        proposta = self._proposta(PropostaSolar.STATUS_RASCUNHO)

        self.client.post(reverse("solar:excluir", args=[proposta.pk]))

        self.assertFalse(PropostaSolar.objects.filter(pk=proposta.pk).exists())


class MunicipioTests(TestCase):
    def test_hsp_do_mes_le_chave_string_do_json(self) -> None:
        """O JSONField volta do banco com as chaves em string."""
        municipio = _municipio(hsp={str(m): f"{m}.00" for m in range(1, 13)})

        self.assertEqual(municipio.hsp_do_mes(1), Decimal("1.00"))
        self.assertEqual(municipio.hsp_do_mes(12), Decimal("12.00"))

    def test_sem_hsp_sincronizado(self) -> None:
        municipio = Municipio.objects.create(codigo_ibge=1, nome="Sem Dados", uf="TO")

        self.assertFalse(municipio.tem_hsp)
        self.assertIsNone(municipio.hsp_do_mes(1))


class GeracaoMensalSerieTests(TestCase):
    """Curva de geração mês a mês a partir do HSP do local."""

    def setUp(self) -> None:
        self.modulo = _modulo()  # 400 Wp

    def _proposta_com_municipio(self, hsp=None):
        proposta = _proposta(self.modulo)  # 10 módulos -> 4,0 kWp, fator 0,75
        proposta.municipio = _municipio(hsp=hsp)
        proposta.save()
        return proposta

    def test_sem_municipio_nao_ha_serie(self) -> None:
        self.assertIsNone(_proposta(self.modulo).geracao_mensal_serie)

    def test_usa_hsp_do_mes_e_dias_reais(self) -> None:
        """Janeiro tem 31 dias e fevereiro 28 — com o mesmo HSP, fevereiro
        gera menos. A conta antiga usava 30 fixo para todo mês."""
        serie = self._proposta_com_municipio().geracao_mensal_serie

        self.assertEqual(len(serie), 12)
        # 4,0 kWp × 5,00 HSP × 31 dias × 0,75 = 465
        self.assertEqual(serie[0]["kwh"], Decimal("465"))
        # fevereiro: × 28 dias = 420
        self.assertEqual(serie[1]["kwh"], Decimal("420"))
        self.assertEqual(serie[0]["nome"], "Jan")

    def test_serie_acompanha_a_sazonalidade_do_hsp(self) -> None:
        hsp = {str(m): "4.00" for m in range(1, 13)}
        hsp["9"] = "6.00"  # setembro é o pico no Tocantins
        serie = self._proposta_com_municipio(hsp=hsp).geracao_mensal_serie

        setembro = next(i for i in serie if i["mes"] == 9)
        self.assertEqual(max(serie, key=lambda i: i["kwh"]), setembro)

    def test_geracao_mensal_media_vem_da_serie(self) -> None:
        proposta = self._proposta_com_municipio()
        serie = proposta.geracao_mensal_serie

        esperado = int(sum(i["kwh"] for i in serie) / 12)
        self.assertEqual(proposta.geracao_mensal_kwh, esperado)

    def test_media_da_serie_supera_a_conta_antiga_de_30_dias(self) -> None:
        """Regressão: 30 dias fixos subestimam o ano (365/12 = 30,4)."""
        proposta = self._proposta_com_municipio()
        antiga = round(float(proposta.potencia_real_kwp) * 5.00 * 30 * 0.75)

        self.assertGreater(proposta.geracao_mensal_kwh, antiga)

    def test_geracao_anual_soma_os_doze_meses(self) -> None:
        proposta = self._proposta_com_municipio()

        self.assertEqual(
            proposta.geracao_anual_kwh,
            sum(i["kwh"] for i in proposta.geracao_mensal_serie),
        )

    def test_municipio_sem_hsp_cai_na_conta_antiga(self) -> None:
        proposta = _proposta(self.modulo)
        proposta.municipio = Municipio.objects.create(codigo_ibge=2, nome="Sem HSP", uf="TO")
        proposta.save()

        self.assertIsNone(proposta.geracao_mensal_serie)
        self.assertEqual(proposta.geracao_mensal_kwh, 495)  # 4,0 × 5,5 × 30 × 0,75


class GraficoGeracaoMensalTests(TestCase):
    def setUp(self) -> None:
        self.modulo = _modulo()
        self.proposta = _proposta(self.modulo)
        self.proposta.municipio = _municipio()
        self.proposta.save()

    def test_gera_doze_barras_com_rotulo_em_todas(self) -> None:
        """Só 12 barras: dá pra rotular todas sem virar ruído, e o valor de
        cada mês é justamente o que interessa."""
        grafico = grafico_geracao_mensal(self.proposta.geracao_mensal_serie)

        self.assertEqual(len(grafico["barras"]), 12)
        self.assertEqual(grafico["barras"][0]["mes"], "Jan")
        self.assertEqual(grafico["barras"][-1]["mes"], "Dez")

    def test_coordenadas_saem_como_string_com_ponto(self) -> None:
        """Mesma armadilha do outro gráfico: USE_THOUSAND_SEPARATOR
        localizaria os números e quebraria o SVG."""
        import re

        grafico = grafico_geracao_mensal(self.proposta.geracao_mensal_serie)

        for chave in ("view_box", "largura", "base_y", "mes_y", "media_y"):
            self.assertNotIn(",", str(grafico[chave]), msg=chave)
        for barra in grafico["barras"]:
            for token in re.findall(r"-?\d[\d.]*", barra["path"]):
                self.assertIn(".", token)

    def test_media_fica_entre_o_menor_e_o_maior_mes(self) -> None:
        grafico = grafico_geracao_mensal(self.proposta.geracao_mensal_serie)
        valores = [b["kwh"] for b in grafico["barras"]]

        self.assertGreaterEqual(grafico["media_kwh"], int(min(valores)))
        self.assertLessEqual(grafico["media_kwh"], int(max(valores)))

    def test_sem_serie_retorna_none(self) -> None:
        self.assertIsNone(grafico_geracao_mensal(None))
        self.assertIsNone(grafico_geracao_mensal([]))


class MunicipioHerdadoDoClienteTests(TestCase):
    """A proposta nova já vem com o município do cliente, mas o vendedor
    pode trocar — o gerador pode ser para outro endereço."""

    def setUp(self) -> None:
        self.gurupi = _municipio()
        self.modulo = _modulo()

    def _cliente_em(self, cidade, estado="TO"):
        return Cliente.objects.create(
            tipo="PF", cpf_cnpj="222.222.222-22", nome="Fulano",
            cidade=cidade, estado=estado,
        )

    def test_sugere_municipio_a_partir_da_cidade_do_cliente(self) -> None:
        form = PropostaSolarForm(initial={"cliente": self._cliente_em("Gurupi").pk})

        self.assertEqual(form.initial["municipio"], self.gurupi.pk)

    def test_casamento_ignora_acento_e_caixa(self) -> None:
        palmas = _municipio(nome="Palmas", codigo=1721000)
        form = PropostaSolarForm(initial={"cliente": self._cliente_em("PALMAS").pk})

        self.assertEqual(form.initial["municipio"], palmas.pk)

    def test_cidade_desconhecida_nao_chuta_municipio(self) -> None:
        """Melhor deixar em branco que arriscar o município errado — ele
        define o HSP e, por consequência, a geração prometida."""
        form = PropostaSolarForm(initial={"cliente": self._cliente_em("Cidade Inexistente").pk})

        self.assertIsNone(form.initial.get("municipio"))

    def test_nao_confunde_cidades_homonimas_de_outra_uf(self) -> None:
        form = PropostaSolarForm(initial={"cliente": self._cliente_em("Gurupi", estado="GO").pk})

        self.assertIsNone(form.initial.get("municipio"))

    def test_cliente_sem_cidade_nao_quebra(self) -> None:
        form = PropostaSolarForm(initial={"cliente": self._cliente_em("").pk})

        self.assertIsNone(form.initial.get("municipio"))

    def test_proposta_existente_nao_tem_o_municipio_sobrescrito(self) -> None:
        """Editar uma proposta salva não pode puxar o município do cliente
        por cima da escolha que o vendedor já fez."""
        outro = _municipio(nome="Porto Nacional", codigo=1718204)
        proposta = _proposta(self.modulo, cliente=self._cliente_em("Gurupi"))
        proposta.municipio = outro
        proposta.save()

        form = PropostaSolarForm(instance=proposta)

        self.assertNotEqual(form.initial.get("municipio"), self.gurupi.pk)


class ConsolidarTarifasANEELTests(TestCase):
    """Transformação dos componentes soltos da ANEEL numa tarifa utilizável.

    Sem rede: exercita só a função pura sobre um payload no formato real
    devolvido pelo `datastore_search`."""

    def _registro(self, componente, valor, **extra):
        base = {
            "DscBaseTarifaria": "Tarifa de Aplicação",
            "DscComponenteTarifario": componente,
            "VlrComponenteTarifario": valor,
            "DatInicioVigencia": "2026-07-04",
            "DatFimVigencia": "2027-07-03",
            "DscSubClasseConsumidor": "Residencial",
            "DscSubGrupoTarifario": "B1",
            "DscModalidadeTarifaria": "Convencional",
        }
        base.update(extra)
        return base

    def test_agrupa_componentes_numa_linha_por_vigencia(self) -> None:
        registros = [
            self._registro("TUSD", "683,43"),
            self._registro("TE", "322,63"),
            self._registro("TUSD_FioB", "441,478264"),
        ]

        tarifas = consolidar_tarifas(registros)

        self.assertEqual(len(tarifas), 1)
        linha = tarifas[("2026-07-04", "Residencial")]
        self.assertEqual(linha["vlr_tusd"], Decimal("683.43"))
        self.assertEqual(linha["vlr_te"], Decimal("322.63"))
        self.assertEqual(linha["vlr_tusd_fio_b"], Decimal("441.478264"))

    def test_converte_virgula_decimal_da_aneel(self) -> None:
        """A ANEEL devolve "683,43", não "683.43"."""
        tarifas = consolidar_tarifas([self._registro("TUSD", "1.006,06"), self._registro("TE", "0,00")])

        self.assertEqual(tarifas[("2026-07-04", "Residencial")]["vlr_tusd"], Decimal("1006.06"))

    def test_ignora_base_economica_e_cva(self) -> None:
        """Só "Tarifa de Aplicação" é o que o cliente realmente paga."""
        registros = [
            self._registro("TUSD", "683,43", DscBaseTarifaria="Base Econômica"),
            self._registro("TE", "322,63", DscBaseTarifaria="Base Econômica"),
            self._registro("TUSD", "1,00", DscBaseTarifaria="CVA"),
        ]

        self.assertEqual(consolidar_tarifas(registros), {})

    def test_descarta_linha_sem_tusd_ou_te(self) -> None:
        """Só Fio B não dá pra montar tarifa nenhuma."""
        self.assertEqual(consolidar_tarifas([self._registro("TUSD_FioB", "441,47")]), {})

    def test_separa_subclasses_diferentes(self) -> None:
        registros = [
            self._registro("TUSD", "683,43"),
            self._registro("TE", "322,63"),
            self._registro("TUSD", "600,00", DscSubClasseConsumidor="Baixa Renda"),
            self._registro("TE", "300,00", DscSubClasseConsumidor="Baixa Renda"),
        ]

        self.assertEqual(len(consolidar_tarifas(registros)), 2)


class TarifaDistribuidoraTests(TestCase):
    def setUp(self) -> None:
        self.eto = Distribuidora.objects.create(
            nome="Energisa Tocantins", sigla="ETO", cnpj="25086034000171", uf="TO"
        )

    def _tarifa(self, inicio, fim=None, tusd="683.43", te="322.63", fio_b="441.478264"):
        return TarifaDistribuidora.objects.create(
            distribuidora=self.eto, vigencia_inicio=inicio, vigencia_fim=fim,
            vlr_tusd=Decimal(tusd), vlr_te=Decimal(te), vlr_tusd_fio_b=Decimal(fio_b),
        )

    def test_tarifa_base_bate_com_a_coluna_tarifa_unit_da_fatura(self) -> None:
        """TUSD 683,43 + TE 322,63 = 1006,06 R$/MWh = 1,006060 R$/kWh —
        exatamente a coluna "Tarifa Unit" da fatura de agosto/2026."""
        tarifa = self._tarifa(date(2026, 7, 4), date(2027, 7, 3))

        self.assertEqual(tarifa.tarifa_base_kwh, Decimal("1.006060"))
        self.assertEqual(tarifa.fio_b_kwh, Decimal("0.441478264"))

    def test_vigente_escolhe_a_do_periodo(self) -> None:
        antiga = self._tarifa(date(2025, 7, 4), date(2026, 7, 3), tusd="600")
        nova = self._tarifa(date(2026, 7, 4), date(2027, 7, 3))

        self.assertEqual(TarifaDistribuidora.vigente(self.eto, date(2026, 1, 10)), antiga)
        self.assertEqual(TarifaDistribuidora.vigente(self.eto, date(2026, 8, 16)), nova)

    def test_vigencia_aberta_continua_valendo(self) -> None:
        aberta = self._tarifa(date(2026, 7, 4), None)

        self.assertEqual(TarifaDistribuidora.vigente(self.eto, date(2030, 1, 1)), aberta)

    def test_sem_tarifa_na_data_retorna_none(self) -> None:
        self._tarifa(date(2026, 7, 4), date(2027, 7, 3))

        self.assertIsNone(TarifaDistribuidora.vigente(self.eto, date(2020, 1, 1)))


class AplicarTributosTests(TestCase):
    """Gross-up da tarifa da ANEEL (sem tributos) para a tarifa da fatura.

    ICMS e PIS/COFINS incidem "por dentro", em cascata. Duas faturas reais
    da Energisa TO confirmam a fórmula com erro abaixo de 0,001%."""

    ICMS = Decimal("20.00")
    PIS_COFINS = Decimal("9.25")

    def test_bate_com_a_fatura_do_ciclo_2025(self) -> None:
        # Fatura de julho/2026: Tarifa Unit 0,930220 -> "com tributos" 1,281290
        calculado = aplicar_tributos(Decimal("0.930220"), self.ICMS, self.PIS_COFINS)

        self.assertAlmostEqual(calculado, Decimal("1.281290"), delta=Decimal("0.00001"))

    def test_bate_com_a_fatura_do_ciclo_2026(self) -> None:
        # Fatura de agosto/2026: Tarifa Unit 1,006060 -> "com tributos" 1,385750
        calculado = aplicar_tributos(Decimal("1.006060"), self.ICMS, self.PIS_COFINS)

        self.assertAlmostEqual(calculado, Decimal("1.385750"), delta=Decimal("0.00001"))

    def test_icms_reduzido_reproduz_a_tarifa_de_injecao(self) -> None:
        """O crédito da energia injetada leva ICMS efetivo bem menor (~7,3%)
        que o consumo — é isso, e não o Fio B, que explica a tarifa de
        injeção ser menor na fatura."""
        calculado = aplicar_tributos(Decimal("1.006060"), Decimal("7.30"), self.PIS_COFINS)

        self.assertAlmostEqual(calculado, Decimal("1.197480"), delta=Decimal("0.002"))

    def test_sem_tributo_devolve_a_propria_base(self) -> None:
        self.assertEqual(aplicar_tributos(Decimal("1.00"), Decimal("0"), Decimal("0")), Decimal("1.00"))


class RetornoGDContraFaturaRealTests(TestCase):
    """Âncoras de verificação do motor de cálculo, contra **duas** faturas
    reais da Energisa Tocantins (B1 residencial monofásico).

    As duas juntas são o que separa tributo de Fio B — a primeira versão
    desta feature confundiu os dois e superestimou a economia em 29%,
    justamente porque só tinha a fatura GD1 como referência.
    """

    COSIP_AGO = Decimal("42.14")
    COSIP_JUL = Decimal("29.50")

    # --- Fatura agosto/2026 — consumidor GD1 (direito adquirido, SEM Fio B)
    GD1_CONSUMO_CT = Decimal("1.385750")
    GD1_INJECAO_CT = Decimal("1.197480")
    GD1_CONSUMO_KWH = Decimal("547")
    GD1_INJETADA_KWH = Decimal("499")

    # --- Fatura julho/2026 — consumidor GDII (regra nova, COM Fio B)
    GDII_CONSUMO_CT = Decimal("1.281290")
    GDII_INJECAO_CT = Decimal("1.104860")
    GDII_AJUSTE_FIO_B = Decimal("0.256552")  # linha "Ajuste GDII - TRF Reduzida"
    GDII_FIO_B_100 = GDII_AJUSTE_FIO_B / Decimal("0.60")  # o ajuste já vem a 60%
    GDII_KWH = Decimal("380")

    def test_gd1_sem_fio_b_reproduz_a_fatura(self) -> None:
        """Fatura: 758,00 − 597,54 + 42,14 (+1,25 bandeira −4,46 bônus) = 199,39.

        Bandeira e bônus são itens transitórios que o motor não modela, então
        somamos os dois à parte. Tolerância de 2 centavos porque a
        distribuidora arredonda linha a linha."""
        retorno = projetar_retorno(
            valor_investimento=Decimal("20000"),
            geracao_mensal_kwh=self.GD1_INJETADA_KWH,
            consumo_mensal_kwh=self.GD1_CONSUMO_KWH,
            tarifa_consumo_kwh=self.GD1_CONSUMO_CT,
            tarifa_injecao_kwh=self.GD1_INJECAO_CT,
            fio_b_kwh=Decimal("0"),  # GD1 não paga Fio B
            tipo_ligacao="monofasico",
            cosip_mensal=self.COSIP_AGO,
            ano_base=2026,
            autoconsumo_simultaneo_pct=Decimal("0"),
        )

        self.assertEqual(retorno["economia_mensal"], Decimal("597.54"))
        total = retorno["conta_estimada"] + Decimal("1.25") - Decimal("4.46")
        self.assertAlmostEqual(total, Decimal("199.39"), delta=Decimal("0.02"))

    def test_gdii_com_fio_b_reproduz_a_fatura(self) -> None:
        """Fatura: 486,89 − 419,85 + 97,48 (Ajuste Fio B) + 29,50 = 194,02.

        Aqui o Fio B aparece como linha própria e isenta de tributo — é o
        caso que a fatura GD1 não tinha e que fez a versão anterior errar."""
        retorno = projetar_retorno(
            valor_investimento=Decimal("20000"),
            geracao_mensal_kwh=self.GDII_KWH,
            consumo_mensal_kwh=self.GDII_KWH,
            tarifa_consumo_kwh=self.GDII_CONSUMO_CT,
            tarifa_injecao_kwh=self.GDII_INJECAO_CT,
            fio_b_kwh=self.GDII_FIO_B_100,
            tipo_ligacao="monofasico",
            cosip_mensal=self.COSIP_JUL,
            ano_base=2026,
            autoconsumo_simultaneo_pct=Decimal("0"),
        )

        # A fatura compensou os 380 kWh cheios; o mínimo de 30 kWh não pegou
        # porque o Ajuste do Fio B já deixa a conta acima dele.
        self.assertAlmostEqual(
            retorno["conta_estimada"], Decimal("194.02"), delta=Decimal("0.05"),
            msg="deveria fechar com o total real da fatura (R$ 194,02)",
        )

    def test_fio_b_reduz_a_economia_frente_ao_gd1(self) -> None:
        """Mesmo sistema, mesma tarifa: quem entrou na regra nova economiza
        menos. Se este teste inverter, o Fio B parou de ser aplicado."""
        comum = dict(
            valor_investimento=Decimal("20000"),
            geracao_mensal_kwh=self.GDII_KWH,
            consumo_mensal_kwh=self.GDII_KWH,
            tarifa_consumo_kwh=self.GDII_CONSUMO_CT,
            tarifa_injecao_kwh=self.GDII_INJECAO_CT,
            tipo_ligacao="monofasico",
            cosip_mensal=self.COSIP_JUL,
            ano_base=2026,
            autoconsumo_simultaneo_pct=Decimal("0"),
        )
        gd1 = projetar_retorno(**comum, fio_b_kwh=Decimal("0"))
        gdii = projetar_retorno(**comum, fio_b_kwh=self.GDII_FIO_B_100)

        self.assertLess(gdii["economia_mensal"], gd1["economia_mensal"])

    def test_regressao_nao_volta_a_confundir_tributo_com_fio_b(self) -> None:
        """O bug original tratava a diferença entre as tarifas de consumo e
        injeção como se fosse Fio B, e ainda descontava o Fio B por cima —
        chegando a ~1,0930/kWh contra os 0,8483 reais (+29%)."""
        retorno = projetar_retorno(
            valor_investimento=Decimal("20000"),
            geracao_mensal_kwh=self.GDII_KWH,
            consumo_mensal_kwh=self.GDII_KWH,
            tarifa_consumo_kwh=self.GDII_CONSUMO_CT,
            tarifa_injecao_kwh=self.GDII_INJECAO_CT,
            fio_b_kwh=self.GDII_FIO_B_100,
            tipo_ligacao="monofasico",
            cosip_mensal=self.COSIP_JUL,
            ano_base=2026,
            autoconsumo_simultaneo_pct=Decimal("0"),
        )
        por_kwh = retorno["fluxo_anual"][0]["tarifa_compensacao"]

        self.assertAlmostEqual(por_kwh, Decimal("0.848308"), delta=Decimal("0.0001"))
        self.assertLess(por_kwh, Decimal("1.09"), msg="voltou a superestimar como no bug original")


class ProjetarRetornoTests(TestCase):
    """Regras de GD que o cálculo ingênuo (geração × tarifa) ignorava."""

    BASE = dict(
        valor_investimento=Decimal("20000"),
        geracao_mensal_kwh=Decimal("500"),
        consumo_mensal_kwh=Decimal("500"),
        tarifa_consumo_kwh=Decimal("1.385750"),
        tarifa_injecao_kwh=Decimal("1.197480"),
        fio_b_kwh=Decimal("0.441478"),
        tipo_ligacao="monofasico",
        cosip_mensal=Decimal("42.14"),
        ano_base=2026,
    )

    def test_economia_e_menor_que_geracao_vezes_tarifa(self) -> None:
        """Regressão do bug original: o cálculo antigo era geração × tarifa
        cheia, que superestima porque ignora tributo sobre a injeção, Fio B
        e custo de disponibilidade."""
        retorno = projetar_retorno(**self.BASE)
        ingenuo = Decimal("500") * Decimal("1.385750")

        self.assertLess(retorno["economia_mensal"], ingenuo)

    def test_custo_de_disponibilidade_e_piso_da_conta(self) -> None:
        """Mesmo gerando muito mais que consome, o cliente monofásico segue
        pagando pelo menos 30 kWh. O mínimo é piso da conta — a compensação
        em si cobre o consumo inteiro, como na fatura real."""
        retorno = projetar_retorno(**{**self.BASE, "geracao_mensal_kwh": Decimal("5000")})

        self.assertEqual(retorno["custo_disponibilidade_kwh"], 30)
        self.assertEqual(retorno["compensada_mensal_kwh"], Decimal("500.00"))
        # conta nunca zera: sobra o mínimo faturado + COSIP
        self.assertGreaterEqual(
            retorno["conta_estimada"],
            Decimal("30") * Decimal("1.385750") + Decimal("42.14") - Decimal("0.01"),
        )

    def test_trifasico_paga_minimo_maior(self) -> None:
        """Sem Fio B (consumidor GD1) a conta cairia bem baixo, e aí o piso
        de 100 kWh do trifásico passa a valer — com Fio B o ajuste já mantém
        a conta acima de qualquer um dos pisos."""
        gd1 = {**self.BASE, "geracao_mensal_kwh": Decimal("5000"), "fio_b_kwh": Decimal("0")}
        mono = projetar_retorno(**gd1)
        tri = projetar_retorno(**{**gd1, "tipo_ligacao": "trifasico"})

        self.assertEqual(tri["custo_disponibilidade_kwh"], 100)
        self.assertGreater(tri["conta_estimada"], mono["conta_estimada"])

    def test_autoconsumo_simultaneo_economiza_mais_que_injetar(self) -> None:
        """O kWh consumido na hora não passa pela rede, logo não sofre Fio B
        — vale a tarifa cheia, mais que o kWh injetado."""
        sem = projetar_retorno(**{**self.BASE, "autoconsumo_simultaneo_pct": Decimal("0")})
        com = projetar_retorno(**{**self.BASE, "autoconsumo_simultaneo_pct": Decimal("50")})

        self.assertGreater(com["economia_mensal"], sem["economia_mensal"])

    def test_autoconsumo_total_economiza_quase_a_tarifa_cheia(self) -> None:
        """Consumindo tudo na hora, nada passa pela rede — mas o mínimo
        faturado (30 kWh) continua na conta, então a economia é a tarifa
        cheia menos esse piso."""
        retorno = projetar_retorno(
            **{**self.BASE, "autoconsumo_simultaneo_pct": Decimal("100")}
        )
        cheia = Decimal("500") * Decimal("1.385750")
        piso = Decimal("30") * Decimal("1.385750")

        self.assertEqual(retorno["autoconsumo_mensal_kwh"], Decimal("500.00"))
        self.assertEqual(retorno["economia_mensal"], (cheia - piso).quantize(Decimal("0.01")))

    def test_economia_cai_quando_o_fio_b_sobe(self) -> None:
        """Entre 2026 (60%) e 2028 (90%) a mesma usina economiza menos."""
        em_2026 = projetar_retorno(**{**self.BASE, "ano_base": 2026})
        em_2028 = projetar_retorno(**{**self.BASE, "ano_base": 2028})

        self.assertLess(em_2028["economia_mensal"], em_2026["economia_mensal"])

    def test_conta_estimada_e_conta_atual_menos_economia(self) -> None:
        retorno = projetar_retorno(**self.BASE)

        self.assertEqual(
            retorno["conta_estimada"],
            retorno["conta_atual"] - retorno["economia_mensal"],
        )

    def test_cosip_nunca_e_compensada(self) -> None:
        """A iluminação pública continua na conta mesmo com a usina."""
        retorno = projetar_retorno(**{**self.BASE, "geracao_mensal_kwh": Decimal("10000")})

        self.assertGreaterEqual(retorno["conta_estimada"], Decimal("42.14"))

    def test_fluxo_anual_tem_25_anos_e_acumula(self) -> None:
        retorno = projetar_retorno(**self.BASE)
        fluxo = retorno["fluxo_anual"]

        self.assertEqual(len(fluxo), 25)
        self.assertEqual(fluxo[0]["ano"], 2026)
        self.assertEqual(fluxo[-1]["ano"], 2050)
        self.assertEqual(fluxo[-1]["acumulado"], retorno["economia_total"])
        for anterior, seguinte in zip(fluxo, fluxo[1:]):
            self.assertGreater(seguinte["acumulado"], anterior["acumulado"])

    def test_geracao_degrada_ao_longo_dos_anos(self) -> None:
        fluxo = projetar_retorno(**self.BASE)["fluxo_anual"]

        self.assertLess(
            fluxo[-1]["geracao_mensal_kwh"], fluxo[0]["geracao_mensal_kwh"]
        )

    def test_sem_tarifa_retorna_none(self) -> None:
        self.assertIsNone(projetar_retorno(**{**self.BASE, "tarifa_consumo_kwh": None}))

    def test_sem_geracao_retorna_none(self) -> None:
        self.assertIsNone(
            projetar_retorno(**{**self.BASE, "geracao_mensal_kwh": Decimal("0")})
        )

    def test_sem_consumo_retorna_none(self) -> None:
        self.assertIsNone(
            projetar_retorno(**{**self.BASE, "consumo_mensal_kwh": Decimal("0")})
        )


class GraficoEconomiaAnualTests(TestCase):
    """Geometria do gráfico do PDF. Ver solar/services.py."""

    def _grafico(self, **extra):
        extra.setdefault("valor_investimento", Decimal("20000"))
        retorno = projetar_retorno(
            geracao_mensal_kwh=Decimal("500"),
            consumo_mensal_kwh=Decimal("500"),
            tarifa_consumo_kwh=Decimal("1.385750"),
            tarifa_injecao_kwh=Decimal("1.197480"),
            fio_b_kwh=Decimal("0.441478"),
            tipo_ligacao="monofasico",
            cosip_mensal=Decimal("42.14"),
            ano_base=2026,
            **extra,
        )
        return grafico_economia_anual(retorno)

    def test_rotulos_das_pontas_ancoram_na_borda(self) -> None:
        """Regressão: com text-anchor=middle os rótulos da primeira e da
        última barra saíam cortados nas bordas do viewBox."""
        grafico = self._grafico()

        primeira, ultima = grafico["barras"][0], grafico["barras"][-1]
        self.assertEqual(primeira["ancora"], "start")
        self.assertEqual(primeira["rotulo_x"], "0.00")
        self.assertEqual(ultima["ancora"], "end")
        self.assertEqual(ultima["rotulo_x"], grafico["largura"] + ".00")

    def test_barras_do_meio_ficam_centralizadas(self) -> None:
        grafico = self._grafico()

        self.assertEqual(grafico["barras"][10]["ancora"], "middle")

    def test_todas_as_coordenadas_usam_ponto_decimal(self) -> None:
        """Nenhum número pode sair com vírgula decimal — o SVG não leria.

        Atenção: vírgula *é* separador legítimo de par de coordenadas num
        path ("M0.00,170.00"), então o teste olha token a token em vez de
        procurar vírgula na string inteira."""
        import re

        grafico = self._grafico()

        for chave in ("view_box", "largura", "base_y", "ano_y", "payback_x"):
            self.assertNotIn(",", str(grafico[chave]), msg=chave)

        for barra in grafico["barras"]:
            self.assertNotIn(",", barra["ano"])
            self.assertNotIn(",", barra["rotulo_x"])
            for token in re.findall(r"-?\d[\d.]*", barra["path"]):
                self.assertIn(".", token, msg=f"{token} em {barra['path']}")

    def test_marcador_de_payback_vira_para_dentro_perto_da_borda(self) -> None:
        """Payback tardio jogaria o texto pra fora do gráfico."""
        # R$ 246.787,75 é o acumulado no ano 20 de 25 — bem além dos 75% da
        # largura em que o rótulo passa a ancorar à esquerda da linha.
        tardio = self._grafico(valor_investimento=Decimal("246000"))

        self.assertIsNotNone(tardio["payback_anos"])
        self.assertEqual(tardio["payback_ancora"], "end")

    def test_sem_payback_nao_desenha_marcador(self) -> None:
        """Investimento que não se paga em 25 anos não ganha linha
        tracejada — o template pula o bloco quando payback_x é None."""
        caro = self._grafico(valor_investimento=Decimal("900000"))

        self.assertIsNone(caro["payback_anos"])
        self.assertIsNone(caro["payback_x"])

    def test_sem_fluxo_retorna_none(self) -> None:
        self.assertIsNone(grafico_economia_anual({"fluxo_anual": []}))
        self.assertIsNone(grafico_economia_anual(None))


class RetornoFinanceiroDaPropostaTests(TestCase):
    """PropostaSolar.retorno_financeiro — integração do model com o motor."""

    def setUp(self) -> None:
        self.modulo = _modulo()  # 400 Wp
        self.inversor = _inversor()  # 5 kW

    def test_sem_tarifa_retorna_none(self) -> None:
        proposta = _proposta(self.modulo)
        self.assertIsNone(proposta.retorno_financeiro)

    def test_tarifa_zero_retorna_none(self) -> None:
        """Não inventa número: tarifa 0 é tratada como "não informada"."""
        proposta = _proposta(self.modulo)
        proposta.tarifa_kwh = Decimal("0")
        proposta.save()
        self.assertIsNone(proposta.retorno_financeiro)

    def test_sem_geracao_retorna_none(self) -> None:
        """Proposta sem módulo de referência não tem geração projetada —
        mesmo com tarifa informada, não há economia pra calcular."""
        proposta = PropostaSolar.objects.create(
            cliente=_cliente(), consumo_medio_kwh=350, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("0"),
            quantidade_modulos=0, valor_instalacao=Decimal("0"),
            tarifa_kwh=Decimal("0.95"),
        )
        self.assertIsNone(proposta.retorno_financeiro)

    def test_tarifa_digitada_e_marcada_como_manual(self) -> None:
        """Sem distribuidora, cai na tarifa digitada da fatura — e o Fio B
        fica zerado, porque não dá pra separar essa parcela sem a
        decomposição da ANEEL."""
        proposta = _proposta(self.modulo)
        proposta.tarifa_kwh = Decimal("1.385750")
        proposta.save()

        retorno = proposta.retorno_financeiro
        self.assertEqual(retorno["origem_tarifa"], "manual")
        self.assertIsNone(retorno["vigencia_tarifa"])

    def test_tarifa_da_aneel_tem_prioridade_sobre_a_digitada(self) -> None:
        distribuidora = Distribuidora.objects.create(
            nome="Energisa Tocantins", sigla="ETO", cnpj="25086034000171", uf="TO"
        )
        TarifaDistribuidora.objects.create(
            distribuidora=distribuidora,
            vigencia_inicio=date(2020, 1, 1),
            vlr_tusd=Decimal("683.43"),
            vlr_te=Decimal("322.63"),
            vlr_tusd_fio_b=Decimal("441.478264"),
        )
        proposta = _proposta(self.modulo)
        proposta.distribuidora = distribuidora
        proposta.tarifa_kwh = Decimal("99.00")  # valor absurdo, deve ser ignorado
        proposta.save()

        retorno = proposta.retorno_financeiro
        self.assertEqual(retorno["origem_tarifa"], "aneel")
        self.assertAlmostEqual(
            retorno["tarifa_consumo_kwh"], Decimal("1.385750"), delta=Decimal("0.0001")
        )

    def test_payback_e_calculado_sobre_o_valor_total(self) -> None:
        proposta = _proposta(self.modulo)
        ItemPropostaSolar.objects.create(
            proposta=proposta, modulo=self.modulo, quantidade=10,
            preco_venda_snapshot=Decimal("600"), preco_custo_snapshot=Decimal("500"),
            data_referencia_preco=date.today(),
        )
        proposta.tarifa_kwh = Decimal("1.385750")
        proposta.save()

        # valor_total = 10*600 + 2000 (instalação) = 8000
        retorno = proposta.retorno_financeiro
        self.assertIsNotNone(retorno["payback_anos"])
        self.assertGreater(retorno["payback_anos"], Decimal("0"))
        self.assertLess(retorno["payback_anos"], Decimal("25"))


class ResumoDeFechamentoNaTelaTests(TestCase):
    """Card "Resumo para fechamento" em proposta_detail.html — o texto que o
    usuário hoje monta manualmente pra mandar no WhatsApp."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.modulo = _modulo()
        cls.inversor = _inversor()
        cls.proposta = _proposta(cls.modulo)
        ItemPropostaSolar.objects.create(
            proposta=cls.proposta, inversor=cls.inversor, quantidade=1,
            preco_venda_snapshot=Decimal("4000"), preco_custo_snapshot=Decimal("3000"),
            data_referencia_preco=date.today(),
        )
        cls.user = User.objects.create_user(username="vend_resumo", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_textarea_de_resumo_aparece_com_dados_da_proposta(self) -> None:
        resposta = self.client.get(reverse("solar:detalhe", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn('id="resumo-proposta"', corpo)
        self.assertIn(self.proposta.cliente.nome, corpo)
        self.assertIn(f"{self.proposta.geracao_mensal_kwh} kWh/mês", corpo)
        self.assertIn(self.modulo.fabricante, corpo)
        self.assertIn(self.inversor.fabricante, corpo)

    def test_resumo_nao_tem_espaco_sobrando_no_inicio_das_linhas(self) -> None:
        """Se a indentação do template vazar pro texto, quem colar no
        WhatsApp cola com espaços estranhos no início de cada linha."""
        resposta = self.client.get(reverse("solar:detalhe", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        inicio = corpo.index('id="resumo-proposta"')
        conteudo = corpo[inicio : corpo.index("</textarea>", inicio)]
        conteudo = conteudo.split(">", 1)[1]  # remove o resto da tag <textarea ...>

        linhas_com_espaco = [linha for linha in conteudo.split("\n") if linha[:1] in (" ", "\t")]
        self.assertEqual(linhas_com_espaco, [])


# ---------------------------------------------------------------------------
# Parcelamento no cartão (TaxaCartao) — dados reais da tabela Intelbras
# ---------------------------------------------------------------------------


def _seed_taxas_visa_master():
    """Só as linhas de Visa/Master necessárias pros testes — não usa o
    management command aqui pra manter os testes rápidos e isolados."""
    dados = [
        (TaxaCartao.FORMA_CREDITO, 1, "3.49"),
        (TaxaCartao.FORMA_CREDITO, 2, "5.19"),
        (TaxaCartao.FORMA_CREDITO, 3, "5.99"),
        (TaxaCartao.FORMA_CREDITO, 21, "19.99"),
    ]
    for forma, parcelas, pct in dados:
        TaxaCartao.objects.create(
            forma=forma, bandeira=TaxaCartao.BANDEIRA_VISA_MASTER, parcelas=parcelas, percentual=Decimal(pct)
        )


class CalcularParcelaCartaoTests(TestCase):
    """Fórmula verificada manualmente contra a planilha oficial Intelbras
    (base R$750,00, bandeira Visa/Master) antes de escrever este teste:
    débito 1,29% -> R$759,80; 2x 5,19% -> R$791,06/2=R$395,53;
    21x 19,99% -> R$937,38/21=R$44,64. Fórmula: valor/(1-taxa%), NÃO
    valor*(1+taxa%) — as duas contas dão resultados próximos mas diferentes,
    e só a primeira bate com o número real da Intelbras."""

    def setUp(self) -> None:
        _seed_taxas_visa_master()

    def test_valor_1x_bate_com_a_planilha_oficial(self) -> None:
        resultado = calcular_parcela_cartao(Decimal("750.00"), TaxaCartao.BANDEIRA_VISA_MASTER)
        linha_1x = next(r for r in resultado if r["parcelas"] == 1)
        self.assertEqual(linha_1x["valor_total"], Decimal("777.12"))

    def test_valor_2x_bate_com_a_planilha_oficial(self) -> None:
        resultado = calcular_parcela_cartao(Decimal("750.00"), TaxaCartao.BANDEIRA_VISA_MASTER)
        linha_2x = next(r for r in resultado if r["parcelas"] == 2)
        self.assertEqual(linha_2x["valor_total"], Decimal("791.06"))
        self.assertEqual(linha_2x["valor_parcela"], Decimal("395.53"))

    def test_valor_21x_bate_com_a_planilha_oficial(self) -> None:
        resultado = calcular_parcela_cartao(Decimal("750.00"), TaxaCartao.BANDEIRA_VISA_MASTER)
        linha_21x = next(r for r in resultado if r["parcelas"] == 21)
        self.assertEqual(linha_21x["valor_total"], Decimal("937.38"))
        self.assertEqual(linha_21x["valor_parcela"], Decimal("44.64"))

    def test_formula_nao_e_multiplicar_pela_taxa(self) -> None:
        """Trava a regressão do erro mais fácil de cometer aqui: usar
        valor*(1+taxa) em vez de valor/(1-taxa). Pra 21x (19,99%), a conta
        errada daria R$899,93 — bem diferente do R$937,38 real."""
        resultado = calcular_parcela_cartao(Decimal("750.00"), TaxaCartao.BANDEIRA_VISA_MASTER)
        linha_21x = next(r for r in resultado if r["parcelas"] == 21)
        formula_errada = Decimal("750.00") * (Decimal("1") + Decimal("19.99") / 100)
        self.assertNotEqual(linha_21x["valor_total"], formula_errada.quantize(Decimal("0.01")))

    def test_valor_base_zero_ou_negativo_retorna_vazio(self) -> None:
        self.assertEqual(calcular_parcela_cartao(Decimal("0"), TaxaCartao.BANDEIRA_VISA_MASTER), [])
        self.assertEqual(calcular_parcela_cartao(Decimal("-10"), TaxaCartao.BANDEIRA_VISA_MASTER), [])

    def test_bandeira_sem_taxa_cadastrada_retorna_vazio(self) -> None:
        self.assertEqual(calcular_parcela_cartao(Decimal("750.00"), TaxaCartao.BANDEIRA_ELO), [])

    def test_resultado_ordenado_por_quantidade_de_parcelas(self) -> None:
        resultado = calcular_parcela_cartao(Decimal("750.00"), TaxaCartao.BANDEIRA_VISA_MASTER)
        self.assertEqual([r["parcelas"] for r in resultado], [1, 2, 3, 21])


class SeedTaxasCartaoTests(TestCase):
    def test_comando_cria_87_linhas(self) -> None:
        call_command("seed_taxas_cartao")
        self.assertEqual(TaxaCartao.objects.count(), 87)

    def test_comando_e_idempotente(self) -> None:
        call_command("seed_taxas_cartao")
        call_command("seed_taxas_cartao")
        self.assertEqual(TaxaCartao.objects.count(), 87)

    def test_amex_e_hiper_nao_tem_linha_de_debito(self) -> None:
        call_command("seed_taxas_cartao")
        self.assertFalse(
            TaxaCartao.objects.filter(
                forma=TaxaCartao.FORMA_DEBITO, bandeira__in=[TaxaCartao.BANDEIRA_AMEX, TaxaCartao.BANDEIRA_HIPER]
            ).exists()
        )


class ResumoFechamentoComCartaoTests(TestCase):
    """Integração via HTTP do bloco de parcelamento no card de resumo."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.modulo = _modulo()
        cls.proposta = PropostaSolar.objects.create(
            cliente=_cliente(), consumo_medio_kwh=600, hsp=Decimal("5.50"),
            fator_eficiencia=Decimal("0.75"), potencia_kwp=Decimal("4.880"),
            quantidade_modulos=8, modulo=cls.modulo, valor_instalacao=Decimal("5000.00"),
        )
        ItemPropostaSolar.objects.create(
            proposta=cls.proposta, modulo=cls.modulo, quantidade=8,
            preco_venda_snapshot=Decimal("885.125"), preco_custo_snapshot=Decimal("700"),
            data_referencia_preco=date.today(),
        )
        # valor_equipamentos = 8 * 885.125 = 7081.00 | valor_total = 7081 + 5000 = 12081.00
        cls.user = User.objects.create_user(username="vend_cartao", password="senha-de-teste")
        cls.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])

    def setUp(self) -> None:
        self.client.force_login(self.user)
        _seed_taxas_visa_master()

    def test_padrao_e_visa_master_com_entrada(self) -> None:
        resposta = self.client.get(reverse("solar:detalhe", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        self.assertIn('value="visa_master" selected', corpo)
        self.assertIn('value="1" selected', corpo)
        self.assertIn("Entrada de R$ 5.000,00", corpo)

    def test_sem_entrada_financia_o_valor_total(self) -> None:
        resposta = self.client.get(
            reverse("solar:resumo_fechamento", args=[self.proposta.pk]), {"com_entrada": "0"}
        )
        corpo = resposta.content.decode("utf-8")

        self.assertIn("Parcelamento de 100% no cartão", corpo)
        self.assertNotIn("Entrada de R$", corpo)
        # 1x sobre 12081.00 a 3.49% = 12081/0.9651 = 12517.87 (conferido: 0.9651*12517.87 = 12081.00)
        self.assertIn("R$ 12.517,87", corpo)

    def test_bandeira_invalida_cai_para_visa_master(self) -> None:
        resposta = self.client.get(
            reverse("solar:resumo_fechamento", args=[self.proposta.pk]), {"bandeira": "bandeira-que-nao-existe"}
        )

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.content.decode("utf-8")
        self.assertIn('value="visa_master" selected', corpo)

    def test_tabela_completa_de_2x_a_21x_aparece(self) -> None:
        """Diferente do PDF (que privilegia enxugar), o resumo de WhatsApp
        mostra a tabela cheia — decisão explícita do usuário."""
        call_command("seed_taxas_cartao")
        resposta = self.client.get(reverse("solar:detalhe", args=[self.proposta.pk]))
        corpo = resposta.content.decode("utf-8")

        for parcelas in (2, 12, 21):
            self.assertIn(f"{parcelas}x\t", corpo)
