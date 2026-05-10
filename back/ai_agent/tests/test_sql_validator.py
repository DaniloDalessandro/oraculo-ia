"""
Testes do Validador SQL

Cobre os principais casos de segurança do sql_safety.py.
"""
from django.test import TestCase

from ai_agent.validators.sql_safety import validate_sql, extract_table_names


class SQLValidatorTest(TestCase):

    # ─── Casos VÁLIDOS ────────────────────────────────────────────────────

    def test_simple_select_valid(self):
        sql = "SELECT id, nome FROM clientes LIMIT 10"
        is_valid, error = validate_sql(sql)
        self.assertTrue(is_valid, error)

    def test_select_with_join_valid(self):
        sql = """
        SELECT a.id, b.nome
        FROM atracacoes a
        JOIN bercos b ON a.berco_id = b.id
        LIMIT 50
        """
        is_valid, error = validate_sql(sql)
        self.assertTrue(is_valid, error)

    def test_select_with_aggregation_valid(self):
        sql = """
        SELECT EXTRACT(YEAR FROM data_desatracacao) AS ano,
               COUNT(DISTINCT id) AS total
        FROM atracacoes
        GROUP BY 1
        ORDER BY 1
        """
        is_valid, error = validate_sql(sql)
        self.assertTrue(is_valid, error)

    def test_with_cte_valid(self):
        sql = """
        WITH totais AS (
            SELECT berco_id, SUM(tonelagem) AS total
            FROM atracacoes
            GROUP BY berco_id
        )
        SELECT b.nome, t.total
        FROM totais t
        JOIN bercos b ON t.berco_id = b.id
        ORDER BY t.total DESC
        LIMIT 10
        """
        is_valid, error = validate_sql(sql)
        self.assertTrue(is_valid, error)

    # ─── Casos INVÁLIDOS — Operações de escrita ───────────────────────────

    def test_insert_blocked(self):
        sql = "INSERT INTO navios (nome) VALUES ('Teste')"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)
        self.assertIn("INSERT", error.upper())

    def test_update_blocked(self):
        sql = "UPDATE navios SET nome = 'X' WHERE id = 1"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_delete_blocked(self):
        sql = "DELETE FROM navios WHERE id = 1"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_drop_blocked(self):
        sql = "DROP TABLE navios"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_alter_blocked(self):
        sql = "ALTER TABLE navios ADD COLUMN imo VARCHAR(20)"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_truncate_blocked(self):
        sql = "TRUNCATE TABLE navios"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_create_blocked(self):
        sql = "CREATE TABLE nova_tabela (id SERIAL PRIMARY KEY)"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_grant_blocked(self):
        sql = "GRANT ALL ON navios TO public"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    # ─── Casos INVÁLIDOS — Múltiplos statements ───────────────────────────

    def test_multiple_statements_blocked(self):
        sql = "SELECT 1; DROP TABLE navios"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    # ─── Casos INVÁLIDOS — Comentários ────────────────────────────────────

    def test_line_comment_blocked(self):
        sql = "SELECT id FROM navios -- comentario"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_block_comment_blocked(self):
        sql = "SELECT /* comentario */ id FROM navios"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    # ─── Casos INVÁLIDOS — Tabelas proibidas ──────────────────────────────

    def test_auth_user_blocked(self):
        sql = "SELECT * FROM auth_user"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_django_session_blocked(self):
        sql = "SELECT session_key FROM django_session"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    # ─── Casos INVÁLIDOS — Tabela inexistente ─────────────────────────────

    def test_unknown_table_blocked_with_known_tables(self):
        sql = "SELECT * FROM tabela_inexistente"
        known_tables = ["navios", "atracacoes", "bercos"]
        is_valid, error = validate_sql(sql, known_tables=known_tables)
        self.assertFalse(is_valid)
        self.assertIn("tabela_inexistente", error)

    def test_known_table_allowed_with_known_tables(self):
        sql = "SELECT id, nome FROM navios LIMIT 10"
        known_tables = ["navios", "atracacoes", "bercos"]
        is_valid, error = validate_sql(sql, known_tables=known_tables)
        self.assertTrue(is_valid, error)

    # ─── Funções perigosas ────────────────────────────────────────────────

    def test_pg_sleep_blocked(self):
        sql = "SELECT pg_sleep(10)"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    def test_pg_read_file_blocked(self):
        sql = "SELECT pg_read_file('/etc/passwd')"
        is_valid, error = validate_sql(sql)
        self.assertFalse(is_valid)

    # ─── extract_table_names ──────────────────────────────────────────────

    def test_extract_simple(self):
        sql = "SELECT id FROM navios"
        tables = extract_table_names(sql)
        self.assertIn("navios", tables)

    def test_extract_with_join(self):
        sql = "SELECT a.id, b.nome FROM atracacoes a JOIN bercos b ON a.berco_id = b.id"
        tables = extract_table_names(sql)
        self.assertIn("atracacoes", tables)
        self.assertIn("bercos", tables)

    def test_extract_empty_on_no_from(self):
        sql = "SELECT 1 + 1"
        tables = extract_table_names(sql)
        self.assertEqual(tables, [])
