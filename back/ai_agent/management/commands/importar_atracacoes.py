"""
Importa atracações do arquivo atracacoes.xlsx para a tabela atracacoes.

Uso:
    python manage.py importar_atracacoes
    python manage.py importar_atracacoes --file /caminho/para/atracacoes.xlsx
    python manage.py importar_atracacoes --dry-run
    python manage.py importar_atracacoes --batch-size 500
"""

import logging
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("ai_agent")

# Colunas obrigatórias que devem existir no Excel
REQUIRED_COLUMNS = {"OPERACAOMODALID"}

# Mapeamento: coluna do Excel → campo do model
COLUMN_MAP = {
    "OPERACAOMODALID":       "operacaomodalid",
    "NUMEROATRACACAO":       "numero_atracacao",
    "STATUS":                "status",
    "BERCO":                 "berco",
    "NAVIO":                 "navio",
    "IMO":                   "imo",
    "COMPRIMENTO":           "comprimento",
    "LARGURA":               "largura",
    "DWT":                   "dwt",
    "DUV":                   "duv",
    "ESCALA":                "escala",
    "BORDO":                 "bordo",
    "CALADOENTRADA":         "calado_entrada",
    "CALADASAIDA":           "calado_saida",
    "NAVEGACAO":             "navegacao",
    "AGENCIA":               "agencia",
    "PROCEDENCIA":           "procedencia",
    "DESTINO":               "destino",
    "BANDEIRA":              "bandeira",
    "ETA":                   "eta",
    "ETB":                   "etb",
    "NOR":                   "nor",
    "PRONTIDAO":             "prontidao",
    "ATRACACAO":             "atracacao",
    "INICIO":                "inicio_operacao",
    "TERMINO":               "termino_operacao",
    "DESATRACACAO":          "desatracacao",
    "ETS":                   "ets",
    "ENTREMANOBRA":          "entremanobra",
    "IS_IMPRODUTIVIDADE":    "is_improdutividade",
    "HORAS_PLANEJADAS":      "horas_planejadas",
    "PRANCHA":               "prancha",
    "EXCLUDENTE_EMAP":       "excludente_emap",
    "EXCLUDENTE_INTEMPERIE": "excludente_intemperie",
    "EXCL_EMAP_LM":          "excl_emap_lm",
    "EXCL_INTEMPERIE_LM":    "excl_intemperie_lm",
    "PROX_ATRACACAO":        "prox_atracacao",
}

DATETIME_FIELDS = {
    "eta", "etb", "nor", "prontidao", "atracacao",
    "inicio_operacao", "termino_operacao", "desatracacao",
    "ets", "entremanobra", "prox_atracacao",
}

DECIMAL_FIELDS = {
    "comprimento", "largura", "dwt",
    "calado_entrada", "calado_saida",
    "horas_planejadas", "prancha",
    "excludente_emap", "excludente_intemperie",
    "excl_emap_lm", "excl_intemperie_lm",
}

INTEGER_FIELDS = {"operacaomodalid", "numero_atracacao"}

BOOLEAN_FIELDS = {"is_improdutividade"}

# Formatos de data que o parser vai tentar, em ordem de precedência
DATETIME_FORMATS = [
    "%d/%m/%y %H:%M:%S",   # '30/12/18 08:55:00'
    "%d/%m/%Y %H:%M:%S",   # '30/12/2018 08:55:00'
    "%Y-%m-%d %H:%M:%S",   # '2018-12-30 08:55:00'
    "%Y-%m-%dT%H:%M:%S",   # '2018-12-30T08:55:00'
    "%d/%m/%y %H:%M",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
]


def _parse_datetime(value):
    """Converte valor do Excel para datetime timezone-aware; None em falha."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            return value
        return value.replace(tzinfo=dt_timezone.utc)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    # Remove nanosegundos: '30/12/18 08:55:00,000000000' → '30/12/18 08:55:00'
    if "," in value:
        value = value.split(",")[0].strip()
    for fmt in DATETIME_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=dt_timezone.utc)
        except ValueError:
            continue
    return None


def _parse_decimal(value):
    """Converte valor do Excel para Decimal; None em falha ou vazio."""
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


def _parse_integer(value):
    """Converte valor do Excel para int; None em falha ou vazio."""
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


def _parse_boolean(value):
    """Converte 0/1/True/False/'sim'/'não' para bool; None para vazio ou desconhecido."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        val = value.strip().lower()
        if not val:
            return None
        if val in ("1", "sim", "true", "s", "yes"):
            return True
        if val in ("0", "não", "nao", "false", "n", "no"):
            return False
    return None


