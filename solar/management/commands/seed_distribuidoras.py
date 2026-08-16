"""Cadastra as distribuidoras usadas nas propostas.

O CNPJ é o que importa: é a chave de consulta na API da ANEEL (a sigla
muda de grafia entre os arquivos anuais, o CNPJ não).

Começa pelas do entorno da Optimus (sul do Tocantins e estados vizinhos).
Para incluir outra, basta acrescentar aqui ou cadastrar pelo admin.
"""

from django.core.management.base import BaseCommand

from solar.models import Distribuidora

# (nome, sigla ANEEL, CNPJ só dígitos, UF)
DISTRIBUIDORAS = [
    ("Energisa Tocantins", "ETO", "25086034000171", "TO"),
    ("Equatorial Goiás", "EQTLGO", "01543032000104", "GO"),
    ("Equatorial Pará", "EQTLPA", "04895728000180", "PA"),
    ("Equatorial Maranhão", "EQTLMA", "06272793000184", "MA"),
    ("Energisa Mato Grosso", "EMT", "03467321000199", "MT"),
    ("Neoenergia Brasília", "NEOENERGIA BSB", "00070698000111", "DF"),
]


class Command(BaseCommand):
    help = "Cadastra as distribuidoras de energia (idempotente)."

    def handle(self, *args, **opcoes):
        criadas = atualizadas = 0
        for nome, sigla, cnpj, uf in DISTRIBUIDORAS:
            _, foi_criada = Distribuidora.objects.update_or_create(
                cnpj=cnpj,
                defaults={"nome": nome, "sigla": sigla, "uf": uf},
            )
            criadas += foi_criada
            atualizadas += not foi_criada

        self.stdout.write(
            self.style.SUCCESS(
                f"Distribuidoras: {criadas} criadas, {atualizadas} atualizadas "
                f"(total {Distribuidora.objects.count()})."
            )
        )
