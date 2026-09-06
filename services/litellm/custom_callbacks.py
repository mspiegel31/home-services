"""LiteLLM request policies for locally served models.

The policy normalizes public thinking controls into the qwen3/Froggeric
chat-template contract before LiteLLM forwards Chat Completions requests to
llama-swap. It also removes unsupported OpenAI Responses compatibility hints
from NInfer requests. Other models and API shapes pass through unchanged.

Precedence for the qwen models:

1. an explicit boolean ``chat_template_kwargs.enable_thinking``
2. an explicit boolean top-level ``enable_thinking``
3. ``thinking_token_budget`` (zero disables thinking, otherwise enables it)
4. ``reasoning_effort``

When the resolved state is thinking-off, a stale top-level
``reasoning_effort`` is stripped so vLLM's effort-to-thinking auto-injection
has nothing to act on.

The Froggeric template defaults to medium thinking when none of those controls
is present, so this module deliberately does not invent a default.

NInfer implements reasoning effort and raw reasoning output, but intentionally
does not implement reasoning summaries or encrypted reasoning output. Responses
clients commonly request both, so those optional hints are removed only for the
NInfer route.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger(__name__)

QWEN_MODELS: Final[frozenset[str]] = frozenset(
    {
        # All models using vLLM's qwen3 reasoning parser share the
        # chat_template_kwargs compatibility contract.
        "qwen3.8-27b-fp8",
        "qwen3.8-27b-nvfp4-bf16-lmhead",
        "qwen3.8-27b-nvfp4-bf16-lmhead-sglang",
        "qwen3.8-27b-ninfer",
        "ornith-1.5-9b-nvfp4",
    }
)

# Qwen3.8 exposes a three-tier effort vocabulary to clients. The other qwen
# models retain their public effort values, including Ornith's distinct high
# tier.
QWEN38_MODELS: Final[frozenset[str]] = frozenset(
    {
        "qwen3.8-27b-fp8",
        "qwen3.8-27b-nvfp4-bf16-lmhead",
        "qwen3.8-27b-nvfp4-bf16-lmhead-sglang",
        "qwen3.8-27b-ninfer",
    }
)

NINFER_MODEL: Final[str] = "qwen3.8-27b-ninfer"
_NINFER_ENCRYPTED_REASONING_INCLUDE: Final[str] = "reasoning.encrypted_content"


_OFF_ALIASES: Final[frozenset[str]] = frozenset(
    {"off", "none", "disabled", "false", "0"}
)

_LOW_ALIASES: Final[frozenset[str]] = frozenset({"low", "minimal"})
_MEDIUM_ALIASES: Final[frozenset[str]] = frozenset({"medium", "moderate"})
_XHIGH_ALIASES: Final[frozenset[str]] = frozenset(
    {"high", "xhigh", "max", "maximum", "extra-high", "x-high"}
)


def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def _is_off_effort(value: Any) -> bool:
    return _normalize(value) in _OFF_ALIASES


def _canonical_effort(value: Any) -> str | None:
    """Map public effort vocabularies onto Froggeric's three tiers."""
    normalized = _normalize(value)

    if normalized in _LOW_ALIASES:
        return "low"
    if normalized in _MEDIUM_ALIASES:
        return "medium"
    if normalized in _XHIGH_ALIASES:
        return "xhigh"

    logger.warning(
        "qwen thinking policy: leaving unknown reasoning_effort %r untouched",
        value,
    )
    return None


def _explicit_enable_thinking(data: dict[str, Any]) -> bool | None:
    """Read a direct thinking toggle, with the kwargs layer as authoritative."""
    kwargs = data.get("chat_template_kwargs")
    if isinstance(kwargs, dict):
        value = kwargs.get("enable_thinking")
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)

    value = data.get("enable_thinking")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)

    return None


def _budget_disables_thinking(data: dict[str, Any]) -> bool:
    try:
        budget = float(data.get("thinking_token_budget"))
    except (TypeError, ValueError):
        return False
    return budget <= 0

def _transform_ninfer_responses(data: dict[str, Any]) -> dict[str, Any] | None:
    """Remove optional Responses features that NInfer cannot produce."""
    if "input" not in data:
        return None

    changed = False
    reasoning_in = data.get("reasoning")
    if isinstance(reasoning_in, dict) and reasoning_in.get("summary") is not None:
        reasoning = dict(reasoning_in)
        reasoning.pop("summary")
        if reasoning:
            data["reasoning"] = reasoning
        else:
            data.pop("reasoning")
        changed = True

    include_in = data.get("include")
    if (
        isinstance(include_in, list)
        and _NINFER_ENCRYPTED_REASONING_INCLUDE in include_in
    ):
        include = [
            value
            for value in include_in
            if value != _NINFER_ENCRYPTED_REASONING_INCLUDE
        ]
        if include:
            data["include"] = include
        else:
            data.pop("include")
        changed = True

    return data if changed else None


class QwenThinkingPolicy(CustomLogger):
    def _transform(self, data: dict[str, Any]) -> dict[str, Any] | None:
        model = data.get("model")
        if not isinstance(model, str) or model not in QWEN_MODELS:
            return None

        if model == NINFER_MODEL:
            responses_result = _transform_ninfer_responses(data)
            if responses_result is not None:
                return responses_result

        if not isinstance(data.get("messages"), list):
            return None

        effort_raw = data.get("reasoning_effort")
        kwargs_in = data.get("chat_template_kwargs")
        explicit_enable = _explicit_enable_thinking(data)
        budget_present = data.get("thinking_token_budget") is not None

        no_controls = (
            effort_raw is None
            and explicit_enable is None
            and budget_present is False
        )
        if no_controls:
            return None

        kwargs = dict(kwargs_in) if isinstance(kwargs_in, dict) else {}
        changed = False

        if explicit_enable is not None and "enable_thinking" not in kwargs:
            kwargs["enable_thinking"] = explicit_enable
            changed = True

        if effort_raw is not None and kwargs.get("enable_thinking") is not False:
            if _is_off_effort(effort_raw):
                if kwargs.get("enable_thinking") is not False:
                    kwargs["enable_thinking"] = False
                    changed = True
            else:
                effort = (
                    _canonical_effort(effort_raw)
                    if model in QWEN38_MODELS
                    else effort_raw
                )
                if effort is not None:
                    if kwargs.get("enable_thinking") is not True:
                        kwargs["enable_thinking"] = True
                        changed = True
                    if (
                        model != NINFER_MODEL
                        and kwargs.get("reasoning_effort") != effort
                    ):
                        kwargs["reasoning_effort"] = effort
                        changed = True

        if budget_present:
            if _budget_disables_thinking(data):
                if kwargs.get("enable_thinking") is not False:
                    kwargs["enable_thinking"] = False
                    changed = True
            elif kwargs.get("enable_thinking") is not True:
                kwargs["enable_thinking"] = True
                changed = True

        if kwargs.get("enable_thinking") is False and effort_raw is not None:
            if data.pop("reasoning_effort", None) is not None:
                changed = True
            if kwargs.pop("reasoning_effort", None) is not None:
                changed = True

        if not changed:
            return None

        data["chat_template_kwargs"] = kwargs
        return data

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict[str, Any],
        call_type: Any,
    ) -> dict[str, Any] | None:
        try:
            return self._transform(dict(data))
        except Exception:
            logger.exception(
                "qwen thinking policy failed; passing request through unchanged"
            )
            return None


qwen_thinking_policy = QwenThinkingPolicy()
