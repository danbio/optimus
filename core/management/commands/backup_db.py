"""Gera um backup do banco em JSON comprimido.

Funciona igual em SQLite (dev) e PostgreSQL (produção), porque usa o `dumpdata`
do próprio Django em vez de ferramenta específica do banco — o mesmo arquivo
serve para restaurar em qualquer um dos dois.

    python manage.py backup_db                # grava em backups/
    python manage.py backup_db --destino /bkp # outro diretório
    python manage.py backup_db --manter 7     # apaga os mais antigos, mantém 7

Restaurar:

    python manage.py loaddata backups/optimus_2026-08-09_1425.json.gz

Atenção: `loaddata` **soma** ao que já existe, não zera o banco antes. Para uma
restauração limpa, começar de um banco vazio (migrate em base nova).
"""

import gzip
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

# Excluídos por serem recriados pelo `migrate` — incluí-los causa conflito de
# chave ao restaurar.
EXCLUIR = ["contenttypes", "auth.permission", "sessions.session", "admin.logentry"]


class Command(BaseCommand):
    help = "Gera backup do banco em JSON comprimido (funciona em SQLite e PostgreSQL)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--destino",
            default=str(Path(settings.BASE_DIR) / "backups"),
            help="Diretório onde gravar (padrão: backups/ na raiz do projeto).",
        )
        parser.add_argument(
            "--manter",
            type=int,
            default=0,
            help="Quantos backups manter. 0 (padrão) não apaga nada.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        destino = Path(options["destino"])
        destino.mkdir(parents=True, exist_ok=True)

        nome = f"optimus_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json.gz"
        arquivo = destino / nome

        # Serializa em memória e grava com UTF-8 explícito, em vez de usar
        # `dumpdata --output`. No Windows aquele caminho grava na codificação do
        # console (cp1252) e ABORTA no meio ao encontrar caractere fora dela —
        # deixando um arquivo truncado que parece um backup válido.
        buffer = io.StringIO()
        call_command(
            "dumpdata",
            exclude=EXCLUIR,
            natural_foreign=True,
            natural_primary=True,
            stdout=buffer,
            verbosity=0,
        )
        conteudo = buffer.getvalue()

        with gzip.open(arquivo, "wt", encoding="utf-8") as destino_gz:
            destino_gz.write(conteudo)

        registros = self._validar(arquivo)

        tamanho_kb = arquivo.stat().st_size / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Backup gravado: {arquivo} ({tamanho_kb:.1f} KB, {registros} registros)"
            )
        )

        manter = options["manter"]
        if manter > 0:
            self._remover_antigos(destino, manter)

    def _validar(self, arquivo: Path) -> int:
        """Relê o arquivo gravado e confirma que é um JSON completo.

        Backup que falha em silêncio é pior que backup nenhum: sem esta
        conferência, um dump interrompido no meio passa por bom até o dia em
        que for preciso restaurar.
        """
        try:
            with gzip.open(arquivo, "rt", encoding="utf-8") as f:
                dados = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
            arquivo.unlink(missing_ok=True)
            raise CommandError(f"Backup inválido, arquivo descartado: {erro}") from erro

        if not isinstance(dados, list) or not dados:
            arquivo.unlink(missing_ok=True)
            raise CommandError("Backup inválido (vazio ou fora do formato), arquivo descartado.")

        return len(dados)

    def _remover_antigos(self, destino: Path, manter: int) -> None:
        backups = sorted(
            destino.glob("optimus_*.json.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for antigo in backups[manter:]:
            antigo.unlink()
            self.stdout.write(f"  removido (rotação): {antigo.name}")
