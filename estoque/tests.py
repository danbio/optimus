"""
Testes E2E do app estoque.

Execução:
    python manage.py test estoque -v 2
"""

import io

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Produto


def _xlsx(rows: list[list]) -> bytes:
    """Cria um arquivo xlsx em memória a partir de uma lista de linhas."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload(conteudo: bytes, nome: str = "tabela.xlsx"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(nome, conteudo, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class ImportacaoTest(TestCase):
    URL = "/estoque/importar/"

    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@test.com", "senha123")
        self.client.login(username="admin", password="senha123")

    # ── 1. Importação básica ───────────────────────────────────────────────────

    def test_importar_planilha_minima(self):
        """Importa planilha com colunas mínimas e verifica criação dos produtos."""
        xlsx = _xlsx(
            [
                ["Codigo", "Descricao", "PSD", "PSCF"],
                [10001, "Câmera IP 4MP Full HD", 450.00, 699.00],
                [10002, "DVR 8 Canais Full HD", 800.00, 1200.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "2 criado")

        self.assertEqual(Produto.objects.count(), 2)
        cam = Produto.objects.get(codigo=10001)
        self.assertEqual(cam.descricao, "Câmera IP 4MP Full HD")
        self.assertAlmostEqual(float(cam.psd), 450.00)
        self.assertAlmostEqual(float(cam.pscf), 699.00)

    # ── 2. Cabeçalhos acentuados (padrão planilha Intelbras) ───────────────────

    def test_importar_cabecalhos_acentuados(self):
        """Colunas com acentos (Código, Descrição) devem ser reconhecidas."""
        xlsx = _xlsx(
            [
                ["Código", "Descrição", "IPI (%)", "ICMS (%)", "PSD", "PSCF"],
                [20001, "Interfone Externo", 0.0, 12.0, 150.00, 280.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 criado")
        p = Produto.objects.get(codigo=20001)
        self.assertAlmostEqual(float(p.ipi), 0.0)
        self.assertAlmostEqual(float(p.icms), 12.0)

    def test_importar_ipi_icms_formato_decimal(self):
        """IPI/ICMS em formato decimal (0.065) deve ser convertido para percentual (6.50)."""
        xlsx = _xlsx(
            [
                ["Codigo Produto", "Descricao do Produto", "Unidade", "IPI", "ICMS", "PSD", "PSCF", "Qtd. Multipla", "Preco Referencia"],
                [70001, "Câmera IP 4MP", "BU SEGURANCA", 0.065, 0.04, 649.56, 844.70, 1.0, "PSD"],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 criado")
        p = Produto.objects.get(codigo=70001)
        self.assertAlmostEqual(float(p.ipi), 6.50)
        self.assertAlmostEqual(float(p.icms), 4.00)
        self.assertAlmostEqual(float(p.psd), 649.56)
        self.assertEqual(p.bu, "BU SEGURANCA")
        self.assertEqual(p.preco_referencia, "PSD")

    def test_importar_coluna_exata_prevalece_sobre_alias(self):
        """Coluna 'PSD' deve ser mapeada mesmo quando alias genérico ('Custo') aparece antes.
        Replica estrutura real da tabela Intelbras: PV/Custo/PP são fórmulas (None),
        PSD/PSCF vêm depois com valores reais."""
        xlsx = _xlsx(
            [
                ["Codigo Produto", "Descricao do Produto", "PV", "Custo", "PP", "PSD", "PSCF"],
                [90001, "Câmera Dome 4MP", None, None, None, 550.00, 850.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 criado")
        p = Produto.objects.get(codigo=90001)
        self.assertAlmostEqual(float(p.psd), 550.00)
        self.assertAlmostEqual(float(p.pscf), 850.00)

    def test_importar_deduplica_por_codigo(self):
        """Produto repetido por UF deve ser importado apenas uma vez."""
        xlsx = _xlsx(
            [
                ["Codigo Produto", "Descricao do Produto", "PSD", "PSCF"],
                [80001, "Produto repetido SC", 100.00, 200.00],
                [80001, "Produto repetido PE", 100.00, 200.00],
                [80001, "Produto repetido RJ", 100.00, 200.00],
                [80002, "Produto único", 50.00, 90.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "2 criado")
        self.assertEqual(Produto.objects.count(), 2)

    # ── 3. Linhas de cabeçalho antes da linha de colunas ─────────────────────

    def test_importar_com_linhas_iniciais_ignoradas(self):
        """Planilhas com linhas de título antes do cabeçalho devem ser aceitas."""
        xlsx = _xlsx(
            [
                ["Tabela de Preços Intelbras", None, None, None],
                ["Válida para revendas autorizadas", None, None, None],
                ["Vigência: 01/2025", None, None, None],
                [None, None, None, None],
                ["Codigo", "Descricao", "PSD", "PSCF"],
                [30001, "Kit Alarme Residencial", 320.00, 520.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 criado")
        self.assertTrue(Produto.objects.filter(codigo=30001).exists())

    # ── 4. Atualização de produto existente ────────────────────────────────────

    def test_importar_atualiza_existente(self):
        """Produto com mesmo código deve ser atualizado, não duplicado."""
        Produto.objects.create(codigo=40001, descricao="Versão Antiga", psd=100, pscf=200)

        xlsx = _xlsx(
            [
                ["Codigo", "Descricao", "PSD", "PSCF"],
                [40001, "Versão Atualizada", 110.00, 220.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 atualizado")
        self.assertEqual(Produto.objects.count(), 1)
        p = Produto.objects.get(codigo=40001)
        self.assertEqual(p.descricao, "Versão Atualizada")
        self.assertAlmostEqual(float(p.psd), 110.00)

    # ── 5. Mistura: criação + atualização ─────────────────────────────────────

    def test_importar_cria_e_atualiza(self):
        """Importação deve criar novos e atualizar existentes na mesma planilha."""
        Produto.objects.create(codigo=50001, descricao="Já existe", psd=10, pscf=20)

        xlsx = _xlsx(
            [
                ["Codigo", "Descricao", "PSD", "PSCF"],
                [50001, "Já existe — atualizado", 11.00, 22.00],
                [50002, "Produto novo", 30.00, 50.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 criado")
        self.assertContains(resp, "1 atualizado")
        self.assertEqual(Produto.objects.count(), 2)

    # ── 6. Arquivo com formato inválido ───────────────────────────────────────

    def test_formato_invalido_rejeitado(self):
        """Upload de CSV deve ser rejeitado na validação do form."""
        csv = b"Codigo,Descricao\n10001,Teste"
        arquivo = __import__("django.core.files.uploadedfile", fromlist=["SimpleUploadedFile"]).SimpleUploadedFile("tabela.csv", csv, content_type="text/csv")
        resp = self.client.post(self.URL, {"arquivo": arquivo})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Formato inválido")

    # ── 7. Linhas sem código são ignoradas sem derrubar a importação ──────────

    def test_linhas_sem_codigo_sao_ignoradas(self):
        """Linhas onde o código não é número devem ser contadas como erros, não exceção."""
        xlsx = _xlsx(
            [
                ["Codigo", "Descricao", "PSD", "PSCF"],
                ["abc", "Linha inválida", 10.00, 20.00],
                [60001, "Produto válido", 50.00, 90.00],
            ]
        )
        resp = self.client.post(self.URL, {"arquivo": _upload(xlsx)}, follow=True)

        self.assertContains(resp, "1 criado")
        self.assertContains(resp, "1 linha(s) com erro")
        self.assertEqual(Produto.objects.count(), 1)

    # ── 8. CRUD básico via views ───────────────────────────────────────────────

    def test_criar_produto_via_form(self):
        """Cadastro manual de produto via formulário."""
        resp = self.client.post(
            reverse("estoque:novo"),
            {
                "codigo": 99001,
                "descricao": "Produto Teste Form",
                "psd": "100.00",
                "pscf": "180.00",
                "ipi": "0.00",
                "icms": "12.00",
                "qtd_multipla": "1.00",
                "ativo": "on",
            },
            follow=True,
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Produto.objects.filter(codigo=99001).exists())

    def test_lista_produtos_requer_login(self):
        """Lista de produtos deve redirecionar usuário não autenticado."""
        self.client.logout()
        resp = self.client.get(reverse("estoque:lista"))
        self.assertRedirects(resp, "/login/?next=/estoque/")

    def test_busca_por_codigo_numerico(self):
        """Busca pelo código numérico deve retornar o produto correto."""
        Produto.objects.create(codigo=12345, descricao="Câmera de Segurança", psd=300, pscf=500)
        Produto.objects.create(codigo=67890, descricao="Alarme Residencial", psd=200, pscf=350)

        resp = self.client.get(reverse("estoque:lista") + "?q=12345")
        self.assertContains(resp, "Câmera de Segurança")
        self.assertNotContains(resp, "Alarme Residencial")
