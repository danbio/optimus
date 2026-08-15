"""Testes do app solar."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
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
        pro cliente."""
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
