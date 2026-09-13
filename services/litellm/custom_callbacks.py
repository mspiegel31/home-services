"""LiteLLM request policies for local reasoning models.

The policy normalizes public thinking controls into each model's chat-template
contract before LiteLLM forwards Chat Completions requests to llama-swap. It
also removes unsupported OpenAI Responses compatibility hints from NInfer
requests. Other models and API shapes pass through unchanged.

Precedence for each managed model:

1. an explicit boolean ``chat_template_kwargs.enable_thinking``
2. an explicit boolean top-level ``enable_thinking``
3. ``thinking_token_budget`` (zero disables thinking, otherwise enables it)
4. ``reasoning_effort``

When the resolved state is thinking-off, a stale top-level
``reasoning_effort`` is stripped so vLLM's effort-to-thinking auto-injection
has nothing to act on.

The Froggeric template defaults to medium thinking when none of those controls
is present, so this module deliberately does not invent a default. Gemma 4,
Laguna XS 2.1, and Ornith receive ``enable_thinking`` but never an effort tier.

The Unsloth NVFP4 deployment loads its thinking-mode sampling defaults from
the checkpoint. Its Froggeric template defaults to medium effort, so requests
without a thinking control receive Unsloth's xhigh default explicitly.
Thinking-off requests receive Unsloth's differing non-thinking defaults only
for values the client omitted.

NInfer implements reasoning effort and raw reasoning output, but intentionally
does not implement reasoning summaries or encrypted reasoning output. Responses
clients commonly request both, so those optional hints are removed only for the
NInfer route.
"""


import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Final, Mapping

from litellm.integrations.custom_logger import CustomLogger

if TYPE_CHECKING:
    from litellm.caching.caching import DualCache
    from litellm.proxy._types import UserAPIKeyAuth
    from litellm.types.utils import CallTypesLiteral

logger = logging.getLogger(__name__)


class LocalReasoningModel(str, Enum):
    """Model IDs requiring local chat-template thinking controls."""

    GEMMA4_31B = "gemma-4-31b"
    QWEN38_FP8 = "qwen3.8-27b-fp8"
    QWEN38_UNSLOTH_NVFP4 = "qwen3.8-27b-nvfp4"
    QWEN38_NVFP4 = "qwen3.8-27b-nvfp4-bf16-lmhead"
    QWEN38_NVFP4_SGLANG = "qwen3.8-27b-nvfp4-bf16-lmhead-sglang"
    QWEN38_NINFER = "qwen3.8-27b-ninfer"
    QWEN38_QUASAR_NVFP4 = "qwen3.8-27b-quasar-nvfp4"
    ORNITH = "ornith-1.5-9b-nvfp4"
    ORNITH_35B_A3B = "ornith-1.5-35b-a3b-nvfp4"
    LAGUNA_XS_2_1 = "laguna-xs-2.1"


class TemplateEffort(str, Enum):
    """Froggeric's three thinking tiers, as wire values."""

    LOW = "low"
    MEDIUM = "medium"
    XHIGH = "xhigh"


@dataclass(frozen=True)
class ModelCapabilities:
    """Which chat-template contract a deployment speaks.

    Qwen3.8 collapses the public effort vocabulary into three tiers and
    expects the effort nested under ``chat_template_kwargs``. NInfer accepts
    effort only at the top level. Gemma 4, Laguna XS 2.1, and Ornith only
    accept ``enable_thinking``.
    """

    three_tier_effort: bool
    nested_effort: bool


