"""LiteLLM request policies for local reasoning models.

The policy normalizes public thinking controls into each model's chat-template
contract before LiteLLM forwards Chat Completions requests to llama-swap.
Other models and API shapes pass through unchanged.

Precedence for each managed model:

1. an explicit boolean ``chat_template_kwargs.enable_thinking``
2. an explicit boolean top-level ``enable_thinking``
3. ``thinking_token_budget`` (zero disables thinking, otherwise enables it)
4. ``reasoning_effort``

When the resolved state is thinking-off, a stale top-level
``reasoning_effort`` is stripped so vLLM's effort-to-thinking auto-injection
has nothing to act on.

The Froggeric template defaults to medium thinking when none of those controls
is present; Qwen3.8 FP8 keeps that default. Swift 1.5's pinned Froggeric
template instead receives an explicit xhigh default.
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

    QWEN38_FP8 = "qwen3.8-27b-fp8"
    QWEN38_FLASH_NEXT_NVFP4 = "qwen3.8-flash-next-nvfp4"
    QWEN38_SWIFT_1_5_FLASH_NEXT_NVFP4 = "swift-1.5-qwen3.8-flash-next-nvfp4"
    QWEN38_SWIFT_1_5_NVFP4 = "swift-1.5-qwen3.8-27b-nvfp4"
    QWEN38_SWIFT_1_5_BF16 = "swift-1.5-qwen3.8-27b-bf16"


class TemplateEffort(str, Enum):
    """Froggeric's three thinking tiers, as wire values."""

    LOW = "low"
    MEDIUM = "medium"
    XHIGH = "xhigh"



_KW_ENABLE_THINKING: Final[str] = "enable_thinking"
_KW_REASONING_EFFORT: Final[str] = "reasoning_effort"

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
        return LocalReasoningModel(value.rsplit("/", maxsplit=1)[-1])
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


def _apply_swift_default_effort(data: dict[str, Any]) -> bool:
    """Set Swift 1.5's pinned Froggeric template to xhigh by default."""
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


class ChatTemplateThinkingPolicy:
    """Translates public thinking controls into the Qwen3.8 template contract."""

    def transform(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(data.get("messages"), list):
            return None

        kwargs_in = data.get("chat_template_kwargs")
        kwargs: dict[str, Any] = dict(kwargs_in) if isinstance(kwargs_in, dict) else {}
        controls = _extract_controls(data)
        if controls.is_empty:
            return None

        changed = False
        if controls.explicit_enable is not None and _KW_ENABLE_THINKING not in kwargs:
            kwargs[_KW_ENABLE_THINKING] = controls.explicit_enable
            changed = True
        changed |= self._apply_effort(data, kwargs, controls.effort)
        changed |= self._apply_budget(kwargs, controls.thinking_token_budget)
        changed |= self._strip_stale_effort(data, kwargs, controls.effort)
        if not changed:
            return None
        data["chat_template_kwargs"] = kwargs
        return data

    def _apply_effort(
        self,
        data: dict[str, Any],
        kwargs: dict[str, Any],
        effort: Any,
    ) -> bool:
        if effort is None or kwargs.get(_KW_ENABLE_THINKING) is False:
            return False

        if _is_off_effort(effort):
            kwargs[_KW_ENABLE_THINKING] = False
            return True

        tier = _canonical_effort(effort)
        if tier is None:
            return False
        changed = False
        if kwargs.get(_KW_ENABLE_THINKING) is not True:
            kwargs[_KW_ENABLE_THINKING] = True
            changed = True
        if kwargs.get(_KW_REASONING_EFFORT) != tier.value:
            kwargs[_KW_REASONING_EFFORT] = tier.value
            changed = True
        changed |= data.pop(_KW_REASONING_EFFORT, None) is not None
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
        self._chat_policy = ChatTemplateThinkingPolicy()

    def _transform(self, data: dict[str, Any]) -> dict[str, Any] | None:
        model = _local_reasoning_model(data.get("model"))
        if model is None:
            return None

        transformed = self._chat_policy.transform(data)
        uses_froggeric_xhigh_default = model in (
            LocalReasoningModel.QWEN38_SWIFT_1_5_NVFP4,
            LocalReasoningModel.QWEN38_SWIFT_1_5_BF16,
            LocalReasoningModel.QWEN38_SWIFT_1_5_FLASH_NEXT_NVFP4,
        )
        if not uses_froggeric_xhigh_default:
            return transformed

        request = transformed if transformed is not None else data
        if transformed is None and _apply_swift_default_effort(request):
            return request
        return transformed

    def _safe_transform(self, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return self._transform(dict(data))
        except Exception:
            logger.exception(
                "local thinking policy failed; passing request through unchanged"
            )
            return None

    async def async_pre_call_hook(
        self,
        user_api_key_dict: "UserAPIKeyAuth",
        cache: "DualCache",
        data: dict[str, Any],
        call_type: "CallTypesLiteral",
    ) -> dict[str, Any] | None:
        return self._safe_transform(data)

    async def async_pre_call_deployment_hook(
        self,
        kwargs: dict[str, Any],
        call_type: Any,
    ) -> dict[str, Any] | None:
        """Transform the selected deployment immediately before forwarding."""
        return self._safe_transform(kwargs)


local_thinking_policy = LocalReasoningRequestAdapter()
