from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.permissoes import GRUPO_ADMIN
from estoque.models import Produto

from .models import ItemVenda, Venda


class FinalizacaoVendaEstoqueTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operador", password="senha123")
        # Estes testes verificam regra de negócio, não permissão: o usuário
        # recebe acesso total para não esbarrar no RBAC. A matriz de acesso é
        # testada em core/tests.py.
        self.user.groups.add(Group.objects.get_or_create(name=GRUPO_ADMIN)[0])
        self.client.force_login(self.user)

    def test_finalizar_venda_baixa_estoque(self):
        produto = Produto.objects.create(
            codigo=70001,
            descricao="Camera",
            pscf=Decimal("120.00"),
            quantidade_estoque=Decimal("10.00"),
        )
        venda = Venda.objects.create(forma_pagamento="pix", num_parcelas=1)
        ItemVenda.objects.create(
            venda=venda,
            produto=produto,
            quantidade=Decimal("3.00"),
            valor_unitario=Decimal("120.00"),
        )

        self.client.post(reverse("balcao:finalizar", kwargs={"pk": venda.pk}), follow=True)

        venda.refresh_from_db()
        produto.refresh_from_db()
        self.assertEqual(venda.status, Venda.STATUS_FINALIZADA)
        self.assertEqual(produto.quantidade_estoque, Decimal("7.00"))

    def test_nao_finaliza_venda_com_estoque_insuficiente(self):
        produto = Produto.objects.create(
            codigo=70002,
            descricao="DVR",
            pscf=Decimal("500.00"),
            quantidade_estoque=Decimal("1.00"),
        )
        venda = Venda.objects.create(forma_pagamento="pix", num_parcelas=1)
        ItemVenda.objects.create(
            venda=venda,
            produto=produto,
            quantidade=Decimal("2.00"),
            valor_unitario=Decimal("500.00"),
        )

        resposta = self.client.post(reverse("balcao:finalizar", kwargs={"pk": venda.pk}), follow=True)

        venda.refresh_from_db()
        produto.refresh_from_db()
        self.assertEqual(venda.status, Venda.STATUS_RASCUNHO)
        self.assertEqual(produto.quantidade_estoque, Decimal("1.00"))
        self.assertContains(resposta, "Estoque insuficiente para finalizar a venda")
