"""
gemini_service.py — Shim de compatibilidade.

Redireciona para llm_service.py.
Mantido para não quebrar imports existentes em tools que ainda referenciam este módulo.
"""
from ai_agent.services.llm_service import get_llm, invoke_llm  # noqa: F401
