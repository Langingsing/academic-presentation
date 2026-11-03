"""Run with: python -m unittest discover -s scripts -p test_tts.py"""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import tts


class TTSUsageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="tts test 中文 ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "模型").mkdir()
        (self.root / "voice profile.qvoice").touch()
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps(asdict(tts.Config(
            executable=sys.executable, model_dir="模型", voice_profile="voice profile.qvoice"
        ))), encoding="utf-8")
        self.text = self.root / "文稿.txt"
        self.text.write_text("Hello, $HOME; `test`.", encoding="utf-8-sig")
        self.output = self.root / "result.wav"

    def invoke(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with patch.object(sys, "argv", ["tts.py", "--config", str(self.config), *args]), redirect_stdout(out), redirect_stderr(io.StringIO()):
            status = tts.main()
        return status, out.getvalue()

    def write_wav(self, argv: list[str], **kwargs: object) -> None:
        self.assertEqual(argv[argv.index("--text") + 1], "Hello, $HOME; `test`.")
        self.assertEqual(argv[argv.index("--model-dir") + 1], str(self.root / "模型"))
        with wave.open(argv[argv.index("--output") + 1], "wb") as audio:
            audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            audio.writeframes(bytes(4800))

    def run_args(self) -> list[str]:
        return ["run", "--text-file", str(self.text), "--output", str(self.output)]

    def test_dry_run_has_no_side_effects(self) -> None:
        with patch.object(tts.subprocess, "run") as process:
            status, text = self.invoke(*self.run_args(), "--dry-run")
        self.assertEqual(status, 0)
        self.assertIn(str(self.root / "voice profile.qvoice"), json.loads(text))
        self.assertFalse(self.output.exists())
        process.assert_not_called()

    def test_success_and_no_overwrite(self) -> None:
        with patch.object(tts.subprocess, "run", side_effect=self.write_wav) as process:
            status, text = self.invoke(*self.run_args())
            self.assertEqual(status, 0)
            self.assertAlmostEqual(json.loads(text)["duration_seconds"], 0.1)
            original = self.output.read_bytes()
            self.assertEqual(self.invoke(*self.run_args())[0], 1)
            self.assertEqual(self.output.read_bytes(), original)
            self.assertEqual(process.call_count, 1)

    def test_timeout_or_corrupt_audio_does_not_publish(self) -> None:
        for failure in (subprocess.TimeoutExpired("tts", 1), None):
            def generate(argv: list[str], **kwargs: object) -> None:
                if failure:
                    raise failure
                Path(argv[argv.index("--output") + 1]).write_bytes(b"bad WAV")
            with patch.object(tts.subprocess, "run", side_effect=generate):
                self.assertEqual(self.invoke(*self.run_args())[0], 1)
            self.assertFalse(self.output.exists())
            self.assertFalse(list(self.root.glob(".tts-*")))

    def test_invalid_config_and_init_preserve_file(self) -> None:
        original = self.config.read_bytes()
        self.assertEqual(self.invoke("init")[0], 1)
        self.assertEqual(self.config.read_bytes(), original)
        data = json.loads(original)
        for key, value in (("threads", True), ("temperature", -1), ("typo", 2)):
            self.config.write_text(json.dumps({**data, key: value}), encoding="utf-8")
            self.assertEqual(self.invoke("check")[0], 1)


if __name__ == "__main__":
    unittest.main()
