"""A restart must refuse a corrupted cache and preserve a valid one."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import accelerated_longbaseline as runner


class ResumeIntegrityChecks(unittest.TestCase):
    def test_changed_input_and_changed_frozen_fit_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "results/123_longbaseline"
            folder.mkdir(parents=True)
            source = root / "source.csv"
            source.write_bytes(b"time,flux\n1,1\n")
            processed = folder / "lightcurve.csv.gz"
            processed.write_bytes(b"fixture-processed-bytes")
            signal = dict(period_days=4.2, epoch_btjd=1.0, duration_days=0.1, depth=0.001)
            frozen = folder / "frozen_training.json"
            frozen.write_text(json.dumps(dict(signals=[signal])))
            result = dict(
                tic=123,
                status="longbaseline_screened",
                source_data="source.csv",
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                processed_data_sha256=hashlib.sha256(processed.read_bytes()).hexdigest(),
                signals=[signal],
            )
            path = folder / "result.json"
            path.write_text(json.dumps(result))
            before = path.read_bytes()
            with patch.object(runner, "ROOT", root):
                self.assertTrue(runner.checked_cache(123))
                self.assertEqual(path.read_bytes(), before)
                source.write_bytes(b"changed-input")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    runner.checked_cache(123)
                source.write_bytes(b"time,flux\n1,1\n")
                frozen.write_text(json.dumps(dict(signals=[dict(signal, period_days=4.3)])))
                with self.assertRaisesRegex(ValueError, "Frozen-result mismatch"):
                    runner.checked_cache(123)
                self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
