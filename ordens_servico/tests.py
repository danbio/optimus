from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clientes.models import Cliente
from servicos.models import PropostaServico

from .models import OrdemServico, Tecnico


class OrdemServicoRegraNegocioTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="tester", password="senha123")
        self.client.force_login(self.usuario)

        self.cliente_a = Cliente.objects.create(cpf_cnpj="11111111111", nome="Cliente A")
        self.cliente_b = Cliente.objects.create(cpf_cnpj="22222222222", nome="Cliente B")
        self.tecnico = Tecnico.objects.create(nome="Tecnico 1", especialidade="geral")
        self.proposta = PropostaServico.objects.create(
            cliente=self.cliente_a,
            tipo_servico="seguranca",
            status=PropostaServico.STATUS_APROVADA,
            validade=timezone.localdate() + timedelta(days=30),
        )

    def test_model_rejeita_cliente_diferente_da_proposta_vinculada(self):
        os_obj = OrdemServico(
            cliente=self.cliente_b,
            proposta_servico=self.proposta,
            tecnico=self.tecnico,
        )

        with self.assertRaises(ValidationError):
            os_obj.clean()

    def test_agendamento_no_passado_nao_altera_status(self):
        os_obj = OrdemServico.objects.create(cliente=self.cliente_a, tecnico=self.tecnico, proposta_servico=self.proposta)
        data_passada = (timezone.localtime() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

        resposta = self.client.post(
            reverse("ordens_servico:agendar", kwargs={"pk": os_obj.pk}),
            {"data_agendamento": data_passada},
            follow=True,
        )

        os_obj.refresh_from_db()
        self.assertEqual(os_obj.status, OrdemServico.STATUS_ABERTA)
        self.assertIsNone(os_obj.data_agendamento)
        self.assertContains(resposta, "data de agendamento válida e futura")

    def test_concluir_os_nao_conclui_proposta_se_existe_outra_pendente(self):
        os_execucao = OrdemServico.objects.create(
            cliente=self.cliente_a,
            tecnico=self.tecnico,
            proposta_servico=self.proposta,
            status=OrdemServico.STATUS_EM_EXECUCAO,
        )
        OrdemServico.objects.create(
            cliente=self.cliente_a,
            tecnico=self.tecnico,
            proposta_servico=self.proposta,
            status=OrdemServico.STATUS_AGENDADA,
        )

        self.client.post(
            reverse("ordens_servico:concluir", kwargs={"pk": os_execucao.pk}),
            {"assinatura_nome": "Cliente A", "assinatura_confirmada": "on"},
            follow=True,
        )

        os_execucao.refresh_from_db()
        self.proposta.refresh_from_db()
        self.assertEqual(os_execucao.status, OrdemServico.STATUS_CONCLUIDA)
        self.assertEqual(self.proposta.status, PropostaServico.STATUS_APROVADA)

    def test_concluir_os_conclui_proposta_quando_nao_ha_pendencias(self):
        os_execucao = OrdemServico.objects.create(
            cliente=self.cliente_a,
            tecnico=self.tecnico,
            proposta_servico=self.proposta,
            status=OrdemServico.STATUS_EM_EXECUCAO,
        )

        self.client.post(
            reverse("ordens_servico:concluir", kwargs={"pk": os_execucao.pk}),
            {"assinatura_nome": "Cliente A", "assinatura_confirmada": "on"},
            follow=True,
        )

        os_execucao.refresh_from_db()
        self.proposta.refresh_from_db()
        self.assertEqual(os_execucao.status, OrdemServico.STATUS_CONCLUIDA)
        self.assertEqual(self.proposta.status, PropostaServico.STATUS_CONCLUIDA)
