# 可选实现：本地 TTS 配置

本页仅说明附带脚本的使用条件，不限定录播流程所用的工具。`scripts/tts.py` 是 Qwen3-TTS C CLI 的轻量入口，不安装模型或后端。需要 Python 3.10+ 和可在本机运行的 `qwen_tts`（Windows 为对应可执行程序）；其他 TTS 后端按其自身接口使用，不将这里的参数直接传给不兼容的程序。

## 配置与运行

以下命令在技能根目录执行。Linux/macOS 使用可用的 Python 3 解释器；Windows 可将 `python` 换为 `py -3`。在其他目录执行时，传入脚本的实际路径。脚本不依赖当前工作目录定位默认配置。

```text
python scripts/tts.py init
python scripts/tts.py check
python scripts/tts.py run --text-file "talk.txt" --output "talk.wav" --dry-run
python scripts/tts.py run --text-file "talk.txt" --output "talk.wav"
```

`init` 只创建一次 `state/config.json`，不会覆盖已有配置。先编辑其中的 `executable`、`model_dir` 和 `voice_profile`：分别指向 Qwen3-TTS C 程序、模型目录及已生成的 `.qvoice` 或 `.bin` 音色文件。参考录音的编码和音色配置创建仍由后端完成；本脚本不声称不同模型间的音色配置兼容。

程序名可通过 PATH 查找；显式程序路径、模型路径和音色路径相对于配置文件所在目录解析，也可使用绝对路径。Windows JSON 路径可写为 `C:/tts/qwen_tts.exe`，若使用反斜杠需写成 `C:\\tts\\qwen_tts.exe`。输入文稿和输出文件相对于调用者当前目录解析；文稿采用 UTF-8，兼容 BOM。

| 字段 | 含义 | 初始值 |
| --- | --- | --- |
| `executable` | Qwen3-TTS C 可执行程序或 PATH 名称 | 空，需配置 |
| `model_dir` | 模型目录 | 空，需配置 |
| `voice_profile` | 已编码的音色文件 | 空，需配置 |
| `language` | 传给后端的语言名称 | `English` |
| `quantization` | `none`、`int4` 或 `int8` | `int8` |
| `threads` | 正整数工作线程数 | `4` |
| `seed` | 非负整数采样种子 | `42` |
| `temperature` | 正数采样温度 | `0.5` |
| `max_tokens` | 正整数最大音频 token 数 | `2250` |
| `max_duration` | 最大音频时长，秒 | `180` |
| `timeout_seconds` | 每次后端进程超时，秒 | `900` |

这些初始值是可修改的起点，不表示适合所有模型、设备或声音。更换后端版本时核对参数支持，先做短样片。`check` 仅检查配置类型和资源路径，不加载模型或证明其完整、兼容；`--dry-run` 输出 JSON 参数数组，不执行 TTS。指定其他配置时将 `--config "路径/config.json"` 放在子命令之前。

运行采用独立参数和 `shell=False`，不拼接 shell 命令。后端日志写入 stderr，成功时 stdout 返回输出路径与实际音频时长的 JSON。先在输出目录的临时子目录中生成并读取完整 PCM WAV，成功后保存到目标；已有目标不会被覆盖。生成失败或超时返回非零退出码，保留已存在的目标文件。内容准确性、音色和自然度仍按录播工作流核对。
