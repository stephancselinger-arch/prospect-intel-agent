"""LLM client interface and implementations.

Two implementations are provided:

- ``MockLLMClient``: deterministic, dependency-free. Used in tests and as the
  default when ``ANTHROPIC_API_KEY`` is not set. Lets the demo and evals run end
  to end without burning credits.
- ``ClaudeLLMClient``: wraps the ``anthropic`` SDK. Uses prompt caching on the
  system prompt and seller_context block (which are stable across many drafts
  for a single user), so per-prospect calls only pay for the variable enrichment
  payload. Tool use is modeled via structured JSON output rather than the SDK's
  tool API so we can swap backends without changing call sites.
"""

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


SIGNAL_EXTRACTION_SYSTEM = """You analyze company source documents and extract \
buying signals. For each signal you emit, you MUST cite the source document \
indices that support it. Never invent facts not present in the documents.

Respond ONLY with a JSON object matching this schema:
{
  "summary": "2-3 sentences",
  "signals": [
    {
      "signal_type": "hiring|funding|leadership_change|product_launch|expansion|tech_stack|compliance|partnership|earnings|other",
      "claim": "one sentence",
      "confidence": 0.0-1.0,
      "citation_indices": [0, 1]
    }
  ]
}
"""

OUTREACH_DRAFT_SYSTEM = """You are a senior B2B account executive drafting a \
cold outbound email. Rules:
- Maximum 110 words in the body.
- Open with a specific reference to a signal from the prospect's enriched data.
- One concrete value hypothesis. No fluff, no "I hope this email finds you well".
- One specific ask (15-min call this week, intro to the right person, etc.).
- Cite signals by their integer index in square brackets, e.g. [0], so the UI \
  can highlight which evidence the line is grounded in. Cite at least one.

Respond ONLY with a JSON object:
{
  "subject": "string under 60 chars",
  "body": "string",
  "cited_signal_indices": [0]
}
"""


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0


class LLMClient(ABC):
    """Minimal interface so callers don't depend on a specific SDK."""

    backend_name: str

    @abstractmethod
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        cacheable_prefix: Optional[str] = None,
    ) -> LLMResponse:
        """Return a response whose ``text`` is a JSON string.

        ``cacheable_prefix`` is content that is stable across many calls and
        should be marked for prompt caching by implementations that support it.
        """


