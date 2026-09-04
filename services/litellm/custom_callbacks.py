"""LiteLLM request policies for locally served models.

The policy is intentionally narrow: it normalizes public thinking controls into
 the qwen3/Froggeric chat-template contract before LiteLLM forwards the request
to llama-swap/vLLM. Other models pass through unchanged.

Scope comes from the request payload. Chat Completions requests carry
``messages``. Responses API requests carry ``input`` and use the ``aresponses``
hook type because embedding requests also carry ``input``.

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
        "qwen3.8-27b-bf16",
        "qwen3.8-27b-fp8",
        "qwen3.8-27b-nvfp4",
        "qwen3.8-27b-nvfp4-bf16-lmhead",
        "thinkingcap-qwen3.6-27b",
        "ornith-1.5-35b-a3b",
        "ornith-1.5-35b-a3b-fp8",
        "ornith-1.5-35b-a3b-nvfp4",
        "ornith-1.5-9b-nvfp4",
    }
)

# Qwen3.8 exposes a three-tier effort vocabulary to clients. The other qwen
# models retain their public effort values, including Ornith's distinct high
# tier.
QWEN38_MODELS: Final[frozenset[str]] = frozenset(
    {
        "qwen3.8-27b-bf16",
        "qwen3.8-27b-fp8",
        "qwen3.8-27b-nvfp4",
        "qwen3.8-27b-nvfp4-bf16-lmhead",
    }
)


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

def _reasoning_effort(data: dict[str, Any]) -> Any:
    effort = data.get("reasoning_effort")
    if effort is not None:
        return effort

    reasoning = data.get("reasoning")
    if isinstance(reasoning, dict):
        return reasoning.get("effort")

    return None


def _template_kwargs(
    data: dict[str, Any], *, is_responses: bool
) -> dict[str, Any] | None:
    container = data.get("extra_body") if is_responses else data
    if not isinstance(container, dict):
        return None

    kwargs = container.get("chat_template_kwargs")
    return kwargs if isinstance(kwargs, dict) else None


class QwenThinkingPolicy(CustomLogger):
    def _transform(
        self, data: dict[str, Any], call_type: Any
    ) -> dict[str, Any] | None:
        model = data.get("model")
        if not isinstance(model, str) or model not in QWEN_MODELS:
            return None

        is_chat = isinstance(data.get("messages"), list)
        is_responses = call_type == "aresponses" and "input" in data
        if not is_chat and not is_responses:
            return None

        effort_raw = _reasoning_effort(data)
        kwargs_in = _template_kwargs(data, is_responses=is_responses)
        explicit_data = dict(data)
        if kwargs_in is not None:
            explicit_data["chat_template_kwargs"] = kwargs_in
        explicit_enable = _explicit_enable_thinking(explicit_data)
        budget_present = data.get("thinking_token_budget") is not None

        no_controls = (
            effort_raw is None
            and explicit_enable is None
            and budget_present is False
            and (not isinstance(kwargs_in, dict) or "enable_thinking" not in kwargs_in)
        )
        if no_controls and not is_responses:
            return None

        kwargs = dict(kwargs_in) if isinstance(kwargs_in, dict) else {}
        changed = False
        if no_controls:
            kwargs["enable_thinking"] = False
            changed = True

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
                    if kwargs.get("reasoning_effort") != effort:
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

        if is_responses and effort_raw is not None:
            response_effort = (
                "none"
                if kwargs.get("enable_thinking") is False
                else kwargs.get("reasoning_effort")
            )
            reasoning = data.get("reasoning")
            if response_effort is not None and isinstance(reasoning, dict):
                if reasoning.get("effort") != response_effort:
                    data["reasoning"] = {**reasoning, "effort": response_effort}
                    changed = True
            elif response_effort is not None and "reasoning_effort" in data:
                if data["reasoning_effort"] != response_effort:
                    data["reasoning_effort"] = response_effort
                    changed = True

        if not changed:
            return None

        if is_responses:
            extra_body_in = data.get("extra_body")
            extra_body = dict(extra_body_in) if isinstance(extra_body_in, dict) else {}
            extra_body["chat_template_kwargs"] = kwargs
            data["extra_body"] = extra_body
        else:
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
            return self._transform(dict(data), call_type)
        except Exception:
            logger.exception(
                "qwen thinking policy failed; passing request through unchanged"
            )
            return None


qwen_thinking_policy = QwenThinkingPolicy()
