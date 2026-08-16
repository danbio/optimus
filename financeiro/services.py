"""
Funções helper para criação de lançamentos financeiros a partir dos outros apps.
Cada app de origem chama a função correspondente — nunca acessa LancamentoFinanceiro diretamente.
"""

import datetime

from django.utils import timezone


def _criar_parcelas(lancamento, num_parcelas, data_vencimento_base):
    from .models import ParcelaLancamento

    if num_parcelas <= 0:
        num_parcelas = 1

    valor_parcela = round(lancamento.valor_liquido / num_parcelas, 2)
    # Ajuste de centavos na última parcela
    total_parcelas = valor_parcela * (num_parcelas - 1)
    valor_ultima = lancamento.valor_liquido - total_parcelas

    for i in range(1, num_parcelas + 1):
        vencimento = data_vencimento_base + datetime.timedelta(days=30 * (i - 1))
        ParcelaLancamento.objects.create(
            lancamento=lancamento,
            numero_parcela=i,
            valor=valor_parcela if i < num_parcelas else valor_ultima,
            data_vencimento=vencimento,
        )


def criar_lancamento_de_proposta_solar(proposta):
    """Chamado em solar/views.py quando proposta muda para 'aprovada'.

    Lança **só os equipamentos**. A mão de obra entra depois, quando a OS é
    faturada (ver `criar_lancamento_de_ordem_servico`) — segue o caixa
    real: o gerador é comprado no início, a instalação só se paga na
    entrega. Somados, os dois fecham `proposta.valor_total`.

    ⚠️ Até 2026-08-16 os dois lançavam `valor_total`, cobrando o cliente em
    dobro. Ver `FaturamentoSolarSemDuplicidadeTests`.
    """
    from .models import LancamentoFinanceiro

    # Evitar duplicata
    if LancamentoFinanceiro.objects.filter(proposta_solar=proposta).exists():
        return None

    valor = proposta.valor_equipamentos or 0
    if valor <= 0:
        return None

    lan = LancamentoFinanceiro.objects.create(
        descricao=f"Proposta Solar {proposta.numero} — equipamentos",
        cliente=proposta.cliente,
        proposta_solar=proposta,
        valor_bruto=valor,
        desconto=0,
        data_vencimento=timezone.localdate() + datetime.timedelta(days=30),
    )
    _criar_parcelas(lan, 1, lan.data_vencimento)
    return lan


def criar_lancamento_de_proposta_servico(proposta):
    """Chamado em servicos/views.py quando proposta muda para 'aprovada'."""
    from .models import LancamentoFinanceiro

    if LancamentoFinanceiro.objects.filter(proposta_servico=proposta).exists():
        return None

    lan = LancamentoFinanceiro.objects.create(
        descricao=f"Proposta de Serviço {proposta.numero} — {proposta.get_tipo_servico_display()}",
        cliente=proposta.cliente,
        proposta_servico=proposta,
        valor_bruto=proposta.valor_total,
        desconto=0,
        data_vencimento=timezone.localdate() + datetime.timedelta(days=30),
    )
    _criar_parcelas(lan, 1, lan.data_vencimento)
    return lan


def criar_lancamento_de_ordem_servico(os_obj):
    """Chamado em ordens_servico/views.py quando OS muda para 'faturada'.

    Quando a OS vem de uma proposta, lança **só a mão de obra**: os
    equipamentos já foram lançados na aprovação da proposta. Lançar o valor
    total aqui cobraria o cliente duas vezes — foi exatamente o bug que a
    auditoria de 2026-08-16 encontrou.
    """
    from .models import LancamentoFinanceiro

    if LancamentoFinanceiro.objects.filter(ordem_servico=os_obj).exists():
        return None

    valor = 0
    descricao = f"Ordem de Serviço {os_obj.numero}"
    if os_obj.proposta_solar:
        valor = os_obj.proposta_solar.valor_instalacao or 0
        descricao = f"OS {os_obj.numero} — instalação Solar {os_obj.proposta_solar.numero}"
    elif os_obj.proposta_servico:
        valor = os_obj.proposta_servico.valor_total
        descricao = f"OS {os_obj.numero} — Serviço {os_obj.proposta_servico.numero}"

    # Sem valor a cobrar não se cria lançamento: R$ 0,00 no contas a receber
    # é ruído que ninguém sabe baixar.
    if valor <= 0:
        return None

    lan = LancamentoFinanceiro.objects.create(
        descricao=descricao,
        cliente=os_obj.cliente,
        ordem_servico=os_obj,
        valor_bruto=valor,
        desconto=0,
        data_vencimento=timezone.localdate(),
    )
    _criar_parcelas(lan, 1, lan.data_vencimento)
    return lan


def criar_lancamento_de_venda_balcao(venda):
    """Chamado em balcao/views.py ao finalizar venda."""
    from .models import LancamentoFinanceiro

    if LancamentoFinanceiro.objects.filter(venda_balcao=venda).exists():
        return None

    cliente = venda.cliente
    if cliente is None:
        # Venda avulsa sem cadastro — usa cliente genérico ou cria sem FK
        # Neste caso, o campo cliente é obrigatório no model; precisamos de um cliente.
        # A view de finalizar_venda deve garantir que, se não há cliente, a venda fica sem lançamento
        # ou o operador é responsável. Por ora, não criamos lançamento para vendas avulsas sem cliente.
        return None

    lan = LancamentoFinanceiro.objects.create(
        descricao=f"Venda Balcão {venda.numero}",
        cliente=cliente,
        venda_balcao=venda,
        valor_bruto=venda.subtotal,
        desconto=venda.desconto_reais,
        forma_pagamento=venda.forma_pagamento,
        num_parcelas=venda.num_parcelas,
        data_vencimento=timezone.localdate(),
    )
    _criar_parcelas(lan, venda.num_parcelas, lan.data_vencimento)

    # Pagamento à vista: baixa automática
    if venda.num_parcelas == 1 and venda.forma_pagamento in ("dinheiro", "pix", "cartao_debito"):
        from .models import BaixaFinanceira

        parcela = lan.parcelas.first()
        BaixaFinanceira.objects.create(
            lancamento=lan,
            parcela=parcela,
            valor=lan.valor_liquido,
            forma_pagamento=venda.forma_pagamento,
            data_pagamento=timezone.localdate(),
            registrado_por=venda.operador,
        )
        lan.valor_recebido = lan.valor_liquido
        lan.status = LancamentoFinanceiro.STATUS_LIQUIDADO
        lan.data_liquidacao = timezone.localdate()
        lan.save()
        if parcela:
            parcela.status = parcela.STATUS_PAGO
            parcela.data_pagamento = timezone.localdate()
            parcela.valor_pago = lan.valor_liquido
            parcela.save()

    return lan