def _parse_string(value):
    """Normaliza texto; None para vazios."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _build_field_value(field_name, raw_value):
    """Converte o valor bruto do Excel para o tipo correto do campo."""
    if field_name in DATETIME_FIELDS:
        return _parse_datetime(raw_value)
    if field_name in DECIMAL_FIELDS:
        return _parse_decimal(raw_value)
    if field_name in INTEGER_FIELDS:
        return _parse_integer(raw_value)
    if field_name in BOOLEAN_FIELDS:
        return _parse_boolean(raw_value)
    return _parse_string(raw_value)


class Command(BaseCommand):
    help = "Importa atracações do arquivo atracacoes.xlsx para a tabela atracacoes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Caminho para o arquivo .xlsx (padrão: <raiz_do_projeto>/atracacoes.xlsx)",
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

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "Dependência 'openpyxl' não encontrada. "
                "Execute: pip install openpyxl"
            )

        from ai_agent.models import Atracacao

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        xlsx_path = self._resolve_file_path(options["file"])

        self.stdout.write(f"Arquivo: {xlsx_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN — nenhuma alteração será salva."))

        # --- Leitura do Excel ---
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
        self.stdout.write(f"Registros lidos no Excel: {total_lidos}")

        # --- Validação de colunas obrigatórias ---
        missing = REQUIRED_COLUMNS - set(headers)
        if missing:
            raise CommandError(
                f"Colunas obrigatórias ausentes no arquivo: {', '.join(sorted(missing))}\n"
                f"Colunas encontradas: {', '.join(h for h in headers if h)}"
            )

        # Identifica índices das colunas mapeadas que existem no Excel
        col_indices = {}
        for xlsx_col, model_field in COLUMN_MAP.items():
            try:
                col_indices[model_field] = headers.index(xlsx_col)
            except ValueError:
                pass  # colunas opcionais ausentes são simplesmente ignoradas

        present_model_fields = list(col_indices.keys())
        self.stdout.write(f"Colunas mapeadas: {len(present_model_fields)}/{len(COLUMN_MAP)}")

        # --- Carrega IDs existentes ---
        existing_ids = set(
            Atracacao.objects.values_list("operacaomodalid", flat=True)
        )

        criados_list = []
        atualizados_list = []
        ignorados = 0

        for row_num, row in enumerate(data_rows, start=2):
            try:
                fields = self._parse_row(row, col_indices)
            except Exception as exc:
                ignorados += 1
                logger.warning("Linha %d ignorada por erro de parsing: %s", row_num, exc)
                continue

            operacaomodalid = fields.get("operacaomodalid")
            if operacaomodalid is None:
                ignorados += 1
                logger.warning("Linha %d ignorada: OPERACAOMODALID vazio.", row_num)
                continue

            if operacaomodalid in existing_ids:
                atualizados_list.append((operacaomodalid, fields))
            else:
                criados_list.append(Atracacao(**fields))
                existing_ids.add(operacaomodalid)

            if row_num % 1000 == 0:
                self.stdout.write(f"  ... processadas {row_num - 1} linhas")

        if not dry_run:
            criados, atualizados, ignorados_batch = self._persist(
                criados_list, atualizados_list, batch_size, Atracacao, present_model_fields
            )
            ignorados += ignorados_batch
        else:
            criados = len(criados_list)
            atualizados = len(atualizados_list)

        self._print_summary(total_lidos, criados, atualizados, ignorados, dry_run)

    # ------------------------------------------------------------------

    def _resolve_file_path(self, file_arg):
        if file_arg:
            path = Path(file_arg)
            if not path.exists():
                raise CommandError(f"Arquivo não encontrado: {path}")
            return path

        # Sobe a partir do arquivo do comando até encontrar a raiz do projeto
        base = Path(__file__).resolve()
        for parent in base.parents:
            candidate = parent / "atracacoes.xlsx"
            if candidate.exists():
                return candidate
            if (parent / "manage.py").exists():
                # Raiz do projeto fica um nível acima do back/
                candidate = parent.parent / "atracacoes.xlsx"
                if candidate.exists():
                    return candidate
                break

        raise CommandError(
            "Arquivo 'atracacoes.xlsx' não encontrado na raiz do projeto. "
            "Use --file para indicar o caminho."
        )

    def _parse_row(self, row, col_indices):
        """Converte uma linha do Excel para dicionário de campos do model."""
        fields = {}
        for field_name, col_idx in col_indices.items():
            raw = row[col_idx] if col_idx < len(row) else None
            fields[field_name] = _build_field_value(field_name, raw)
        return fields

    def _persist(self, to_create, to_update, batch_size, Model, present_model_fields):
        criados = 0
        atualizados = 0
        ignorados = 0

        # Apenas campos presentes no Excel (exclui a chave única e campos de auditoria)
        update_fields = [f for f in present_model_fields if f != "operacaomodalid"]
        update_fields.append("updated_at")

        # --- Criação em lote ---
        for i in range(0, len(to_create), batch_size):
            batch = to_create[i : i + batch_size]
            try:
                with transaction.atomic():
                    Model.objects.bulk_create(batch, ignore_conflicts=False)
                criados += len(batch)
            except Exception:
                # Fallback: insere um a um para isolar o registro problemático
                for obj in batch:
                    try:
                        with transaction.atomic():
                            obj.save()
                        criados += 1
                    except Exception as row_exc:
                        ignorados += 1
                        logger.error(
                            "Erro ao criar operacaomodalid=%s: %s",
                            getattr(obj, "operacaomodalid", "?"),
                            row_exc,
                        )

        # --- Atualização em lote ---
        if not to_update:
            return criados, atualizados, ignorados

        # Mapeia operacaomodalid → pk (id) para montar os objetos de update
        pk_lookup = dict(
            Model.objects.filter(
                operacaomodalid__in=[omid for omid, _ in to_update]
            ).values_list("operacaomodalid", "id")
        )

        now = timezone.now()
        update_objects = []
        for operacaomodalid, fields in to_update:
            real_pk = pk_lookup.get(operacaomodalid)
            if real_pk is None:
                ignorados += 1
                continue
            obj = Model(id=real_pk, **fields)
            obj.updated_at = now   # bulk_update não aciona auto_now
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
                            update_data = {
                                f: getattr(obj, f)
                                for f in update_fields
                                if f != "updated_at"
                            }
                            update_data["updated_at"] = now
                            Model.objects.filter(id=obj.id).update(**update_data)
                        atualizados += 1
                    except Exception as row_exc:
                        ignorados += 1
                        logger.error(
                            "Erro ao atualizar id=%s: %s",
                            obj.id,
                            row_exc,
                        )

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
            "%sImportação: lidos=%d criados=%d atualizados=%d ignorados=%d",
            prefix,
            total,
            criados,
            atualizados,
            ignorados,
        )