# Qwen3.8 exposes three effort tiers. Gemma 4, Laguna XS 2.1, and Ornith
# are binary-only, so they must not receive reasoning_effort.
_CAPABILITIES: Final[Mapping[LocalReasoningModel, ModelCapabilities]] = {
    LocalReasoningModel.GEMMA4_31B: ModelCapabilities(
        three_tier_effort=False, nested_effort=False
    ),
    LocalReasoningModel.QWEN38_FP8: ModelCapabilities(
        three_tier_effort=True, nested_effort=True
    ),
    LocalReasoningModel.QWEN38_UNSLOTH_NVFP4: ModelCapabilities(
        three_tier_effort=True, nested_effort=True
    ),
    LocalReasoningModel.QWEN38_NVFP4: ModelCapabilities(
        three_tier_effort=True, nested_effort=True
    ),
    LocalReasoningModel.QWEN38_NVFP4_SGLANG: ModelCapabilities(
        three_tier_effort=True, nested_effort=True
    ),
    LocalReasoningModel.QWEN38_NINFER: ModelCapabilities(
        three_tier_effort=True, nested_effort=False
    ),
    LocalReasoningModel.QWEN38_QUASAR_NVFP4: ModelCapabilities(
        three_tier_effort=True, nested_effort=True
    ),
    LocalReasoningModel.ORNITH: ModelCapabilities(
        three_tier_effort=False, nested_effort=False
    ),
    LocalReasoningModel.ORNITH_35B_A3B: ModelCapabilities(
        three_tier_effort=False, nested_effort=False
    ),
    # Laguna's template takes only enable_thinking; it has no effort tiers.
    LocalReasoningModel.LAGUNA_XS_2_1: ModelCapabilities(
        three_tier_effort=False, nested_effort=False
    ),
}

_NINFER_ENCRYPTED_REASONING_INCLUDE: Final[str] = "reasoning.encrypted_content"
_KW_ENABLE_THINKING: Final[str] = "enable_thinking"
_KW_REASONING_EFFORT: Final[str] = "reasoning_effort"
_UNSLOTH_INSTRUCT_SAMPLING_DEFAULTS: Final[Mapping[str, float]] = {
    "temperature": 0.7,
    "top_p": 0.8,
    "presence_penalty": 1.5,
}

# "Off" spellings are a thinking state rather than a tier, so they stay out
# of the tier table.
_OFF_ALIASES: Final[frozenset[str]] = frozenset(
    {"off", "none", "disabled", "false", "0"}
)
_EFFORT_ALIASES: Final[Mapping[str, TemplateEffort]] = {
    "low": TemplateEffort.LOW,
    "minimal": TemplateEffort.LOW,
    "medium": TemplateEffort.MEDIUM,
    "moderate": TemplateEffort.MEDIUM,
    "high": TemplateEffort.XHIGH,
    "xhigh": TemplateEffort.XHIGH,
    "max": TemplateEffort.XHIGH,
    "maximum": TemplateEffort.XHIGH,
    "extra-high": TemplateEffort.XHIGH,
    "x-high": TemplateEffort.XHIGH,
}


def _normalize(value: object) -> str:
    return str(value).strip().lower()


def _local_reasoning_model(value: Any) -> LocalReasoningModel | None:
    if not isinstance(value, str):
        return None
    try:
        return LocalReasoningModel(value)
    except ValueError:
        return None


def _is_off_effort(value: object) -> bool:
    return _normalize(value) in _OFF_ALIASES


def _canonical_effort(value: object) -> TemplateEffort | None:
    """Map the public effort vocabulary onto Froggeric's three tiers."""
    tier = _EFFORT_ALIASES.get(_normalize(value))
    if tier is None:
        logger.warning(
            "local thinking policy: leaving unknown reasoning_effort %r untouched",
            value,
        )
    return tier


