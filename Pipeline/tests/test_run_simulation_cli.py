import os
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CliTests(unittest.TestCase):
    def run_cli(self, *extra):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, os.path.join(PIPELINE, "run_simulation.py"),
                 "--config", os.path.join(PIPELINE, "config.json"),
                 "--output-dir", out, "--workers", "2", "--episodes", "4", *extra],
                capture_output=True, text=True, timeout=120,
            )
            return result, sorted(os.listdir(out))

    def test_orchestrated_mode_writes_every_episode(self):
        result, files = self.run_cli("--orchestrated")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 completed, 0 failed", result.stdout)
        self.assertEqual(len(files), 4)

    def test_default_mode_still_works(self):
        result, files = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(files), 4)


if __name__ == "__main__":
    unittest.main()
