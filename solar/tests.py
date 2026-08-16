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
from .models import (
    EstruturaFixacao,
    Inversor,
    ItemPropostaSolar,
    MateriaisEletricos,
    ModuloFotovoltaico,
    PrecoEquipamentoSolar,
    PropostaSolar,
    TaxaCartao,
)
from .services import (
    formatar_prazo,
    grafico_economia_anual,
    percentual_fio_b,
    projetar_retorno,
    tarifa_compensacao,
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
        self.assertIn("Total", corpo)

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
        self.assertNotIn("R$ 600,00", corpo)
        self.assertNotIn("R$ 4000,00", corpo)

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


class RetornoGDContraFaturaRealTests(TestCase):
    """Âncora de verificação do motor de cálculo: reproduz uma fatura real
    da Energisa Tocantins (B1 residencial monofásico, referência agosto/2026,
    consumidor GD). Se algum destes testes quebrar, o cálculo deixou de
    corresponder ao que a distribuidora realmente cobra."""

    TARIFA = Decimal("1.385750")   # linha "Consumo em kWh", com tributos
    FIO_B = Decimal("0.313783")    # padrão de Configuracao
    CONSUMO = Decimal("547")       # kWh lidos do medidor
    INJETADA = Decimal("499")      # kWh injetados na rede
    COSIP = Decimal("42.14")       # Contrib de Ilum Pub

    def test_tarifa_de_compensacao_bate_com_a_linha_gdi_da_fatura(self) -> None:
        """A fatura credita a energia injetada a 1,197480 R$/kWh, não à
        tarifa cheia de 1,385750 — a diferença é o Fio B a 60% (2026)."""
        tarifa = tarifa_compensacao(self.TARIFA, self.FIO_B, 2026)

        self.assertEqual(tarifa.quantize(Decimal("0.000001")), Decimal("1.197480"))

    def test_valor_creditado_bate_com_a_fatura(self) -> None:
        tarifa = tarifa_compensacao(self.TARIFA, self.FIO_B, 2026)
        creditado = (self.INJETADA * tarifa).quantize(Decimal("0.01"))

        self.assertEqual(creditado, Decimal("597.54"))

    def test_conta_estimada_reproduz_a_fatura(self) -> None:
        """Fatura real: 758,00 (consumo) − 597,54 (injetada) + 42,14 (COSIP)
        + 1,25 (bandeira) − 4,46 (bônus Itaipu) = 199,39.

        O motor não modela bandeira nem bônus (itens transitórios), então
        deve fechar em ~202,60 — a fatura sem essas duas linhas.

        Tolerância de 2 centavos porque a distribuidora arredonda cada
        linha antes de somar e a tarifa impressa (1,385750) já é um
        arredondamento da tarifa-base com gross-up de tributos. Exigir
        igualdade ao centavo seria ajustar o cálculo a artefato de
        arredondamento, não à regra de negócio."""
        # 100% injetado: é o cenário que a fatura registra (o medidor só vê
        # o que passa pela rede).
        retorno = projetar_retorno(
            valor_investimento=Decimal("20000"),
            geracao_mensal_kwh=self.INJETADA,
            consumo_mensal_kwh=self.CONSUMO,
            tarifa_kwh=self.TARIFA,
            tusd_fio_b_kwh=self.FIO_B,
            tipo_ligacao="monofasico",
            cosip_mensal=self.COSIP,
            ano_base=2026,
            autoconsumo_simultaneo_pct=Decimal("0"),
        )

        self.assertEqual(retorno["economia_mensal"], Decimal("597.54"))

        total_modelado = retorno["conta_estimada"] + Decimal("1.25") - Decimal("4.46")
        self.assertAlmostEqual(
            total_modelado,
            Decimal("199.39"),
            delta=Decimal("0.02"),
            msg="deveria fechar com o total real da fatura (R$ 199,39)",
        )


class ProjetarRetornoTests(TestCase):
    """Regras de GD que o cálculo ingênuo (geração × tarifa) ignorava."""

    BASE = dict(
        valor_investimento=Decimal("20000"),
        geracao_mensal_kwh=Decimal("500"),
        consumo_mensal_kwh=Decimal("500"),
        tarifa_kwh=Decimal("1.385750"),
        tusd_fio_b_kwh=Decimal("0.313783"),
        tipo_ligacao="monofasico",
        cosip_mensal=Decimal("42.14"),
        ano_base=2026,
    )

    def test_economia_e_menor_que_geracao_vezes_tarifa(self) -> None:
        """Regressão do bug original: o cálculo antigo era geração × tarifa
        cheia, que superestima porque ignora Fio B e custo de
        disponibilidade."""
        retorno = projetar_retorno(**self.BASE)
        ingenuo = Decimal("500") * Decimal("1.385750")

        self.assertLess(retorno["economia_mensal"], ingenuo)

    def test_custo_de_disponibilidade_limita_a_compensacao(self) -> None:
        """Mesmo gerando muito mais que consome, o cliente monofásico segue
        pagando os 30 kWh mínimos."""
        retorno = projetar_retorno(**{**self.BASE, "geracao_mensal_kwh": Decimal("5000")})

        self.assertEqual(retorno["custo_disponibilidade_kwh"], 30)
        self.assertEqual(retorno["compensada_mensal_kwh"], Decimal("470.00"))  # 500 − 30

    def test_trifasico_paga_minimo_maior(self) -> None:
        retorno = projetar_retorno(**{**self.BASE, "tipo_ligacao": "trifasico"})

        self.assertEqual(retorno["custo_disponibilidade_kwh"], 100)
        self.assertEqual(retorno["compensada_mensal_kwh"], Decimal("400.00"))  # 500 − 100

    def test_autoconsumo_simultaneo_economiza_mais_que_injetar(self) -> None:
        """O kWh consumido na hora não passa pela rede, logo não sofre Fio B
        — vale a tarifa cheia, mais que o kWh injetado."""
        sem = projetar_retorno(**{**self.BASE, "autoconsumo_simultaneo_pct": Decimal("0")})
        com = projetar_retorno(**{**self.BASE, "autoconsumo_simultaneo_pct": Decimal("50")})

        self.assertGreater(com["economia_mensal"], sem["economia_mensal"])

    def test_autoconsumo_total_economiza_a_tarifa_cheia(self) -> None:
        retorno = projetar_retorno(
            **{**self.BASE, "autoconsumo_simultaneo_pct": Decimal("100")}
        )
        cheia = (Decimal("500") * Decimal("1.385750")).quantize(Decimal("0.01"))

        self.assertEqual(retorno["autoconsumo_mensal_kwh"], Decimal("500.00"))
        self.assertEqual(retorno["economia_mensal"], cheia)

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
        self.assertIsNone(projetar_retorno(**{**self.BASE, "tarifa_kwh": None}))

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
            tarifa_kwh=Decimal("1.385750"),
            tusd_fio_b_kwh=Decimal("0.313783"),
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

    def test_usa_os_parametros_regionais_de_configuracao(self) -> None:
        """Fio B e COSIP vêm do painel de Configurações, não hardcoded."""
        from configuracoes.models import Configuracao

        config = Configuracao.atual()
        config.tusd_fio_b_kwh = Decimal("0")
        config.save()

        proposta = _proposta(self.modulo)
        proposta.tarifa_kwh = Decimal("1.00")
        proposta.autoconsumo_simultaneo_pct = Decimal("0")
        proposta.save()

        # Sem Fio B, cada kWh compensado vale a tarifa cheia.
        retorno = proposta.retorno_financeiro
        self.assertEqual(retorno["fluxo_anual"][0]["tarifa_compensacao"], Decimal("1.000000"))

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
