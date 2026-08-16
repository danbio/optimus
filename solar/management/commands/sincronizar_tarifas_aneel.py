"""Espelha as tarifas homologadas da ANEEL para o banco local.

Uso:
    python manage.py sincronizar_tarifas_aneel              # ano atual
    python manage.py sincronizar_tarifas_aneel --ano 2026
    python manage.py sincronizar_tarifas_aneel --cnpj 25086034000171

Idempotente: rodar de novo atualiza no lugar em vez de duplicar. Vale
agendar uma vez por ano, depois do reajuste da distribuidora (a ANEEL
homologa em julho no caso da Energisa TO).
"""

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from solar.aneel import ErroANEEL, buscar_componentes, consolidar_tarifas, resource_id_do_ano
from solar.models import Distribuidora, TarifaDistribuidora


class Command(BaseCommand):
    help = "Sincroniza tarifas homologadas (TUSD, TE, Fio B) do portal de dados abertos da ANEEL."

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int, default=date.today().year, help="Ano do arquivo da ANEEL (padrão: atual).")
        parser.add_argument("--cnpj", help="Sincroniza só esta distribuidora. Padrão: todas as ativas.")
        parser.add_argument("--subgrupo", default="B1")
        parser.add_argument("--modalidade", default="Convencional")

    def handle(self, *args, **opcoes):
        ano = opcoes["ano"]
        distribuidoras = Distribuidora.objects.filter(ativo=True)
        if opcoes.get("cnpj"):
            distribuidoras = distribuidoras.filter(cnpj=opcoes["cnpj"])

        if not distribuidoras.exists():
            raise CommandError("Nenhuma distribuidora ativa encontrada. Rode `seed_distribuidoras` antes.")

        try:
            resource_id = resource_id_do_ano(ano)
        except ErroANEEL as erro:
            raise CommandError(str(erro)) from erro

        self.stdout.write(f"Arquivo da ANEEL de {ano}: {resource_id}")

        total_criadas = total_atualizadas = 0
        for distribuidora in distribuidoras:
            try:
                registros = buscar_componentes(
                    resource_id,
                    cnpj=distribuidora.cnpj,
                    subgrupo=opcoes["subgrupo"],
                    modalidade=opcoes["modalidade"],
                )
            except ErroANEEL as erro:
                # Uma distribuidora fora do ar não pode derrubar o resto.
                self.stderr.write(self.style.WARNING(f"{distribuidora.sigla}: {erro}"))
                continue

            tarifas = consolidar_tarifas(registros)
            if not tarifas:
                self.stderr.write(
                    self.style.WARNING(f"{distribuidora.sigla}: nenhuma tarifa em {ano} (a ANEEL pode não ter carregado esse ano)")
                )
                continue

            criadas = atualizadas = 0
            for linha in tarifas.values():
                _, foi_criada = TarifaDistribuidora.objects.update_or_create(
                    distribuidora=distribuidora,
                    subgrupo=linha["subgrupo"],
                    modalidade=linha["modalidade"],
                    subclasse=linha["subclasse"],
                    vigencia_inicio=_data(linha["vigencia_inicio"]),
                    defaults={
                        "vigencia_fim": _data(linha["vigencia_fim"]),
                        "vlr_tusd": linha["vlr_tusd"],
                        "vlr_te": linha["vlr_te"],
                        "vlr_tusd_fio_b": linha.get("vlr_tusd_fio_b", 0),
                        "sincronizado_em": timezone.now(),
                    },
                )
                criadas += foi_criada
                atualizadas += not foi_criada

            total_criadas += criadas
            total_atualizadas += atualizadas
            self.stdout.write(f"  {distribuidora.sigla}: {criadas} criadas, {atualizadas} atualizadas")

        self.stdout.write(
            self.style.SUCCESS(f"Tarifas ANEEL: {total_criadas} criadas, {total_atualizadas} atualizadas.")
        )


def _data(texto: str | None) -> date | None:
    if not texto:
        return None
    return datetime.strptime(texto[:10], "%Y-%m-%d").date()
