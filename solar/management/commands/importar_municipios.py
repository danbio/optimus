"""Importa os municípios de uma UF do IBGE, com coordenadas.

Uso:
    python manage.py importar_municipios --uf TO
    python manage.py importar_municipios --uf TO GO MT

São só duas requisições por UF (lista + malha completa do estado), então é
rápido. O HSP vem depois, com `sincronizar_hsp`.
"""

from django.core.management.base import BaseCommand, CommandError

from solar.geo import ErroGeo, centroides, listar_municipios
from solar.models import Municipio


class Command(BaseCommand):
    help = "Importa municípios e coordenadas do IBGE (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--uf", nargs="+", required=True, help="Uma ou mais UFs. Ex.: --uf TO GO")

    def handle(self, *args, **opcoes):
        total_criados = total_atualizados = 0

        for uf in [u.upper() for u in opcoes["uf"]]:
            try:
                municipios = listar_municipios(uf)
                coordenadas = centroides(uf)
            except ErroGeo as erro:
                raise CommandError(str(erro)) from erro

            criados = atualizados = 0
            for item in municipios:
                latitude, longitude = coordenadas.get(item["codigo_ibge"], (None, None))
                _, foi_criado = Municipio.objects.update_or_create(
                    codigo_ibge=item["codigo_ibge"],
                    defaults={
                        "nome": item["nome"],
                        "uf": uf,
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                )
                criados += foi_criado
                atualizados += not foi_criado

            sem_coordenada = sum(1 for m in municipios if m["codigo_ibge"] not in coordenadas)
            aviso = f" ({sem_coordenada} sem coordenada)" if sem_coordenada else ""
            self.stdout.write(f"  {uf}: {criados} criados, {atualizados} atualizados{aviso}")
            total_criados += criados
            total_atualizados += atualizados

        self.stdout.write(
            self.style.SUCCESS(
                f"Municípios: {total_criados} criados, {total_atualizados} atualizados "
                f"(total {Municipio.objects.count()})."
            )
        )
