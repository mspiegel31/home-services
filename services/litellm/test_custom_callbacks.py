"""Basic smoke tests for the qwen thinking policy.

Vanilla Python only (stdlib, no pytest, no LiteLLM required). Run from this
directory:

    python3 test_custom_callbacks.py
"""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from typing import Any

try:
    from custom_callbacks import qwen_thinking_policy
except ImportError:
    # Vanilla-Python fallback: stub the LiteLLM import so the policy module
    # loads without the LiteLLM dependency installed.
    _litellm = types.ModuleType("litellm")
    _integrations = types.ModuleType("litellm.integrations")
    _custom_logger = types.ModuleType("litellm.integrations.custom_logger")

    class CustomLogger:
        def __init__(self, **kwargs: Any) -> None:
            pass

    _custom_logger.CustomLogger = CustomLogger  # type: ignore[attr-defined]
    _litellm.integrations = _integrations  # type: ignore[attr-defined]
    _integrations.custom_logger = _custom_logger  # type: ignore[attr-defined]
    sys.modules["litellm"] = _litellm
    sys.modules["litellm.integrations"] = _integrations
    sys.modules["litellm.integrations.custom_logger"] = _custom_logger

    from custom_callbacks import qwen_thinking_policy


def call_hook(data: dict[str, Any], call_type: str = "completion") -> dict[str, Any] | None:
    """Invoke the public LiteLLM hook entry point with a copy of ``data``."""
    return asyncio.run(
        qwen_thinking_policy.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=dict(data),
            call_type=call_type,  # type: ignore[arg-type]
        )
    )


def chat(controls: dict[str, Any]) -> dict[str, Any]:
    """A minimal chat-completion payload carrying the given request controls."""
    return {"messages": [{"role": "user", "content": "hi"}], **controls}


