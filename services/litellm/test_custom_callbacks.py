"""Basic smoke tests for the Qwen3.8 thinking policy.

Vanilla Python only (stdlib, no pytest, no LiteLLM required). Run from this
directory:

    python3 test_custom_callbacks.py
"""

from __future__ import annotations

import asyncio
import sys
import types
import unittest

try:
    from custom_callbacks import qwen38_thinking_policy
except ImportError:
    # Vanilla-Python fallback: stub the LiteLLM import so the policy module
    # loads without the LiteLLM dependency installed.
    _litellm = types.ModuleType("litellm")
    _integrations = types.ModuleType("litellm.integrations")
    _custom_logger = types.ModuleType("litellm.integrations.custom_logger")

    class CustomLogger:
        pass

    _custom_logger.CustomLogger = CustomLogger
    _litellm.integrations = _integrations
    _integrations.custom_logger = _custom_logger
    sys.modules["litellm"] = _litellm
    sys.modules["litellm.integrations"] = _integrations
    sys.modules["litellm.integrations.custom_logger"] = _custom_logger

    from custom_callbacks import qwen38_thinking_policy


def call_hook(data: dict, call_type: str = "completion") -> dict | None:
    """Invoke the public LiteLLM hook entry point with a copy of ``data``."""
    return asyncio.run(
        qwen38_thinking_policy.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=dict(data),
            call_type=call_type,  # type: ignore[arg-type]
        )
    )


class Qwen38ThinkingPolicySmokeTests(unittest.TestCase):
    # ---- pass-through ----------------------------------------------------

    def test_other_models_pass_through(self):
        for data in (
            {"model": "muse-glimmer-30b", "reasoning_effort": "low"},
            {"model": "deepseek-v4-flash", "reasoning_effort": "max"},
            {"model": "qwen3.9-27b", "reasoning_effort": "low"},
            {"model": "qwen3.8-27b", "reasoning_effort": "low"},
        ):
            with self.subTest(data=data):
                self.assertIsNone(call_hook(data))

    def test_non_completion_route_passes_through(self):
        self.assertIsNone(
            call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"}, "embeddings")
        )

    def test_proxy_route_type_translates(self):
        # The proxy dispatches route_type="acompletion" to the pre-call hook;
        # a guard accepting only "completion" silently no-ops every live request.
        result = call_hook(
            {"model": "qwen3.8-27b-fp8", "reasoning_effort": "none"}, "acompletion"
        )
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    def test_no_controls_leaves_template_default(self):
        self.assertIsNone(call_hook({"model": "qwen3.8-27b-fp8", "max_tokens": 16}))

    def test_unknown_effort_passes_through(self):
        self.assertIsNone(call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "turbo"}))

    def test_all_quantized_variants_are_targets(self):
        for model in ("qwen3.8-27b-bf16", "qwen3.8-27b-fp8", "qwen3.8-27b-nvfp4"):
            with self.subTest(model=model):
                result = call_hook({"model": model, "reasoning_effort": "low"})
                self.assertEqual(
                    result["chat_template_kwargs"],
                    {"enable_thinking": True, "reasoning_effort": "low"},
                )

    # ---- reasoning_effort mapping ----------------------------------------

    def test_effort_none_disables_thinking(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "none"})
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    def test_effort_off_disables_thinking(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "off"})
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    def test_effort_low(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"})
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "low"},
        )

    def test_effort_medium(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "medium"})
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "medium"},
        )

    def test_effort_high_maps_to_xhigh(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "high"})
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )

    def test_effort_max_maps_to_xhigh(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "max"})
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )

    def test_effort_xhigh(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "xhigh"})
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "xhigh"},
        )

    # ---- token budget ------------------------------------------------------

    def test_zero_token_budget_disables_thinking(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "thinking_token_budget": 0})
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})

    def test_positive_token_budget_enables_thinking(self):
        result = call_hook({"model": "qwen3.8-27b-fp8", "thinking_token_budget": 4096})
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": True})

    def test_zero_budget_wins_over_high_effort(self):
        result = call_hook(
            {
                "model": "qwen3.8-27b-fp8",
                "reasoning_effort": "high",
                "thinking_token_budget": 0,
            }
        )
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("reasoning_effort", result)

    # ---- precedence ---------------------------------------------------------

    def test_explicit_kwargs_false_wins_over_effort(self):
        result = call_hook(
            {
                "model": "qwen3.8-27b-fp8",
                "reasoning_effort": "xhigh",
                "chat_template_kwargs": {"enable_thinking": False},
            }
        )
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})

    def test_explicit_top_level_false_wins_over_effort(self):
        result = call_hook(
            {
                "model": "qwen3.8-27b-fp8",
                "reasoning_effort": "medium",
                "enable_thinking": False,
            }
        )
        self.assertEqual(result["chat_template_kwargs"], {"enable_thinking": False})

    def test_explicit_true_with_effort_selects_tier(self):
        result = call_hook(
            {
                "model": "qwen3.8-27b-fp8",
                "reasoning_effort": "low",
                "enable_thinking": True,
            }
        )
        self.assertEqual(
            result["chat_template_kwargs"],
            {"enable_thinking": True, "reasoning_effort": "low"},
        )

    # ---- hygiene ------------------------------------------------------------

    def test_existing_template_kwargs_preserved(self):
        result = call_hook(
            {
                "model": "qwen3.8-27b-fp8",
                "reasoning_effort": "medium",
                "chat_template_kwargs": {"image_count": 0, "video_count": 0},
            }
        )
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
        original = {"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"}
        snapshot = dict(original)
        result = call_hook(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(result["chat_template_kwargs"]["reasoning_effort"], "low")

    def test_policy_failure_does_not_break_hook(self):
        original = qwen38_thinking_policy._transform
        qwen38_thinking_policy._transform = (  # type: ignore[method-assign]
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        try:
            result = call_hook({"model": "qwen3.8-27b-fp8", "reasoning_effort": "low"})
        finally:
            qwen38_thinking_policy._transform = original
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