class MockLLMClient(LLMClient):
    """Deterministic stub. Produces plausible signals + outreach without an API call.

    The mock is not "random fake data" — it parses the user payload (which is
    a JSON dump of the enrichment data) and writes outputs that are actually
    grounded in it. This means evals against the mock measure the *pipeline*,
    not the model.
    """

    backend_name = "mock"

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        cacheable_prefix: Optional[str] = None,
    ) -> LLMResponse:
        payload = _safe_json(user)
        if system is SIGNAL_EXTRACTION_SYSTEM or "extract buying signals" in system.lower():
            text = json.dumps(self._extract_signals(payload))
        else:
            text = json.dumps(self._draft_outreach(payload))
        # Pretend the cacheable_prefix produced cache hits, for a more realistic eval.
        cached = len((cacheable_prefix or "")) // 4
        return LLMResponse(
            text=text,
            input_tokens=len(user) // 4,
            output_tokens=len(text) // 4,
            cached_input_tokens=cached,
        )

    @staticmethod
    def _extract_signals(payload: dict) -> dict:
        sources = payload.get("sources", [])
        signals = []
        for i, src in enumerate(sources):
            excerpt = (src.get("excerpt") or "").lower()
            title = src.get("title") or ""
            stype = src.get("source_type", "")
            # Check specific signals (funding, leadership, launch, expansion)
            # before the generic "hiring" keyword — a Series-C announcement
            # often mentions hiring as a *use of funds* and would otherwise
            # mis-classify.
            if "series " in excerpt or "raised $" in excerpt or "funding round" in excerpt:
                signals.append({
                    "signal_type": "funding",
                    "claim": f"Funding event referenced in: {title}",
                    "confidence": 0.82,
                    "citation_indices": [i],
                })
            elif (
                "appointed" in excerpt
                or "joins as" in excerpt
                or "named cio" in excerpt
                or "named ciso" in excerpt
                or "named cto" in excerpt
                or "as chief revenue officer" in excerpt
                or "as chief technology officer" in excerpt
            ):
                signals.append({
                    "signal_type": "leadership_change",
                    "claim": f"Leadership change referenced in: {title}",
                    "confidence": 0.84,
                    "citation_indices": [i],
                })
            elif "launches" in excerpt or "introducing" in excerpt:
                signals.append({
                    "signal_type": "product_launch",
                    "claim": f"Product launch referenced in: {title}",
                    "confidence": 0.74,
                    "citation_indices": [i],
                })
            elif "opens office" in excerpt or "new market" in excerpt or "expanding to" in excerpt or "european expansion" in excerpt:
                signals.append({
                    "signal_type": "expansion",
                    "claim": f"Expansion referenced in: {title}",
                    "confidence": 0.7,
                    "citation_indices": [i],
                })
            elif stype == "job_posting" or "we're hiring" in excerpt:
                signals.append({
                    "signal_type": "hiring",
                    "claim": f"Hiring signal in: {title}",
                    "confidence": 0.78,
                    "citation_indices": [i],
                })
        company = payload.get("company") or {}
        domain = company.get("domain", "unknown")
        return {
            "summary": (
                f"{company.get('name') or domain} — {len(sources)} public signals "
                f"reviewed; {len(signals)} actionable items extracted."
            ),
            "signals": signals,
        }

    @staticmethod
    def _draft_outreach(payload: dict) -> dict:
        prospect = payload.get("prospect") or {}
        signals = prospect.get("signals") or []
        seller = payload.get("seller_context") or "our platform"
        tone = payload.get("tone", "consultative")

        if not signals:
            return {
                "subject": "Quick thought on your stack",
                "body": (
                    f"Wanted to flag something we've seen play out for peers in your "
                    f"category. Worth a 15-min look this week? "
                    f"(Pitching {seller[:60]}.)"
                ),
                "cited_signal_indices": [],
            }
        top = signals[0]
        company_name = (prospect.get("company") or {}).get("name") or "your team"
        subject_map = {
            "consultative": f"Re: {top.get('claim','')[:40]}",
            "direct": f"{company_name} + a 15-min ask",
            "executive": f"One observation on {company_name}",
        }
        body = (
            f"Noticed [0]: {top.get('claim','')}. Teams hitting that inflection "
            f"usually run into one specific bottleneck — happy to share the "
            f"three patterns we see most often. "
            f"Open to a 15-min look this week? ({seller[:80]})"
        )
        return {
            "subject": subject_map.get(tone, subject_map["consultative"])[:60],
            "body": body,
            "cited_signal_indices": [0],
        }


class ClaudeLLMClient(LLMClient):
    """Thin wrapper around the Anthropic SDK with prompt caching.

    System prompt and seller context are sent as cache_control'd blocks so
    repeated drafts for the same seller mostly hit cache. Output is constrained
    to JSON via the system prompt instructions (we deliberately avoid the SDK's
    tools API here to keep the interface backend-agnostic).
    """

    backend_name = "claude"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        # Imported lazily so MockLLMClient users don't need anthropic installed at runtime.
        from anthropic import Anthropic  # type: ignore

        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        cacheable_prefix: Optional[str] = None,
    ) -> LLMResponse:
        system_blocks: List[dict] = [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }]
        if cacheable_prefix:
            system_blocks.append({
                "type": "text",
                "text": cacheable_prefix,
                "cache_control": {"type": "ephemeral"},
            })

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_blocks,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=_extract_json(text),
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            cached_input_tokens=(
                getattr(usage, "cache_read_input_tokens", 0) if usage else 0
            ),
        )


def get_default_client() -> LLMClient:
    """Pick a backend based on env. ``LLM_BACKEND`` overrides auto-detection."""
    backend = os.getenv("LLM_BACKEND", "auto").lower()
    if backend == "mock":
        return MockLLMClient()
    if backend == "claude":
        return ClaudeLLMClient()
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return ClaudeLLMClient()
        except Exception:
            return MockLLMClient()
    return MockLLMClient()


def _safe_json(s: str) -> dict:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {}


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> str:
    """Defensive: Claude usually returns clean JSON, but strip fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n", "", text)
        text = re.sub(r"\n```$", "", text)
    match = _JSON_OBJECT_RE.search(text)
    return match.group(0) if match else text
