"""What merge_args.py writes into a lane's run config before it is served."""
import json
import tempfile
import unittest
from pathlib import Path

import merge_args

LANE_ENV = {"PARALLEL": "8", "STRATA_VRAM_RESERVE_MIB": "2048", "STRATA_PLE_IO": "direct"}


class MergeArgsTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp(prefix="strata-merge-")) / "cfg.json"

    def merged(self, cfg):
        self.path.write_text(json.dumps(cfg))
        merge_args.merge(str(self.path), LANE_ENV)
        return json.loads(self.path.read_text())

    def test_deepseek_config_is_served_as_written(self):
        # strata-dsv41 exits on options it does not know, and takes one request at a time.
        cfg = {"arch": "deepseek41", "exe": "/opt/strata/engine-dsv41/current/strata-dsv41",
               "args": ["--pack", "/data/packs/p", "--max-context", "65536"]}
        self.assertEqual(self.merged(cfg), cfg)

    def test_qwen_config_gets_cache_flags_and_lane_env(self):
        out = self.merged({"exe": "/opt/strata/engine/strata", "args": ["--model", "/data/packs/p"]})
        self.assertIn("--prompt-cache", out["args"])
        self.assertEqual(out["args"][out["args"].index("--vram-reserve-mib") + 1], "2048")
        self.assertEqual(out["parallel"], 8)


if __name__ == "__main__":
    unittest.main()
