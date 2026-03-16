import sqlite3
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from estoque.models import Produto


class Command(BaseCommand):
    help = "Importa produtos do banco de dados legado (produtos.db)"

    def handle(self, *args, **options):
        db_path = settings.BASE_DIR / "produtos.db"

        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado: {db_path}"))
            return

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM produtos")
        rows = cur.fetchall()
        conn.close()

        total = len(rows)
        self.stdout.write(f"Processando {total} produtos do banco legado...")

        criados = atualizados = erros = 0

        for row in rows:
            try:
                ean = str(row["ean"] or "").strip()
                if ean in ("-", "N/A", "n/a"):
                    ean = ""

                _, created = Produto.objects.update_or_create(
                    codigo=int(row["codigo"]),
                    defaults={
                        "bu": str(row["bu"] or "").strip(),
                        "segmento": str(row["segmento"] or "").strip(),
                        "familia": str(row["familia"] or "").strip(),
                        "descricao": str(row["descricao"] or "").strip(),
                        "ipi": Decimal(str(row["ipi"] or 0)).quantize(Decimal("0.01")),
                        "icms": Decimal(str(row["icms"] or 0)).quantize(Decimal("0.01")),
                        "psd": Decimal(str(row["psd"] or 0)).quantize(Decimal("0.01")),
                        "pscf": Decimal(str(row["pscf"] or 0)).quantize(Decimal("0.01")),
                        "preco_referencia": str(row["preco_referencia"] or "").strip(),
                        "qtd_multipla": Decimal(str(row["qtd_multipla"] or 1)).quantize(Decimal("0.01")),
                        "ncm": str(row["ncm"] or "").strip(),
                        "ean": ean,
                        "observacoes": str(row["observacoes"] or "").strip(),
                    },
                )
                if created:
                    criados += 1
                else:
                    atualizados += 1
            except Exception as e:
                erros += 1
                self.stderr.write(f"  Erro no código {row['codigo']}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Concluído: {criados} produto(s) criado(s), {atualizados} atualizado(s), {erros} erro(s)."))
