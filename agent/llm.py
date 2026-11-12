"""Criação do modelo de chat (Groq) com limitador de requisições compartilhado."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.rate_limiters import InMemoryRateLimiter

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"


@lru_cache(maxsize=1)
def _rate_limiter() -> InMemoryRateLimiter:
    # um único limitador para todos os agentes (mesma chave de API)
    rps = float(os.getenv("GROQ_RPS", "0.45"))  # ~27 req/min
    return InMemoryRateLimiter(requests_per_second=rps, check_every_n_seconds=0.05, max_bucket_size=3)


def make_llm(model: str | None = None, temperature: float = 0.2):
    from langchain_groq import ChatGroq

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Defina GROQ_API_KEY no arquivo .env (veja .env.example).")
    model = model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    extra = {}
    if "gpt-oss" in model:  # modelos de raciocínio: controla quanto "pensam" (tokens)
        extra["reasoning_effort"] = os.getenv("GROQ_REASONING_EFFORT", "low")
    return ChatGroq(model=model, temperature=temperature, max_retries=6, timeout=90,
                    rate_limiter=_rate_limiter(), **extra)