def _as_bool_toggle(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return None


def _explicit_enable_thinking(data: Mapping[str, Any]) -> bool | None:
    """Read a direct thinking toggle, with the kwargs layer as authoritative."""
    kwargs = data.get("chat_template_kwargs")
    if isinstance(kwargs, dict):
        toggle = _as_bool_toggle(kwargs.get(_KW_ENABLE_THINKING))
        if toggle is not None:
            return toggle
    return _as_bool_toggle(data.get(_KW_ENABLE_THINKING))


def _apply_unsloth_default_effort(data: dict[str, Any]) -> bool:
    """Keep Unsloth's xhigh default while using Froggeric's safer template."""
    if not isinstance(data.get("messages"), list):
        return False
    if not _extract_controls(data).is_empty:
        return False

    kwargs_in = data.get("chat_template_kwargs")
    kwargs: dict[str, Any] = dict(kwargs_in) if isinstance(kwargs_in, dict) else {}
    kwargs[_KW_ENABLE_THINKING] = True
    kwargs[_KW_REASONING_EFFORT] = TemplateEffort.XHIGH.value
    data["chat_template_kwargs"] = kwargs
    return True


def _apply_unsloth_instruct_sampling_defaults(data: dict[str, Any]) -> bool:
    """Apply Unsloth's non-thinking profile without overriding the client."""
    if not isinstance(data.get("messages"), list):
        return False

    kwargs = data.get("chat_template_kwargs")
    if not isinstance(kwargs, dict) or kwargs.get(_KW_ENABLE_THINKING) is not False:
        return False

    changed = False
    for parameter, value in _UNSLOTH_INSTRUCT_SAMPLING_DEFAULTS.items():
        if data.get(parameter) is None:
            data[parameter] = value
            changed = True
    return changed


def _budget_disables_thinking(budget: Any) -> bool:
    try:
        value = float(budget)
    except (TypeError, ValueError):
        return False
    return value <= 0


@dataclass(frozen=True)
class ThinkingControls:
    """Client thinking controls parsed out of a request."""

    effort: Any | None
    explicit_enable: bool | None
    thinking_token_budget: Any | None

    @property
    def is_empty(self) -> bool:
        return (
            self.effort is None
            and self.explicit_enable is None
            and self.thinking_token_budget is None
        )


def _extract_controls(data: Mapping[str, Any]) -> ThinkingControls:
    return ThinkingControls(
        effort=data.get(_KW_REASONING_EFFORT),
        explicit_enable=_explicit_enable_thinking(data),
        thinking_token_budget=data.get("thinking_token_budget"),
    )


class NInferResponsesPolicy:
    """Drops optional Responses API features NInfer cannot produce."""

    def sanitize(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if "input" not in data:
            return None

        changed = self._drop_reasoning_summary(data)
        changed |= self._drop_encrypted_reasoning(data)
        return data if changed else None

    @staticmethod
    def _drop_reasoning_summary(data: dict[str, Any]) -> bool:
        reasoning_in = data.get("reasoning")
        if not isinstance(reasoning_in, dict) or reasoning_in.get("summary") is None:
            return False

        reasoning = dict(reasoning_in)
        reasoning.pop("summary")
        if reasoning:
            data["reasoning"] = reasoning
        else:
            data.pop("reasoning")
        return True

    @staticmethod
    def _drop_encrypted_reasoning(data: dict[str, Any]) -> bool:
        include_in = data.get("include")
        if not isinstance(
            include_in, list
        ) or _NINFER_ENCRYPTED_REASONING_INCLUDE not in include_in:
            return False

        include = [
            value
            for value in include_in
            if value != _NINFER_ENCRYPTED_REASONING_INCLUDE
        ]
        if include:
            data["include"] = include
        else:
            data.pop("include")
        return True


class ChatTemplateThinkingPolicy:
    """Translates public thinking controls into the model's template contract."""

    def transform(
        self, data: dict[str, Any], model: LocalReasoningModel
    ) -> dict[str, Any] | None:
        if not isinstance(data.get("messages"), list):
            return None

        caps = _CAPABILITIES[model]
        binary_thinking = not caps.three_tier_effort and not caps.nested_effort
        kwargs_in = data.get("chat_template_kwargs")
        kwargs: dict[str, Any] = dict(kwargs_in) if isinstance(kwargs_in, dict) else {}
        controls = _extract_controls(data)
        if (
            binary_thinking
            and controls.effort is None
            and _KW_REASONING_EFFORT in kwargs
        ):
            controls = ThinkingControls(
                effort=kwargs.get(_KW_REASONING_EFFORT),
                explicit_enable=controls.explicit_enable,
                thinking_token_budget=controls.thinking_token_budget,
            )
        if controls.is_empty:
            return None

        changed = False
        if controls.explicit_enable is not None and _KW_ENABLE_THINKING not in kwargs:
            kwargs[_KW_ENABLE_THINKING] = controls.explicit_enable
            changed = True
        if not binary_thinking or controls.explicit_enable is None:
            changed |= self._apply_effort(kwargs, controls.effort, caps)
            changed |= self._apply_budget(kwargs, controls.thinking_token_budget)
        changed |= self._strip_stale_effort(data, kwargs, controls.effort)
        if binary_thinking:
            changed |= data.pop(_KW_REASONING_EFFORT, None) is not None
            changed |= kwargs.pop(_KW_REASONING_EFFORT, None) is not None

        if not changed:
            return None
        data["chat_template_kwargs"] = kwargs
        return data

    def _apply_effort(
        self,
        kwargs: dict[str, Any],
        effort: Any,
        caps: ModelCapabilities,
    ) -> bool:
        if effort is None or kwargs.get(_KW_ENABLE_THINKING) is False:
            return False

        if _is_off_effort(effort):
            kwargs[_KW_ENABLE_THINKING] = False
            return True

        if caps.three_tier_effort:
            tier = _canonical_effort(effort)
            if tier is None:
                return False
            wire_effort: Any = tier.value
        else:
            wire_effort = effort

        changed = False
        if kwargs.get(_KW_ENABLE_THINKING) is not True:
            kwargs[_KW_ENABLE_THINKING] = True
            changed = True
        if caps.nested_effort and kwargs.get(_KW_REASONING_EFFORT) != wire_effort:
            kwargs[_KW_REASONING_EFFORT] = wire_effort
            changed = True
        return changed

    def _apply_budget(self, kwargs: dict[str, Any], budget: Any) -> bool:
        if budget is None:
            return False

        changed = False
        if _budget_disables_thinking(budget):
            if kwargs.get(_KW_ENABLE_THINKING) is not False:
                kwargs[_KW_ENABLE_THINKING] = False
                changed = True
        elif kwargs.get(_KW_ENABLE_THINKING) is not True:
            kwargs[_KW_ENABLE_THINKING] = True
            changed = True
        return changed

    def _strip_stale_effort(
        self,
        data: dict[str, Any],
        kwargs: dict[str, Any],
        effort: Any,
    ) -> bool:
        # vLLM re-arms thinking from a leftover effort, so a thinking-off
        # request must ship with none at either level.
        if effort is None or kwargs.get(_KW_ENABLE_THINKING) is not False:
            return False

        changed = False
        if data.pop(_KW_REASONING_EFFORT, None) is not None:
            changed = True
        if kwargs.pop(_KW_REASONING_EFFORT, None) is not None:
            changed = True
        return changed


class LocalReasoningRequestAdapter(CustomLogger):
    """Proxy hook applying local reasoning-model request policies."""

    def __init__(self) -> None:
        super().__init__()
        self._responses_policy = NInferResponsesPolicy()
        self._chat_policy = ChatTemplateThinkingPolicy()

    def _transform(self, data: dict[str, Any]) -> dict[str, Any] | None:
        model = _local_reasoning_model(data.get("model"))
        if model is None:
            return None

        if model is LocalReasoningModel.QWEN38_NINFER:
            sanitized = self._responses_policy.sanitize(data)
            if sanitized is not None:
                return sanitized

        transformed = self._chat_policy.transform(data, model)
        if model is not LocalReasoningModel.QWEN38_UNSLOTH_NVFP4:
            return transformed

        request = transformed if transformed is not None else data
        changed = False
        if transformed is None:
            changed |= _apply_unsloth_default_effort(request)
        changed |= _apply_unsloth_instruct_sampling_defaults(request)
        return request if changed else transformed

    async def async_pre_call_hook(
        self,
        user_api_key_dict: "UserAPIKeyAuth",
        cache: "DualCache",
        data: dict[str, Any],
        call_type: "CallTypesLiteral",
    ) -> dict[str, Any] | None:
        try:
            return self._transform(dict(data))
        except Exception:
            logger.exception(
                "local thinking policy failed; passing request through unchanged"
            )
            return None


local_thinking_policy = LocalReasoningRequestAdapter()
