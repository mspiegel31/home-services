"""Which run config the entrypoint serves, without Docker.

The entrypoint is written for the image's fixed /opt/strata layout; the test
copies it with those paths rewritten onto a sandbox tree of stub scripts, so
the resolution logic (CONFIG selection, the FAMILY/MODEL tag, the copy for a
CONFIG outside /data, the check mode) runs as shipped.
"""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRYPOINT = HERE / "entrypoint.sh"


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="strata-entrypoint-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.app = self.tmp / "opt-strata"
        self.exporter = self.tmp / "opt-strata-exporter"
        self.data = self.tmp / "data"
        for directory in (self.app / "terminal/bin", self.app / "terminal/python/bin",
                          self.exporter, self.data / "config"):
            directory.mkdir(parents=True)

        (self.app / "terminal/python/bin/python3").write_text("#!/bin/sh\nprintf 'py %s\\n' \"$*\"\n")
        (self.app / "terminal/bin/strata").write_text("#!/bin/sh\nprintf 'strata %s\\n' \"$*\"\n")
        for stub in ("hugepage_preflight.py", "metrics_exporter.py", "merge_args.py"):
            (self.exporter / stub).write_text("# stub\n")
        for script in (self.app / "terminal/python/bin/python3", self.app / "terminal/bin/strata"):
            script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        rewritten = (ENTRYPOINT.read_text()
                     .replace("/opt/strata-exporter", str(self.exporter))
                     .replace("/opt/strata", str(self.app)))
        self.script = self.tmp / "entrypoint.sh"
        self.script.write_text(rewritten)
        self.script.chmod(self.script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def run_entry(self, env):
        full = {"PATH": os.environ["PATH"], "STRATA_DATA": str(self.data), **env}
        return subprocess.run(["/bin/sh", str(self.script)], capture_output=True, text=True,
                              env=full, timeout=60)

    def written(self, tag):
        return self.data / f"config/strata-{tag}.json"

    def test_config_outside_data_is_copied_before_serving(self):
        source = self.tmp / "elsewhere.json"
        source.write_text('{"model_name": "lane"}')
        result = self.run_entry({
            "STRATA_ENTRYPOINT_CHECK": "1", "CONFIG": str(source),
            "FAMILY": "unsloth", "MODEL": "Q8_0",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        copied = self.written("unsloth-q8_0")
        self.assertEqual(copied.read_text(), '{"model_name": "lane"}')
        self.assertIn(f"serve --config {copied} --plan --output json", result.stdout)
        self.assertIn(f"merge_args.py {copied}", result.stdout)

    def test_config_under_data_is_served_in_place(self):
        served = self.data / "strata-configs/strata-unsloth-q8_0.json"
        served.parent.mkdir(parents=True)
        served.write_text('{"model_name": "lane"}')
        result = self.run_entry({
            "STRATA_ENTRYPOINT_CHECK": "1", "CONFIG": str(served),
            "FAMILY": "unsloth", "MODEL": "Q8_0",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"serve --config {served} --plan --output json", result.stdout)
        self.assertEqual([p.name for p in (self.data / "config").iterdir()], [],
                         "copied a config that was already under /data")

    def test_no_config_resolves_the_family_model_tag(self):
        for family, model, tag in (("unsloth", "UD-Q5_K_XL", "unsloth-ud-q5_k_xl"),
                                   ("qwen", "IQ3_S", "iq3_s"),
                                   ("swift", "IQ3_XXS", "swift-iq3_xxs")):
            with self.subTest(family=family, model=model):
                shutil.rmtree(self.data / "config", ignore_errors=True)
                (self.data / "config").mkdir(parents=True)
                cfg = self.data / f"config/strata-{tag}.json"
                cfg.write_text('{"model_name": "lane"}')
                result = self.run_entry({
                    "STRATA_ENTRYPOINT_CHECK": "1", "FAMILY": family, "MODEL": model,
                })
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"serve --config {cfg} --plan --output json", result.stdout)

    def test_missing_config_stops_before_serving(self):
        result = self.run_entry({"FAMILY": "unsloth", "MODEL": "Q8_0"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("strata-unsloth-q8_0.json", result.stderr)
        self.assertIn("prepare job", result.stderr)

    def test_missing_config_file_stops_before_serving(self):
        result = self.run_entry({"CONFIG": str(self.tmp / "gone.json")})
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stderr)

    def test_serve_mode_passes_host_and_port_from_env(self):
        cfg = self.data / "config/strata-unsloth-q8_0.json"
        cfg.write_text('{"model_name": "lane"}')
        result = self.run_entry({
            "FAMILY": "unsloth", "MODEL": "Q8_0", "HOST": "0.0.0.0", "PORT": "8080",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"serve --config {cfg} --host 0.0.0.0 --port 8080", result.stdout)
        self.assertNotIn("--plan", result.stdout)

    def test_check_mode_never_calls_serve_without_plan(self):
        cfg = self.data / "config/strata-iq3_s.json"
        cfg.write_text('{"model_name": "lane"}')
        result = self.run_entry({
            "STRATA_ENTRYPOINT_CHECK": "1", "FAMILY": "qwen", "MODEL": "IQ3_S",
            "HOST": "0.0.0.0", "PORT": "8080",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--plan --output json", result.stdout)
        self.assertNotIn(f"serve --config {cfg} --host", result.stdout)


if __name__ == "__main__":
    unittest.main()
