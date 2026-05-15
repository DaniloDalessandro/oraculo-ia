"""
Importa mercadorias do arquivo mercadoria.xlsx para a tabela mercadorias.

Uso:
    python manage.py importar_mercadorias
    python manage.py importar_mercadorias --file /caminho/para/mercadoria.xlsx
    python manage.py importar_mercadorias --dry-run
    python manage.py importar_mercadorias --batch-size 500
    python manage.py importar_mercadorias --skip-atracacao-check
"""

import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("ai_agent")

# Colunas obrigatórias que devem existir no Excel
REQUIRED_COLUMNS = {"ID", "ATRACACAO_ID"}

# Mapeamento: coluna do Excel → campo do model
COLUMN_MAP = {
    "ID":              "mercadoria_id",
    "ATRACACAO_ID":    "atracacao_id",
    "NOME":            "nome",
    "GM":              "gm",
    "NATUREZATIPO":    "natureza_tipo",
    "NATUREZASUBTIPO": "natureza_subtipo",
    "OPERACAO":        "operacao",
    "SENTIDO":         "sentido",
    "OPERADOR":        "operador",
    "CLIENTE":         "cliente",
    "PBM":             "pbm",
    "PLR":             "plr",
    "QTDM":            "qtdm",
    "QTDR":            "qtdr",
}

INTEGER_FIELDS = {"mercadoria_id", "atracacao_id"}
DECIMAL_FIELDS = {"pbm", "plr", "qtdm", "qtdr"}
STRING_FIELDS = {"nome", "gm", "natureza_tipo", "natureza_subtipo", "operacao", "sentido", "operador", "cliente"}


# ─── Parsers ──────────────────────────────────────────────────────────────────

