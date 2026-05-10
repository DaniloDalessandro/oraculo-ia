"""
Semantic Search Service

Calcula similaridade textual entre perguntas usando difflib.
Sem dependências externas, sem GPU, sem API de embeddings.
"""
import re
from difflib import SequenceMatcher
from typing import List, Optional, Tuple


# Stopwords em português para normalização
_STOPWORDS = frozenset([
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "sobre", "entre", "que", "e", "ou",
    "foi", "ser", "está", "são", "qual", "quais", "quanto", "quantos",
    "me", "se", "me", "te", "lhe", "nos", "vos",
])


def _normalize(text: str) -> str:
    """Normaliza texto para comparação: lowercase, sem pontuação, sem stopwords."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t not in _STOPWORDS and len(t) > 1]
    return " ".join(tokens)


def text_similarity(a: str, b: str) -> float:
    """
    Retorna similaridade entre 0.0 e 1.0 entre duas strings.
    Combina SequenceMatcher com overlap de tokens para melhor precisão.
    """
    na = _normalize(a)
    nb = _normalize(b)

    if not na or not nb:
        return 0.0

    # Similaridade de sequência (leva em conta ordem)
    seq_score = SequenceMatcher(None, na, nb).ratio()

    # Overlap de tokens (não depende de ordem)
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if tokens_a or tokens_b:
        overlap = len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)
    else:
        overlap = 0.0

    # Média ponderada: sequência tem mais peso
    return round(0.6 * seq_score + 0.4 * overlap, 4)


def find_best_match(
    query: str,
    candidates: List[str],
    threshold: float = 0.72,
) -> Optional[Tuple[int, float]]:
    """
    Encontra o melhor candidato acima do threshold.

    Returns:
        (index, score) ou None se nenhum candidato passa o threshold.
    """
    if not candidates:
        return None

    best_idx, best_score = -1, 0.0
    for i, candidate in enumerate(candidates):
        score = text_similarity(query, candidate)
        if score > best_score:
            best_score = score
            best_idx = i

    if best_score >= threshold:
        return best_idx, best_score
    return None
