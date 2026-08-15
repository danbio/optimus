"""
Popula a tabela de acréscimo de cartão (TaxaCartao) com os dados oficiais
da tabela Intelbras "Simulador de Acréscimo ao Portador", fornecida pelo
usuário em 2026-08-13 (planilha Google Sheets, exportação CSV verificada).

Uso: python manage.py seed_taxas_cartao

Idempotente — rodar de novo não duplica, só atualiza o percentual se já
existir a combinação forma+bandeira+parcelas (get_or_create com defaults
não atualiza; usar update_or_create pra refletir correções da Intelbras
ao rodar de novo).
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from solar.models import TaxaCartao

VISA_MASTER = TaxaCartao.BANDEIRA_VISA_MASTER
AMEX = TaxaCartao.BANDEIRA_AMEX
ELO = TaxaCartao.BANDEIRA_ELO
HIPER = TaxaCartao.BANDEIRA_HIPER

DEBITO = TaxaCartao.FORMA_DEBITO
CREDITO = TaxaCartao.FORMA_CREDITO
PIX = TaxaCartao.FORMA_PIX

# (forma, bandeira, parcelas, percentual) — só as combinações que a
# planilha realmente lista. Amex e Hiper não têm linha de Débito.
TAXAS = [
    (DEBITO, VISA_MASTER, 1, "1.29"),
    (DEBITO, ELO, 1, "2.49"),
    (CREDITO, VISA_MASTER, 1, "3.49"),
    (CREDITO, AMEX, 1, "4.29"),
    (CREDITO, ELO, 1, "4.99"),
    (CREDITO, HIPER, 1, "4.99"),
    (CREDITO, VISA_MASTER, 2, "5.19"),
    (CREDITO, AMEX, 2, "5.74"),
    (CREDITO, ELO, 2, "6.29"),
    (CREDITO, HIPER, 2, "6.29"),
    (CREDITO, VISA_MASTER, 3, "5.99"),
    (CREDITO, AMEX, 3, "6.54"),
    (CREDITO, ELO, 3, "7.09"),
    (CREDITO, HIPER, 3, "7.09"),
    (CREDITO, VISA_MASTER, 4, "6.67"),
    (CREDITO, AMEX, 4, "7.23"),
    (CREDITO, ELO, 4, "7.79"),
    (CREDITO, HIPER, 4, "7.79"),
    (CREDITO, VISA_MASTER, 5, "7.39"),
    (CREDITO, AMEX, 5, "7.94"),
    (CREDITO, ELO, 5, "8.49"),
    (CREDITO, HIPER, 5, "8.49"),
    (CREDITO, VISA_MASTER, 6, "7.99"),
    (CREDITO, AMEX, 6, "8.59"),
    (CREDITO, ELO, 6, "9.19"),
    (CREDITO, HIPER, 6, "9.19"),
    (CREDITO, VISA_MASTER, 7, "8.79"),
    (CREDITO, AMEX, 7, "9.39"),
    (CREDITO, ELO, 7, "9.99"),
    (CREDITO, HIPER, 7, "9.99"),
    (CREDITO, VISA_MASTER, 8, "9.49"),
    (CREDITO, AMEX, 8, "9.99"),
    (CREDITO, ELO, 8, "10.59"),
    (CREDITO, HIPER, 8, "10.59"),
    (CREDITO, VISA_MASTER, 9, "9.99"),
    (CREDITO, AMEX, 9, "10.64"),
    (CREDITO, ELO, 9, "11.29"),
    (CREDITO, HIPER, 9, "11.29"),
    (CREDITO, VISA_MASTER, 10, "10.99"),
    (CREDITO, AMEX, 10, "11.49"),
    (CREDITO, ELO, 10, "11.99"),
    (CREDITO, HIPER, 10, "11.99"),
    (CREDITO, VISA_MASTER, 11, "11.59"),
    (CREDITO, AMEX, 11, "12.09"),
    (CREDITO, ELO, 11, "12.59"),
    (CREDITO, HIPER, 11, "12.59"),
    (CREDITO, VISA_MASTER, 12, "12.29"),
    (CREDITO, AMEX, 12, "12.79"),
    (CREDITO, ELO, 12, "13.29"),
    (CREDITO, HIPER, 12, "13.29"),
    (CREDITO, VISA_MASTER, 13, "12.64"),
    (CREDITO, AMEX, 13, "13.26"),
    (CREDITO, ELO, 13, "14.29"),
    (CREDITO, HIPER, 13, "14.29"),
    (CREDITO, VISA_MASTER, 14, "12.99"),
    (CREDITO, AMEX, 14, "14.14"),
    (CREDITO, ELO, 14, "15.29"),
    (CREDITO, HIPER, 14, "15.29"),
    (CREDITO, VISA_MASTER, 15, "13.99"),
    (CREDITO, AMEX, 15, "15.14"),
    (CREDITO, ELO, 15, "16.29"),
    (CREDITO, HIPER, 15, "16.29"),
    (CREDITO, VISA_MASTER, 16, "14.99"),
    (CREDITO, AMEX, 16, "16.14"),
    (CREDITO, ELO, 16, "17.29"),
    (CREDITO, HIPER, 16, "17.29"),
    (CREDITO, VISA_MASTER, 17, "15.99"),
    (CREDITO, AMEX, 17, "17.14"),
    (CREDITO, ELO, 17, "18.29"),
    (CREDITO, HIPER, 17, "18.29"),
    (CREDITO, VISA_MASTER, 18, "16.99"),
    (CREDITO, AMEX, 18, "18.14"),
    (CREDITO, ELO, 18, "19.29"),
    (CREDITO, HIPER, 18, "19.29"),
    (CREDITO, VISA_MASTER, 19, "17.99"),
    (CREDITO, AMEX, 19, "19.14"),
    (CREDITO, ELO, 19, "20.29"),
    (CREDITO, HIPER, 19, "20.29"),
    (CREDITO, VISA_MASTER, 20, "18.99"),
    (CREDITO, AMEX, 20, "20.14"),
    (CREDITO, ELO, 20, "21.29"),
    (CREDITO, HIPER, 20, "21.29"),
    (CREDITO, VISA_MASTER, 21, "19.99"),
    (CREDITO, AMEX, 21, "21.14"),
    (CREDITO, ELO, 21, "22.29"),
    (CREDITO, HIPER, 21, "22.29"),
    (PIX, VISA_MASTER, 1, "1.29"),
]


class Command(BaseCommand):
    help = "Popula TaxaCartao com a tabela oficial Intelbras de acréscimo ao portador."

    def handle(self, *args, **options):
        criadas = 0
        atualizadas = 0
        for forma, bandeira, parcelas, percentual in TAXAS:
            _, criada = TaxaCartao.objects.update_or_create(
                forma=forma,
                bandeira=bandeira,
                parcelas=parcelas,
                defaults={"percentual": Decimal(percentual)},
            )
            if criada:
                criadas += 1
            else:
                atualizadas += 1
        self.stdout.write(
            self.style.SUCCESS(f"TaxaCartao: {criadas} criadas, {atualizadas} atualizadas (total {len(TAXAS)}).")
        )
