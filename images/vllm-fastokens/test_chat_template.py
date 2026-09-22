"""Run with the vLLM image's Transformers dependencies: python3 -m unittest discover -s images/vllm-fastokens."""

import json
import random
import unittest
from pathlib import Path

from transformers.utils.chat_template_utils import _compile_jinja_template


TEMPLATE = Path(__file__).with_name("qwen3.8-froggeric-v22.5.jinja").read_text()
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": "Look up weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "units": {"type": "string", "enum": ["fahrenheit", "celsius"]},
                    "city": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {"wind": {"type": "boolean"}, "days": {"type": "integer"}},
                    },
                },
                "required": ["units", "city"],
                "additionalProperties": False,
            },
        },
    }
    for name in ("weather", "forecast")
]


def reorder_keys(value, rng):
    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return {key: reorder_keys(value[key], rng) for key in keys}
    if isinstance(value, list):
        return [reorder_keys(item, rng) for item in value]
    return value


class ToolSchemaSerializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Transformers overrides Jinja's default tojson: unsorted unless requested.
        cls.template = _compile_jinja_template(TEMPLATE)

    def render(self, tools):
        return self.template.render(
            messages=[{"role": "user", "content": "What is the weather?"}],
            tools=tools,
            add_generation_prompt=True,
        )

    def test_nested_key_order_does_not_change_prompt(self):
        baseline = self.render(TOOLS)
        for seed in range(16):
            with self.subTest(seed=seed):
                self.assertEqual(baseline, self.render(reorder_keys(TOOLS, random.Random(seed))))

    def test_serialization_preserves_schema_values_and_array_order(self):
        for tools in (TOOLS, list(reversed(TOOLS))):
            with self.subTest(first_tool=tools[0]["function"]["name"]):
                rendered = self.render(tools)
                definitions = rendered.split("<tools>\n", 1)[1].split("\n</tools>", 1)[0]
                self.assertEqual(tools, [json.loads(line) for line in definitions.splitlines()])


if __name__ == "__main__":
    unittest.main()