class QwenThinkingPolicySmokeTests(unittest.TestCase):
    # ---- pass-through ----------------------------------------------------

    def test_other_models_pass_through(self):
        for data in (
            chat({"model": "muse-glimmer-30b", "reasoning_effort": "low"}),
            chat({"model": "qwen3.9-27b", "reasoning_effort": "low"}),
            chat({"model": "qwen3.8-27b", "reasoning_effort": "low"}),
            chat({"model": "thinkingcap-qwen3.6-27b", "reasoning_effort": "low"}),
        ):
            with self.subTest(data=data):
                self.assertIsNone(call_hook(data))

    def test_non_chat_payload_passes_through(self):
        # Embeddings-style payloads carry no messages, so there is no
        # conversation to translate — for any route type.
        data = {
            "model": "qwen3.8-27b-fp8",
            "input": ["hello"],
            "reasoning_effort": "low",
        }
        for call_type in ("embeddings", "completion", "acompletion"):
            with self.subTest(call_type=call_type):
                result = call_hook(dict(data), call_type)
                self.assertIsNone(result)
                self.assertNotIn("chat_template_kwargs", data)

    def test_ninfer_responses_drops_unsupported_reasoning_options(self):
        original = {
            "model": "qwen3.8-27b-ninfer",
            "input": "hi",
            "reasoning": {"effort": "xhigh", "summary": "auto"},
            "include": ["reasoning.encrypted_content"],
            "store": False,
        }
        result = call_hook(original, "responses")
        self.assertEqual(result["reasoning"], {"effort": "xhigh"})
        self.assertNotIn("include", result)
        self.assertEqual(
            original["reasoning"],
            {"effort": "xhigh", "summary": "auto"},
        )

    def test_ninfer_chat_keeps_reasoning_effort_top_level(self):
        result = call_hook(
            chat({"model": "qwen3.8-27b-ninfer", "reasoning_effort": "low"})
        )
        self.assertEqual(result["reasoning_effort"], "low")
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True},
        )

    def test_route_type_does_not_change_behavior(self):
        # The proxy dispatches chat completions as "acompletion"; the policy
        # keys off the payload, so no route spelling can no-op a chat request.
        for call_type in ("completion", "acompletion", "text_completion", "embeddings"):
            with self.subTest(call_type=call_type):
                result = call_hook(
                    chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "none"}),
                    call_type,
                )
                self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
                self.assertNotIn("reasoning_effort", result)

    def test_no_controls_leaves_template_default(self):
        self.assertIsNone(call_hook(chat({"model": "qwen3.8-27b-fp8", "max_tokens": 16})))

    def test_unknown_effort_passes_through(self):
        self.assertIsNone(call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "turbo"})))

    def test_all_quantized_variants_are_targets(self):
        for model in (
            "qwen3.8-27b-fp8",
            "qwen3.8-27b-nvfp4-bf16-lmhead",
            "qwen3.8-27b-nvfp4-bf16-lmhead-sglang",
        ):
            with self.subTest(model=model):
                result = call_hook(chat({"model": model, "reasoning_effort": "low"}))
                self.assertEqual(
                    result["chat_template_kwargs"],
                    {"enable_thinking": True, "reasoning_effort": "low"},
                )

    def test_ornith_is_a_target(self):
        # The policy spans the whole qwen3 reasoning-parser family, not just
        # the Qwen3.8 line: Ornith shares the same chat_template_kwargs
        # contract.
        result = call_hook(chat({"model": "ornith-1.5-9b-nvfp4", "reasoning_effort": "xhigh"}))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )


    def test_ornith_high_effort_is_not_condensed(self):
        result = call_hook(
            chat({"model": "ornith-1.5-9b-nvfp4", "reasoning_effort": "high"})
        )
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "high"},
        )

    def test_non_qwen_family_model_passes_through(self):
        # Models on a different reasoning-parser family are untouched.
        for model in ("nemotron-3.5-lightning", "north-mini-code-1.0-fp8"):
            with self.subTest(model=model):
                self.assertIsNone(
                    call_hook(chat({"model": model, "reasoning_effort": "low"}))
                )

    # ---- reasoning_effort mapping ----------------------------------------

    def test_effort_none_disables_thinking(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "none"}))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    def test_effort_off_disables_thinking(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "off"}))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    def test_effort_low(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"}))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "low"},
        )

    def test_effort_medium(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "medium"}))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "medium"},
        )

    def test_effort_high_maps_to_xhigh(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "high"}))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )

    def test_effort_max_maps_to_xhigh(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "max"}))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )

    def test_effort_xhigh(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "xhigh"}))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )

    # ---- token budget ------------------------------------------------------

    def test_zero_token_budget_disables_thinking(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "thinking_token_budget": 0}))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})

    def test_positive_token_budget_enables_thinking(self):
        result = call_hook(chat({"model": "qwen3.8-27b-fp8", "thinking_token_budget": 4096}))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": True})

    def test_unparseable_token_budget_treated_as_positive(self):
        # A budget that cannot be parsed is not zero, so it takes the
        # positive-budget path and enables thinking.
        result = call_hook(
            chat({"model": "qwen3.8-27b-fp8", "thinking_token_budget": "abc"})
        )
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": True})

    def test_zero_budget_wins_over_high_effort(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-fp8",
            "reasoning_effort": "high",
            "thinking_token_budget": 0,
        }))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    # ---- precedence ---------------------------------------------------------

    def test_explicit_kwargs_false_wins_over_effort(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-fp8",
            "reasoning_effort": "xhigh",
            "chat_template_kwargs": {"enable_thinking": False},
        }))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})

    def test_explicit_top_level_false_wins_over_effort(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-fp8",
            "reasoning_effort": "medium",
            "enable_thinking": False,
        }))
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})

    def test_omp_off_payload_disables_sglang_thinking(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-nvfp4-bf16-lmhead-sglang",
            "enable_thinking": False,
            "chat_template_kwargs": {"preserve_thinking": True},
        }))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"preserve_thinking": True, "enable_thinking": False},
        )

    def test_omp_low_payload_selects_sglang_tier(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-nvfp4-bf16-lmhead-sglang",
            "enable_thinking": True,
            "reasoning_effort": "low",
            "chat_template_kwargs": {
                "preserve_thinking": True,
                "reasoning_effort": "low",
            },
        }))
        self.assertEqual(
            result["chat_template_kwargs"],
            {
                "preserve_thinking": True,
                "enable_thinking": True,
                "reasoning_effort": "low",
            },
        )

    def test_explicit_true_with_effort_selects_tier(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-fp8",
            "reasoning_effort": "low",
            "enable_thinking": True,
        }))
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "low"},
        )

    # ---- hygiene ------------------------------------------------------------

    def test_existing_template_kwargs_preserved(self):
        result = call_hook(chat({
            "model": "qwen3.8-27b-fp8",
            "reasoning_effort": "medium",
            "chat_template_kwargs": {"image_count": 0, "video_count": 0},
        }))
        self.assertEqual(
            result["chat_template_kwargs"],
            {
                "image_count": 0,
                "video_count": 0,
                "enable_thinking": True,
                "reasoning_effort": "medium",
            },
        )

    def test_input_not_mutated(self):
        original = chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"})
        snapshot = dict(original)
        result = call_hook(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(result["chat_template_kwargs"]["reasoning_effort"], "low")

    def test_policy_failure_does_not_break_hook(self):
        original = qwen_thinking_policy._transform
        qwen_thinking_policy._transform = (  # type: ignore[method-assign]
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        try:
            result = call_hook(chat({"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"}))
        finally:
            qwen_thinking_policy._transform = original
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
