# academic-presentation

供 AI 助手使用的学术汇报技能：从研究材料组织幻灯片与讲稿，分析参考稿风格，并指导录音或合成配音、同步字幕和学术录播的制作与检查。

## 能做什么

- 依据研究问题、方法和实验证据组织汇报，保留指标、单位与结论边界。
- 从真实参考页面提炼布局和表达方式，按内容安排图文密度。
- 新建或改变配音方案时先验证代表性样片，已有合格录音可直接复用；分别评价音色、口音、内容和自然度。
- 使用实际音轨安排切页、对齐字幕，并检查压缩后的图表和视频。
- 比较可用的语音制作方案及运行性能，区分短样音估算和整片实测。

本仓库包含技能指令和一个本地 TTS 配置脚本，不附带幻灯片渲染器、语音模型或 TTS 引擎，也不提供一键生成完整视频的流水线。完整录播所需的画面导出、声音制作、字幕和编码能力按可用的本机、远程或托管环境选择，技能不要求使用固定软件或模型。

## 使用

将仓库下载或克隆到助手能够访问的位置。支持技能加载的助手按各自宿主的安装和发现机制使用；也可以直接让助手读取 `SKILL.md`，再按任务读取其中引用的文档。没有本地文件访问能力时，可将入口及相关参考文档提供为上下文。是否能执行渲染、配音和编码取决于所用环境；只能提供指导时应明确说明实际执行范围。

通用请求示例：

```text
读取 academic-presentation/SKILL.md，根据研究材料和现有幻灯片制作学术汇报。
保留研究事实，先整理讲稿；需要录播时验证代表性样片，再制作视频及所需字幕。
```

自动发现、调用语法和可用工具由各个宿主决定。

### 在 Codex 中使用

针对 Codex，可将仓库克隆到其技能目录下。若设置了 `CODEX_HOME`，使用其下的 `skills/`；以下示例使用默认目录。

Linux/macOS：

```sh
git clone https://github.com/Langingsing/academic-presentation.git ~/.codex/skills/academic-presentation
```

Windows PowerShell：

```powershell
git clone https://github.com/Langingsing/academic-presentation.git "$HOME/.codex/skills/academic-presentation"
```

目标目录已有内容时先核对，避免覆盖已有技能或本地状态。安装后在支持本地技能的 Codex 会话中调用 `$academic-presentation`，例如：

```text
用 $academic-presentation 根据这份论文和现有 PPT 制作会议汇报。
保留研究事实，先给出讲稿和代表性配音样片，再制作完整视频及所需字幕。
```

也可只请求风格分析、讲稿整理或录播检查；技能按任务读取需要的参考文档。

## 录播流程

确认交付要求 → 整理逐页讲稿 → 准备静态或动态画面 → 试做声音和代表性样片 → 分段生成与内容回查 → 字幕对齐 → 合成检查 → 剪辑与交付。已有合格材料直接复用，按任务进入相应阶段。

[完整流程](references/recorded-talk.md)说明了画面导出、不同字幕呈现方式、片头裁剪及字幕同步处理。工具、模型和参数按当前环境选择。

## 可选实现：本地 TTS 脚本

选择这个实现时，脚本需要 Python 3.10+，仅使用标准库；另需自行准备 [Qwen3-TTS C 实现](https://github.com/gabriele-mastrapasqua/qwen3-tts)、相应模型及已编码的 `.qvoice` 或 `.bin` 音色文件。下面命令在仓库根目录执行，Windows 可将 `python` 换为 `py -3`。

```text
python scripts/tts.py init
```

编辑生成的 `state/config.json`，至少填写以下三项。其余参数包括语言、量化、线程数、种子、温度、时长上限和超时，详见 [配置说明](references/tts-configuration.md)。

```json
{
  "executable": "qwen_tts",
  "model_dir": "D:/models/qwen3-tts-base",
  "voice_profile": "D:/voices/my-voice.qvoice"
}
```

这里的路径是示例，按实际执行环境填写。程序名可通过 PATH 查找；显式程序路径、模型路径和音色路径相对于配置文件所在目录解析。Windows 路径可使用 `/`，反斜杠在 JSON 中需转义。

准备 UTF-8 编码的 `talk.txt` 后，先检查配置、预览命令，再生成音频：

```text
python scripts/tts.py check
python scripts/tts.py run --text-file "talk.txt" --output "talk.wav" --dry-run
python scripts/tts.py run --text-file "talk.txt" --output "talk.wav"
```

`init` 和音频生成都不会覆盖已有目标。`check` 只检查配置和路径，不加载模型或验证模型兼容性。`--dry-run` 不执行合成。实际生成会检查输出 WAV；内容、口音和自然度仍需回查与试听。

当前脚本仅支持上述 C CLI。另一个 [qwentts.cpp](https://github.com/ServeurpersoCom/qwentts.cpp) 使用双 GGUF、设备选择和 `.spk`/`.rvq` 参考条件，接口不同，不能直接套用此配置。参见 [性能与后端比较](references/tts-performance.md)。

## 技能与个人状态

只维护一份技能。通用方法放在 `SKILL.md` 和 `references/`；个人偏好、参考材料、配置与项目记录放在技能目录内的 `state/`。

```text
academic-presentation/
├── SKILL.md
├── README.md
├── references/
├── scripts/
└── state/          # 本地数据，Git 忽略
    ├── index.md    # 可选：偏好、材料、案例的索引
    └── config.json
```

没有状态目录时技能仍可使用。存在 `state/index.md` 时按任务读取相关记录；历史参数不自动成为默认值。原始录音、模型和大型产物可留在其他位置，由本地状态记录其位置。状态内相对路径便于迁移，外部绝对路径换机后需重新核对。

`.gitignore` 排除整个 `state/` 以及 Python 缓存。手工压缩目录时需显式排除 `state/` 和 `.git/`，压缩工具不一定遵循 Git 忽略规则。

## 参考与验证

- [技能入口](SKILL.md)：适用范围、风格与学术叙事。
- [录播与配音](references/recorded-talk.md)：从讲稿与画面准备到字幕、剪辑和交付的完整流程。
- [TTS 配置](references/tts-configuration.md)：配置字段、路径与命令行为。
- [TTS 性能](references/tts-performance.md)：后端选择、公平比较及耗时估算。

运行配置脚本的测试：

```text
python -m unittest discover -s scripts -p test_tts.py -v
```

测试覆盖命令预览、含空格及中文的路径、输出保护、无效配置、超时与损坏音频处理。该脚本已在 Linux 上完成真实短音频合成；Windows 使用跨平台路径与参数调用方式，但尚未完成 Windows 实机验证。ASR 匹配与格式检查不能代替真人试听，也不证明克隆声音的自然度。
