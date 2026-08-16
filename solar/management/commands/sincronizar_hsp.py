"""Busca a irradiação solar (HSP) dos municípios na NASA POWER.

Uso:
    python manage.py sincronizar_hsp --uf TO             # só os que faltam
    python manage.py sincronizar_hsp --uf TO --refazer   # todos de novo
    python manage.py sincronizar_hsp --municipio 1709500 # um só

Uma requisição por município, então uma UF inteira leva alguns minutos.
Por padrão pula quem já tem HSP: climatologia é média de longo prazo, não
muda de um ano para o outro.
"""

import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from solar.geo import ErroGeo, hsp_mensal
from solar.models import Municipio

# Respiro entre chamadas para não martelar a API pública da NASA.
INTERVALO_SEGUNDOS = 0.2


class Command(BaseCommand):
    help = "Sincroniza HSP mensal dos municípios via NASA POWER."

    def add_arguments(self, parser):
        parser.add_argument("--uf", nargs="+", help="Limita a estas UFs.")
        parser.add_argument("--municipio", type=int, help="Código IBGE de um município específico.")
        parser.add_argument("--refazer", action="store_true", help="Refaz mesmo quem já tem HSP.")
        parser.add_argument("--limite", type=int, help="Para depois de N municípios (útil para testar).")

    def handle(self, *args, **opcoes):
        alvos = Municipio.objects.filter(latitude__isnull=False, longitude__isnull=False)

        if opcoes.get("municipio"):
            alvos = alvos.filter(codigo_ibge=opcoes["municipio"])
        elif opcoes.get("uf"):
            alvos = alvos.filter(uf__in=[u.upper() for u in opcoes["uf"]])

        if not opcoes["refazer"]:
            alvos = alvos.filter(hsp_anual__isnull=True)

        alvos = alvos.order_by("uf", "nome")
        if opcoes.get("limite"):
            alvos = alvos[: opcoes["limite"]]

        total = alvos.count()
        if not total:
            self.stdout.write(self.style.WARNING("Nada a sincronizar. Rode `importar_municipios` antes, ou use --refazer."))
            return

        self.stdout.write(f"Sincronizando HSP de {total} município(s)...")

        sincronizados = falhas = 0
        for indice, municipio in enumerate(alvos, start=1):
            try:
                dados = hsp_mensal(municipio.latitude, municipio.longitude)
            except ErroGeo as erro:
                # Um município fora do ar não pode derrubar a UF inteira.
                self.stderr.write(self.style.WARNING(f"  {municipio}: {erro}"))
                falhas += 1
                continue

            municipio.hsp_mensal = {str(mes): str(valor) for mes, valor in dados["mensal"].items()}
            municipio.hsp_anual = dados["anual"]
            municipio.sincronizado_em = timezone.now()
            municipio.save(update_fields=["hsp_mensal", "hsp_anual", "sincronizado_em", "atualizado_em"])
            sincronizados += 1

            if indice % 25 == 0 or indice == total:
                self.stdout.write(f"  {indice}/{total}...")
            time.sleep(INTERVALO_SEGUNDOS)

        if falhas:
            self.stderr.write(self.style.WARNING(f"{falhas} município(s) falharam — rode de novo para tentar só eles."))
        if not sincronizados:
            raise CommandError("Nenhum município sincronizado.")

        self.stdout.write(self.style.SUCCESS(f"HSP sincronizado em {sincronizados} município(s)."))
