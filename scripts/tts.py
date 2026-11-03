"""Configure and run the Qwen3-TTS C CLI using only Python's standard library."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

SKILL_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Config:
    executable: str = ""
    model_dir: str = ""
    voice_profile: str = ""
    language: str = "English"
    quantization: str = "int8"
    threads: int = 4
    seed: int = 42
    temperature: float = 0.5
    max_tokens: int = 2250
    max_duration: float = 180.0
    timeout_seconds: float = 900.0

    def __post_init__(self) -> None:
        for name in ("executable", "model_dir", "voice_profile", "language", "quantization"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name}: expected a nonempty string")
        if self.quantization not in {"none", "int4", "int8"}:
            raise ValueError("quantization: choose none, int4, or int8")
        for name in ("threads", "seed", "max_tokens"):
            value = getattr(self, name)
            if type(value) is not int or value < (0 if name == "seed" else 1):
                raise ValueError(f"{name}: expected an integer >= {0 if name == 'seed' else 1}")
        for name in ("temperature", "max_duration", "timeout_seconds"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name}: expected a finite number > 0")


def read_config(path: Path) -> Config:
    data: object = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    unknown = set(data) - {field.name for field in fields(Config)}
    if unknown:
        raise ValueError(f"{path}: unknown fields: {', '.join(sorted(unknown))}")
    def string(name: str, default: str = "") -> str:
        value: object = data.get(name, default)
        if not isinstance(value, str):
            raise ValueError(f"{name}: expected a string")
        return value

    def integer(name: str, default: int) -> int:
        value: object = data.get(name, default)
        if type(value) is not int:
            raise ValueError(f"{name}: expected an integer")
        return value

    def number(name: str, default: float) -> float:
        value: object = data.get(name, default)
        if type(value) not in (int, float):
            raise ValueError(f"{name}: expected a number")
        return float(value)

    return Config(executable=string("executable"), model_dir=string("model_dir"),
                  voice_profile=string("voice_profile"), language=string("language", Config.language),
                  quantization=string("quantization", Config.quantization),
                  threads=integer("threads", Config.threads), seed=integer("seed", Config.seed),
                  temperature=number("temperature", Config.temperature),
                  max_tokens=integer("max_tokens", Config.max_tokens),
                  max_duration=number("max_duration", Config.max_duration),
                  timeout_seconds=number("timeout_seconds", Config.timeout_seconds))


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def command(config: Config, base: Path, text: str, output: Path) -> list[str]:
    # A bare executable name uses PATH. Explicit paths are relative to the config.
    executable = shutil.which(config.executable) if not any(c in config.executable for c in "/\\") else None
    engine = Path(executable) if executable else resolve_path(config.executable, base)
    model = resolve_path(config.model_dir, base)
    voice = resolve_path(config.voice_profile, base)
    if not engine.is_file() or (os.name != "nt" and not os.access(engine, os.X_OK)):
        raise ValueError(f"executable: not an executable file: {engine}")
    if not model.is_dir():
        raise ValueError(f"model_dir: directory not found: {model}")
    if not voice.is_file():
        raise ValueError(f"voice_profile: file not found: {voice}")
    args = [str(engine), "--model-dir", str(model), "--load-voice", str(voice),
            "--language", config.language, "--text", text, "--threads", str(config.threads),
            "--seed", str(config.seed), "--temperature", str(config.temperature),
            "--max-tokens", str(config.max_tokens), "--max-duration", str(config.max_duration),
            "--output", str(output)]
    if config.quantization != "none":
        args.append(f"--{config.quantization}")
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SKILL_ROOT / "state/config.json",
                        help="JSON config (default: this skill's state/config.json)")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init", help="Create an editable config template; never overwrite an existing file")
    sub.add_parser("check", help="Validate settings and resource paths without loading the model")
    run = sub.add_parser("run", help="Synthesize a UTF-8 text file to WAV; never overwrite existing output")
    run.add_argument("--text-file", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--dry-run", action="store_true", help="Print JSON argv; do not synthesize or create output")
    args = parser.parse_args()
    config_path = args.config.expanduser().resolve()
    try:
        if args.action == "init":
            config_path.parent.mkdir(parents=True, exist_ok=True)
            # Blank paths intentionally require the user to choose their own resources.
            defaults = {field.name: field.default for field in fields(Config)}
            with config_path.open("x", encoding="utf-8") as handle:
                json.dump(defaults, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            print(config_path)
            return 0
        config = read_config(config_path)
        if args.action == "check":
            command(config, config_path.parent, "check", Path("check.wav"))
            print(json.dumps({"config": str(config_path), "status": "valid"}))
            return 0
        text = args.text_file.read_text(encoding="utf-8-sig").strip()
        if not text or "\0" in text:
            raise ValueError(f"{args.text_file}: expected nonempty text without NUL characters")
        output = args.output.expanduser().resolve()
        if output.suffix.lower() != ".wav":
            raise ValueError(f"output: expected .wav extension: {output}")
        argv = command(config, config_path.parent, text, output)
        if args.dry_run:
            print(json.dumps(argv, ensure_ascii=False, indent=2))
            return 0
        if output.exists():
            raise ValueError(f"output already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".tts-", dir=output.parent) as temporary:
            staged = Path(temporary) / "audio.wav"
            argv = command(config, config_path.parent, text, staged)
            subprocess.run(argv, check=True, timeout=config.timeout_seconds, stdout=sys.stderr)
            with wave.open(str(staged), "rb") as audio:
                if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                    raise ValueError(f"backend produced an empty WAV: {staged}")
                remaining = audio.getnframes()
                while remaining:
                    frames = min(remaining, 65536)
                    expected = frames * audio.getnchannels() * audio.getsampwidth()
                    if len(audio.readframes(frames)) != expected:
                        raise ValueError(f"backend produced a truncated WAV: {staged}")
                    remaining -= frames
                duration = audio.getnframes() / audio.getframerate()
            # Exclusive destination creation also protects a file created during inference.
            with output.open("xb") as dest, staged.open("rb") as source:
                try:
                    shutil.copyfileobj(source, dest)
                except BaseException:
                    dest.close()
                    output.unlink(missing_ok=True)
                    raise
        print(json.dumps({"output": str(output), "duration_seconds": duration}, ensure_ascii=False))
        return 0
    except (OSError, EOFError, ValueError, TypeError, wave.Error, subprocess.SubprocessError) as error:
        print(f"{args.action}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