def _parse_integer(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _parse_decimal(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_string(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _build_field_value(field_name, raw_value):
    if field_name in INTEGER_FIELDS:
        return _parse_integer(raw_value)
    if field_name in DECIMAL_FIELDS:
        return _parse_decimal(raw_value)
    return _parse_string(raw_value)


# ─── Command ──────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Importa mercadorias do arquivo mercadoria.xlsx para a tabela mercadorias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Caminho para o arquivo .xlsx (padrão: <raiz_do_projeto>/mercadoria.xlsx)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a importação sem salvar no banco.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Tamanho do lote para bulk_create/update (padrão: 200).",
        )
        parser.add_argument(
            "--skip-atracacao-check",
            action="store_true",
            help="Não valida se o ATRACACAO_ID existe na tabela de atracações.",
        )

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "Dependência 'openpyxl' não encontrada. "
                "Execute: pip install openpyxl"
            )

        from ai_agent.models import Mercadoria, Atracacao

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        skip_atracacao_check = options["skip_atracacao_check"]

        xlsx_path = self._resolve_file_path(options["file"])
        self.stdout.write(f"Arquivo : {xlsx_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN — nenhuma alteração será salva."))

        # ── Leitura do Excel ──────────────────────────────────────────────────
        try:
            wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {xlsx_path}")
        except Exception as exc:
            raise CommandError(f"Erro ao abrir o arquivo: {exc}")

        ws = wb.active
        rows = list(ws.iter_rows(min_row=1, values_only=True))
        wb.close()

        if not rows:
            raise CommandError("O arquivo está vazio.")

        headers = [str(h).strip().upper() if h is not None else "" for h in rows[0]]
        data_rows = rows[1:]
        total_lidos = len(data_rows)
        self.stdout.write(f"Registros lidos no Excel : {total_lidos}")

        # ── Validação de colunas obrigatórias ─────────────────────────────────
        missing = REQUIRED_COLUMNS - set(headers)
        if missing:
            raise CommandError(
                f"Colunas obrigatórias ausentes no arquivo: {', '.join(sorted(missing))}\n"
                f"Colunas encontradas: {', '.join(h for h in headers if h)}"
            )

        # Mapeia coluna Excel → índice
        col_indices = {}
        for xlsx_col, model_field in COLUMN_MAP.items():
            try:
                col_indices[model_field] = headers.index(xlsx_col)
            except ValueError:
                pass  # colunas opcionais ausentes são ignoradas

        present_model_fields = list(col_indices.keys())
        self.stdout.write(f"Colunas mapeadas        : {len(present_model_fields)}/{len(COLUMN_MAP)}")

        # ── Carrega IDs existentes ────────────────────────────────────────────
        existing_ids = set(
            Mercadoria.objects.values_list("mercadoria_id", flat=True)
        )

        # ── Carrega IDs de atracações válidas (para validação) ────────────────
        atracacao_ids: set | None = None
        if not skip_atracacao_check:
            atracacao_ids = set(
                Atracacao.objects.values_list("operacaomodalid", flat=True)
            )
            self.stdout.write(f"Atracações no banco     : {len(atracacao_ids)}")

        # ── Processa linhas ───────────────────────────────────────────────────
        to_create = []
        to_update = []
        ignorados = 0
        atracacao_ausentes = 0

        for row_num, row in enumerate(data_rows, start=2):
            try:
                fields = self._parse_row(row, col_indices)
            except Exception as exc:
                ignorados += 1
                logger.warning("Linha %d ignorada (erro de parsing): %s", row_num, exc)
                continue

            mercadoria_id = fields.get("mercadoria_id")
            if mercadoria_id is None:
                ignorados += 1
                logger.warning("Linha %d ignorada: ID vazio.", row_num)
                continue

            atrac_id = fields.get("atracacao_id")
            if atracacao_ids is not None and atrac_id is not None:
                if atrac_id not in atracacao_ids:
                    atracacao_ausentes += 1
                    logger.debug(
                        "Linha %d: ATRACACAO_ID=%s não encontrada na tabela de atracações.",
                        row_num, atrac_id,
                    )

            if mercadoria_id in existing_ids:
                to_update.append((mercadoria_id, fields))
            else:
                to_create.append(Mercadoria(**fields))
                existing_ids.add(mercadoria_id)

            if row_num % 2000 == 0:
                self.stdout.write(f"  ... processadas {row_num - 1} linhas")

        if atracacao_ausentes:
            self.stdout.write(
                self.style.WARNING(
                    f"  Atenção: {atracacao_ausentes} linha(s) referenciam atracações "
                    "não encontradas no banco (serão importadas mesmo assim)."
                )
            )

        # ── Persiste ──────────────────────────────────────────────────────────
        if not dry_run:
            criados, atualizados, ignorados_batch = self._persist(
                to_create, to_update, batch_size, Mercadoria, present_model_fields
            )
            ignorados += ignorados_batch
        else:
            criados = len(to_create)
            atualizados = len(to_update)

        self._print_summary(total_lidos, criados, atualizados, ignorados, dry_run)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _resolve_file_path(self, file_arg):
        if file_arg:
            path = Path(file_arg)
            if not path.exists():
                raise CommandError(f"Arquivo não encontrado: {path}")
            return path

        base = Path(__file__).resolve()
        for parent in base.parents:
            candidate = parent / "mercadoria.xlsx"
            if candidate.exists():
                return candidate
            if (parent / "manage.py").exists():
                candidate = parent.parent / "mercadoria.xlsx"
                if candidate.exists():
                    return candidate
                break

        raise CommandError(
            "Arquivo 'mercadoria.xlsx' não encontrado na raiz do projeto. "
            "Use --file para indicar o caminho."
        )

    def _parse_row(self, row, col_indices):
        fields = {}
        for field_name, col_idx in col_indices.items():
            raw = row[col_idx] if col_idx < len(row) else None
            fields[field_name] = _build_field_value(field_name, raw)
        return fields

    def _persist(self, to_create, to_update, batch_size, Model, present_model_fields):
        criados = 0
        atualizados = 0
        ignorados = 0

        update_fields = [f for f in present_model_fields if f != "mercadoria_id"]
        update_fields.append("updated_at")

        # ── Criação em lote ───────────────────────────────────────────────────
        for i in range(0, len(to_create), batch_size):
            batch = to_create[i : i + batch_size]
            try:
                with transaction.atomic():
                    Model.objects.bulk_create(batch, ignore_conflicts=False)
                criados += len(batch)
            except Exception:
                for obj in batch:
                    try:
                        with transaction.atomic():
                            obj.save()
                        criados += 1
                    except Exception as exc:
                        ignorados += 1
                        logger.error(
                            "Erro ao criar mercadoria_id=%s: %s",
                            getattr(obj, "mercadoria_id", "?"),
                            exc,
                        )

        # ── Atualização em lote ───────────────────────────────────────────────
        if not to_update:
            return criados, atualizados, ignorados

        pk_lookup = dict(
            Model.objects.filter(
                mercadoria_id__in=[mid for mid, _ in to_update]
            ).values_list("mercadoria_id", "id")
        )

        now = timezone.now()
        update_objects = []
        for mercadoria_id, fields in to_update:
            real_pk = pk_lookup.get(mercadoria_id)
            if real_pk is None:
                ignorados += 1
                continue
            obj = Model(id=real_pk, **fields)
            obj.updated_at = now
            update_objects.append(obj)

        for i in range(0, len(update_objects), batch_size):
            batch = update_objects[i : i + batch_size]
            try:
                with transaction.atomic():
                    Model.objects.bulk_update(batch, update_fields)
                atualizados += len(batch)
            except Exception:
                for obj in batch:
                    try:
                        with transaction.atomic():
                            update_data = {f: getattr(obj, f) for f in update_fields if f != "updated_at"}
                            update_data["updated_at"] = now
                            Model.objects.filter(id=obj.id).update(**update_data)
                        atualizados += 1
                    except Exception as exc:
                        ignorados += 1
                        logger.error("Erro ao atualizar id=%s: %s", obj.id, exc)

        return criados, atualizados, ignorados

    def _print_summary(self, total, criados, atualizados, ignorados, dry_run):
        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS(f"{prefix}IMPORTAÇÃO CONCLUÍDA"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Registros lidos       : {total}")
        self.stdout.write(self.style.SUCCESS(f"  Registros criados     : {criados}"))
        self.stdout.write(self.style.WARNING(f"  Registros atualizados : {atualizados}"))
        if ignorados:
            self.stdout.write(self.style.ERROR(f"  Registros ignorados   : {ignorados}"))
        else:
            self.stdout.write(f"  Registros ignorados   : {ignorados}")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        logger.info(
            "%sImportação mercadorias: lidos=%d criados=%d atualizados=%d ignorados=%d",
            prefix, total, criados, atualizados, ignorados,
        )
