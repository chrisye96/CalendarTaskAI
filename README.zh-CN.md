# CalendarTaskAI

[English](README.md) | **简体中文** | [繁體中文](README.zh-TW.md)

[![v1.0.0 released](https://img.shields.io/badge/v1.0.0-released-brightgreen?logo=github)](https://github.com/chrisye96/CalendarTaskAI/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![Build status](https://img.shields.io/github/actions/workflow/status/chrisye96/CalendarTaskAI/release.yml?label=build&logo=githubactions)](https://github.com/chrisye96/CalendarTaskAI/actions/workflows/release.yml)

> **为 [DesktopCal](https://www.desktopcal.com/)（桌面日历）打造的 AI 任务排期工具。** 用中文或英文随手写下任务；明确的日期和时间由确定性的正则解析器直接锁定，含糊的部分交给 LLM 安排，它了解你日历上的任务量和你的习惯。非官方插件，BYOK（自带 API 密钥）；可从 10 家主流服务商中任选，包括 Gemini、ChatGPT、Claude、Grok、Mistral、DeepSeek、Kimi、Qwen、GLM 和 OpenRouter。

```
┌──────────────────────────────────────────────┐
│  Press Ctrl+Alt+Space anywhere               │
│  ┌────────────────────────────────────────┐  │
│  │ 明天9点开会                            │  │
│  │ 完成项目报告                           │  │
│  │ 每周一健身房                           │  │
│  └────────────────────────────────────────┘  │
│              [Submit]                        │
└──────────────────────────────────────────────┘
                    ↓
   AI Allocation:
   2026-05-07   [09:00] 开会
   2026-05-08   完成项目报告
   2026-05-11   健身房   ← 12 weeks expanded
   2026-05-18   健身房
   ...
                    ↓
            DesktopCal updated
```

---

## 快速开始

### A. Windows 用户（无需 Python）

1. 从[最新发布版](https://github.com/chrisye96/CalendarTaskAI/releases/latest)下载 `CalendarTaskAI-v1.0.0.zip`。
2. 解压到任意位置（例如 `C:\Apps\CalendarTaskAI`）。
3. 双击 `CalendarTaskAI.exe`。设置向导会打开；选择服务商，粘贴你的 API 密钥，点击 **Test**，再点击 **Save**。
4. 按 `Ctrl+Alt+Space` 开始输入任务。托盘图标（浅蓝底上的 CT）位于系统托盘；右键单击可打开完整菜单。

> 首次启动时 Windows SmartScreen 可能会发出警告（程序包未签名）。点击 **更多信息**（More info），再点击 **仍要运行**（Run anyway）。

### B. Python 开发者

```powershell
git clone https://github.com/chrisye96/CalendarTaskAI.git
cd CalendarTaskAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pythonw main.py        # GUI 模式（不显示控制台窗口）
# 或者：python main.py today        # CLI 模式
```

你需要从任一受支持的服务商获取 API 密钥。快速链接：

- [Google Gemini](https://aistudio.google.com/apikey)（有免费额度）
- [OpenAI ChatGPT](https://platform.openai.com/api-keys)（付费）
- [Anthropic Claude](https://console.anthropic.com/settings/keys)（付费）
- [xAI Grok](https://console.x.ai/)（付费）
- [Mistral AI](https://console.mistral.ai/api-keys)（欧盟托管）
- [DeepSeek](https://platform.deepseek.com/api_keys)（便宜）
- [Moonshot Kimi](https://platform.moonshot.cn/console/api-keys)（月之暗面；有免费额度）
- [Alibaba Qwen / DashScope](https://bailian.console.aliyun.com/?tab=model#/api-key)（通义千问；中国大陆访问友好）
- [Zhipu GLM](https://open.bigmodel.cn/usercenter/apikeys)（智谱；中国大陆访问友好）
- [OpenRouter](https://openrouter.ai/keys)（300+ 个模型，一个密钥）

---

## CalendarTaskAI 是什么？

[DesktopCal](https://www.desktopcal.com/)（桌面日历）是一款广受喜爱的免费 Windows 日历，直接显示在桌面壁纸上。往里添加任务，要先点日期，打开一个很小的内嵌编辑框，再打字。加一条任务还行。可大多数人实际做计划的方式是把一串任务一股脑列出来，指望日历自己弄清楚每件事该放在哪天，这时就很痛苦了。

CalendarTaskAI 在 DesktopCal 旁边运行，直接写入它的 SQLite 数据库。它接受自由格式的输入，并分两层来理解：

1. **确定性解析器**处理它能识别的所有日期和时间格式（12 种中文写法、8 种英文写法，外加五种格式的时间和时间范围）。这些任务完全绕过 LLM：即时、免费、可离线。
2. **可插拔的 LLM 后端**只为没有明确日期提示的任务挑选日期。提示词能看到你的个人档案（工作时间、排期规则）、当前任务负荷、近期交互历史，以及你的满意度评分。

结果是：典型输入中 70-90% 无需任何 API 调用即可解析。剩下的 10-30% 交给你配置的 LLM（默认 Gemini；可选启用 DeepSeek，Gemini 失败时自动回退到它）。

---

## 功能

**输入**
- 自由格式的自然语言任务输入，中英文可混用
- 多任务输入：用换行、`;`/`；` 或中文顿号 `、` 分隔
- 明确日期：`今天`、`明天`、`下周一`、`3月25日`、`2026-12-01`、`next monday`、`in 3 days` 等
- 明确时间：`9点`、`9点半`、`下午3-5点`、`9:00-10:30`、`9am` 等
- 重复规则：`每周一健身房`、`每月15号交房租`、`every monday standup`

**排期**
- 确定性优先：正则解析明确的提示，其余的才交给 LLM
- 开箱即支持 10 家主流 LLM 服务商：Google Gemini、OpenAI ChatGPT、Anthropic Claude、xAI Grok、Mistral AI、DeepSeek、Moonshot Kimi、Alibaba Qwen、Zhipu GLM 和 OpenRouter（一个密钥即可使用 300+ 个模型）
- 跨服务商自动回退：配置了 DeepSeek 时，Gemini 请求失败会静默改用 DeepSeek-flash 重试，临时的 API 故障不会让你的输入白费
- 确认界面中的手动升级按钮：**Re-run with DeepSeek-flash** / **Re-run with DeepSeek Pro**
- 结合个人档案的提示词：LLM 会遵守 `profile.md` 中的排期规则
- 行为学习：每个被接受、拒绝或挪动的任务都会反馈到之后的提示词中

**工作流**
- 全局快捷键（默认 `Ctrl+Alt+Space`）打开悬浮输入窗口
- 托盘图标菜单：添加任务、模板子菜单、今日任务、撤销上次添加、重试待处理请求、刷新日历、主题、开机自启
- 5 个内置模板（Standup / 周报 / Sprint planning / 健身计划 / 读书清单），另可在 `data/templates.json` 中添加用户自定义条目
- 一键撤销最近添加的一批任务（CLI 对应命令：`python main.py undo`）
- 离线缓存：失败的 API 请求会在下次启动时自动重试

**分发**
- 一个 zip 内含两个 Windows 可执行文件：`CalendarTaskAI.exe`（无窗口运行，托盘 + 快捷键）和 `CalendarTaskAI-cli.exe`（带控制台的 CLI）
- 也可以在 Python 3.10+ 上从源码运行
- JSON 备份 / 恢复，涵盖配置（密钥已脱敏）、个人档案、历史记录、重复规则、模板，以及前后各 1 年（±1 年）的任务

**细节打磨**
- 浅色 + 深色主题，可在托盘菜单中切换（Light / Dark / Follow System）
- 所有操作按钮在两种主题下都达到 WCAG AA 对比度标准
- 适配高 DPI（在 4K 笔记本上也清晰）
- 日志写入 `%APPDATA%\CalendarTaskAI\logs\app.log`（轮转，1 MB × 5）

---

## 安装

### 方式 A：预构建的 Windows 可执行文件

推荐非开发者使用。

1. 访问 [Releases](https://github.com/chrisye96/CalendarTaskAI/releases) 页面，下载 `CalendarTaskAI-vX.Y.Z.zip`（约 25 MB）。
2. 解压到一个你自己管理的文件夹（例如 `C:\Apps\CalendarTaskAI`）。
3. 解压后你会看到：
   - `CalendarTaskAI.exe`：GUI 启动程序（无控制台窗口）。日常使用就运行这个。
   - `CalendarTaskAI-cli.exe`：带控制台的 CLI 版本。用它运行 `today`、`add`、`next`、`backup` 等命令。
4. （可选）把 `CalendarTaskAI.exe` 固定到任务栏 / 发送到开始菜单，或通过托盘菜单启用开机自启。

### 方式 B：从源码运行

适用于 Windows 上的 Python 3.10+。

```powershell
git clone https://github.com/chrisye96/CalendarTaskAI.git
cd CalendarTaskAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

然后运行：

| 模式 | 命令 |
|------|---------|
| GUI（无控制台） | `pythonw main.py` |
| GUI（带控制台，便于调试） | `python main.py` |
| CLI | `python main.py <command>`（见 [CLI 模式](#cli-模式)） |

### 方式 C：自行构建可执行文件

```powershell
pip install -r requirements-dev.txt
python build_release.py
```

先运行测试套件，然后生成 `dist/CalendarTaskAI-vX.Y.Z.zip`。也可以向 GitHub 推送一个 `v[0-9]*` 标签来触发发布工作流，它会在干净的 Windows runner 上完成同样的步骤，并把 zip 作为草稿附加到 GitHub Release。

---

## 首次运行设置

### GUI

首次启动会显示一个 Tkinter 向导：

1. 从可滚动列表中**选择服务商**（新用户默认使用 Gemini；有免费额度）。
2. 点击“Get a {provider} API key”链接，在浏览器中打开该服务商的 API 密钥页面。
3. 把密钥粘贴到带掩码的输入框中。
4. （推荐）点击 **Test**，发起一次很小的真实 API 调用，确认密钥可用。
5. 点击 **Save**。

密钥只保存在你的电脑上，位于 `%APPDATA%\CalendarTaskAI\data\config.json`。之后要修改，可以直接编辑该文件，或通过托盘菜单 **Config** 打开它。

### CLI

```powershell
python main.py config setup
```

以逐项提示的方式引导你填写同样的字段。按 Enter 保留当前值，输入 `q` 保存并退出。

---

## 日常使用

### GUI 模式

1. 按 `Ctrl+Alt+Space`（或右键单击托盘图标 → **Add Task**）。
2. 在悬浮窗口中输入任务。一行可以写多个任务，用 `;`/`；`/`、` 分隔，或者直接换行。
3. 按 `Ctrl+Enter`（或点击 **Submit**）。
4. AI 分析输入后，会展示建议的分配结果，列出每个任务的日期。
5. 点击 **Confirm** 写入 DesktopCal，点击 **Edit** 修改输入，或点击 **Cancel** 放弃。
6. （配置了 DeepSeek 时）确认界面会多出两个按钮：**Re-run with DeepSeek-flash** 用来换一种方式再试一次，**Re-run with DeepSeek Pro** 用于确实复杂的输入。

需要让 DesktopCal 重新加载（它在内存中的视图不会自动刷新）。可以：
- 切换到另一个月份再切回来，或者手动重启 DesktopCal；或者
- 在 `config.json` 中设置 `auto_restart_desktopcal: true`（默认关闭；注意：这会强制结束 DesktopCal，它其他面板中未保存的内容会丢失）。

### CLI 模式

| 命令 | 用途 | 示例 |
|---------|---------|---------|
| `add [TEXT]` | 通过 AI 添加任务（未提供 TEXT 时从 stdin 读取） | `python main.py add "明天买菜"` |
| `today` | 显示今天的任务 | `python main.py today` |
| `next [N]` | 显示未来 N 天的任务（默认 7 天） | `python main.py next 14` |
| `list [DATE]` | 显示某个日期或日期范围内的任务 | `python main.py list 2026-03-25` |
| `done KEYWORD` | 将匹配的任务标记为已完成 | `python main.py done "买菜"` |
| `undone KEYWORD` | 取消已完成标记 | `python main.py undone "报告"` |
| `delete KEYWORD` | 删除匹配的任务 | `python main.py delete "取消的任务"` |
| `move KEYWORD DATE` | 将匹配的任务移动到 DATE | `python main.py move "会议" 2026-04-01` |
| `search KEYWORD` | 在所有日期中查找任务 | `python main.py search "复盘"` |
| `undo` | 撤销最近添加的一批任务 | `python main.py undo` |
| `backup [--out FILE]` | 将完整状态导出为 JSON | `python main.py backup --out my-backup.json` |
| `restore FILE` | 从备份 JSON 恢复 | `python main.py restore my-backup.json` |
| `export [--format md\|txt]` | 打印某个日期范围内的任务 | `python main.py export --start 2026-03-01 --end 2026-03-31` |
| `retry` | 重试待处理的失败 AI 请求 | `python main.py retry` |
| `refresh` | 打印让 DesktopCal 重新加载显示内容的操作说明 | `python main.py refresh` |
| `profile [view\|edit\|reset]` | 管理个人档案 | `python main.py profile edit` |
| `config [show\|set\|setup]` | 管理配置 | `python main.py config show` |

---

## 托盘菜单

右键单击托盘图标（一个 64×64 的方块，马卡龙浅蓝底上写着“CT”），可以看到：

- **Add Task**：打开输入窗口（默认操作；左键单击也可以）
- **Add from template ▶**：已保存模板的子菜单；选一个即可预填输入窗口
- **Today's Tasks**：用消息框列出今天未完成的任务
- **Undo last add**：撤销最近添加的一批任务（没有可撤销的内容时显示为灰色）
- **Retry Pending**：重试离线缓存中所有失败的 AI 请求
- **Config**：用系统编辑器打开 `config.json`
- **Profile**：用系统编辑器打开个人档案 `profile.md`
- **Theme ▶**：选择主题，Light / Dark / Follow System（单选菜单）
- **Auto Start**：开启或关闭登录时自动启动 CalendarTaskAI 的 Windows 注册表项
- **Quit**：退出

---

## 配置

所有运行时数据都位于 `%APPDATA%\CalendarTaskAI\` 下：

```
%APPDATA%\CalendarTaskAI\
├─ data\
│   ├─ config.json       （服务商密钥、快捷键、主题等）
│   ├─ profile.md        （你的工作习惯 + 排程规则）
│   ├─ history.json      （交互记录 + 行为分析）
│   ├─ pending.json      （等待重试的失败 AI 请求）
│   ├─ recurring.json    （已登记的重复规则）
│   ├─ templates.json    （首次启动时写入的 5 个内置模板 + 用户添加的模板）
│   └─ last_op.json      （最近一批，供 Undo 使用）
└─ logs\
    └─ app.log           （轮转保存，1 MB × 5）
```

### `config.json` 参考

```json
{
  "llm_provider": "gemini",
  "gemini_api_key": "your-key-here",
  "gemini_model": "gemini-3.1-flash-lite-preview",
  "openai_api_key": "",
  "openai_model": "gpt-4o",
  "openai_endpoint": "https://api.openai.com/v1",
  "claude_api_key": "",
  "claude_model": "claude-sonnet-4-6",
  "claude_endpoint": "https://api.anthropic.com/v1",
  "claude_max_tokens": 2048,
  "grok_api_key": "",
  "grok_model": "grok-4",
  "grok_endpoint": "https://api.x.ai/v1",
  "mistral_api_key": "",
  "mistral_model": "mistral-large-latest",
  "mistral_endpoint": "https://api.mistral.ai/v1",
  "deepseek_api_key": "",
  "deepseek_model_flash": "deepseek-v4-flash",
  "deepseek_model_pro": "deepseek-v4-pro",
  "deepseek_endpoint": "https://api.deepseek.com/v1",
  "deepseek_pro_threshold": 5,
  "kimi_api_key": "",
  "kimi_model": "moonshot-v1-32k",
  "kimi_endpoint": "https://api.moonshot.cn/v1",
  "qwen_api_key": "",
  "qwen_model": "qwen-plus",
  "qwen_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "glm_api_key": "",
  "glm_model": "glm-4.6",
  "glm_endpoint": "https://open.bigmodel.cn/api/paas/v4",
  "openrouter_api_key": "",
  "openrouter_model": "openrouter/auto",
  "openrouter_endpoint": "https://openrouter.ai/api/v1",
  "hotkey": "ctrl+alt+space",
  "db_path": "%APPDATA%\\CalendarTask\\Db\\calendar.db",
  "auto_start": false,
  "retry_on_startup": true,
  "auto_restart_desktopcal": false,
  "request_timeout_sec": 30,
  "rating_interval": 20,
  "theme": "system"
}
```

| 字段 | 说明 |
|-------|-------------|
| `llm_provider` | 取值为 `"gemini"`、`"openai"`、`"claude"`、`"grok"`、`"mistral"`、`"deepseek"`、`"kimi"`、`"qwen"`、`"glm"`、`"openrouter"` 之一。默认 Gemini。 |
| `<provider>_api_key` | 所选服务商的 BYOK 密钥。除了发给该服务商，绝不会离开你的电脑。只有当前使用的服务商需要密钥；其他的可以留空。 |
| `gemini_model` | Gemini 模型的确切名称。出现 404 会直接报错（不会静默回退到另一个 Gemini 模型）。 |
| `openai_model` | OpenAI 模型名称。默认为 `gpt-4o`；常见的替换值有 `gpt-5`、`gpt-4o-mini`、`o4-mini`。 |
| `claude_model` | Anthropic 模型名称。默认为 `claude-sonnet-4-6`。需要更强的推理时可改为 `claude-opus-4-5`，想要更快、更便宜的调用可改为 `claude-haiku-4-5`。 |
| `claude_max_tokens` | Anthropic API 要求必填。默认值 2048，用于日期分配绰绰有余。 |
| `grok_model` | xAI 模型名称。默认为 `grok-4`。SuperGrok-Heavy 用户可在 `grok-4.3` 结束测试后改用它。 |
| `mistral_model` | Mistral 模型名称。默认为 `mistral-large-latest`（Mistral Large 3）。想要更便宜的调用可改为 `mistral-small-latest`。 |
| `deepseek_model_flash` / `_pro` | DeepSeek 的“fast”和“smart”两档。输入超过 `deepseek_pro_threshold` 时，应用会选用 pro。 |
| `deepseek_pro_threshold` | 未解析的任务数超过该值时，DeepSeek 自动改用 pro 而不是 flash。默认 5。 |
| `kimi_model` | Moonshot 的上下文长度档位：`moonshot-v1-8k` / `-32k` / `-128k`。默认 32k。 |
| `qwen_model` | Alibaba Qwen 模型。默认为 `qwen-plus`（均衡）。可改为 `qwen3-max`（旗舰）或 `qwen3.5-flash`（最便宜）。 |
| `qwen_endpoint` | DashScope 的 OpenAI 兼容端点。默认使用中国大陆节点；国际用户可换成 `dashscope-intl.aliyuncs.com`（新加坡）或 `dashscope-us.aliyuncs.com`。 |
| `glm_model` | Zhipu GLM 模型。默认为 `glm-4.6`。账号开通权限后可改为 `glm-5` / `glm-5.1`。 |
| `openrouter_model` | OpenRouter 模型 id。默认为 `openrouter/auto`（由 OpenRouter 为每条提示词挑选模型）。可改为具体的 id，例如 `anthropic/claude-opus-4-7` 或 `meta-llama/llama-4-maverick`。 |
| `<provider>_endpoint` | OpenAI 兼容 API / Anthropic API 的基础 URL。只有在通过企业网关或自托管端点转发时才需要修改。 |
| `hotkey` | 打开输入窗口的全局快捷键（使用 [keyboard](https://github.com/boppreh/keyboard) 的语法）。 |
| `db_path` | DesktopCal 的 `calendar.db` 的完整路径。默认为 `%APPDATA%\CalendarTask\Db\calendar.db`，除非 DesktopCal 安装在非标准位置，否则保持不变即可。 |
| `auto_start` | Windows 登录时运行。可通过托盘菜单切换。 |
| `retry_on_startup` | 每次启动时自动重试失败的 AI 请求。 |
| `auto_restart_desktopcal` | **默认关闭**。开启后，写入任务后会强制结束并重新启动 DesktopCal（视图会自动刷新，但它其他面板中未保存的内容可能会丢失）。 |
| `request_timeout_sec` | 每次 LLM API 调用的超时时间。 |
| `rating_interval` | 每 N 次操作提示一次满意度评分。 |
| `theme` | `"light"` / `"dark"` / `"system"`。`"system"` 跟随 Windows 的应用主题。 |

---

## 输入参考

### 日期提示

| 你输入 | 解析为 |
|----------|-------------|
| `今天` `今日` `今晚` | 今天 |
| `明天` `明日` | 明天 |
| `后天` `大后天` | 后天 / 3 天后 |
| `下周` | 下周一 |
| `下周一` ~ `下周日` | 下周的周一/周二/.../周日 |
| `这周三` `这周末` | 本周三 / 本周六 |
| `周一` ~ `周日`, `星期一` ~ `星期天`, `礼拜一` ~ `礼拜天` | 接下来最近的那个星期几 |
| `下个月` `这个月` `月初` `月底` | 下月 1 日 / 本月 1 日 / 本月第一天或最后一天 |
| `3天后` `三天后` `2周后` `1个月后` | 相对偏移（阿拉伯数字或中文数字均可） |
| `2026年3月25日` `2026-03-25` `2026.03.25` `2026/03/25` | 完整的 ISO / 中文日期 |
| `3月25日` `3月25` `0325` `3.25` `3/25` `3-25` | 短日期（自动推断年份；已过去的日期顺延到明年） |
| `today` `tonight` `tomorrow` `next week` `next monday` | 对应的英文写法 |
| `in 3 days` `in 2 weeks` `end of month` | 英文相对日期 |

### 时间提示

时间前缀以 `[HH:MM]` 或 `[HH:MM-HH:MM]` 的形式加在任务文本前。这部分完全由确定性解析器负责（LLM 不允许自行编造时间，以免格式走样）。

| 你输入 | 结果 |
|----------|---------|
| `9点开会` | `[09:00] 开会` |
| `9点半开会` | `[09:30] 开会` |
| `9点45分会议` | `[09:45] 会议` |
| `上午9点开会` `下午3点开会` `晚上9点睡觉` `凌晨2点起床` `中午12点吃饭` | 按时段转换为 24 小时制 |
| `9-10点 开会` `下午3-5点 讨论` | 中文时间范围 |
| `9:00 daily standup` `3pm meeting` `9:00-10:30 review` `9-11am sprint` | 西式时间范围，AM/PM |

可以组合：`明天9点开会` 解析为 date=明天，task=`[09:00] 开会`。

### 重复规则

| 你输入 | 安排结果 |
|----------|---------------------|
| `每周一 健身房` | 未来 12 周的每周一安排“健身房” |
| `每周一三五 健身` | 每周一 / 周三 / 周五 |
| `每周一、三、五 健身` | 用顿号分隔的等效写法 |
| `每周三 上午10-11点 团队会议` | 每周三 `[10:00-11:00] 团队会议` |
| `每月15号 交房租` | 每月 15 日安排“交房租” |
| `每月1日 报销` | 每月 1 日安排“报销” |
| `every monday 9am standup` | 每周一 `[09:00] standup` |
| `every fri team review` | 每周五“team review” |

特性：
- **提前展开约 12 周**。新生成的实例会显示在确认界面中；你可以取消整批。
- **规则仅在确认时保存**。取消的输入不会在 `recurring.json` 中留下任何痕迹。
- **启动时补齐**。每次启动都会把滚动的 12 周窗口补满。同一天内重复执行结果不变（幂等）。
- **不在支持范围内**：双周、按月内日期范围、“每隔一个周二”、完整的 cron 表达式。如果你真的会用到其中某项，欢迎提 issue。

### 分隔符行为

| 分隔符 | 是否拆分？ |
|-----------|---------|
| 换行 | 是 |
| `;` `；`（英文 / 中文分号） | 是 |
| `、`（中文顿号） | 是 |
| `,` `，`（普通逗号） | **否**（会把“买菜, 然后洗衣服”这样的句子拆坏） |
| 空格 | **否**（会把“完成项目报告”这样的短语拆开） |

---

## 个人档案

个人档案位于 `%APPDATA%\CalendarTaskAI\data\profile.md`，每次调用 LLM 都会放进提示词。首次启动时会生成一个模板：

```markdown
# Personal Profile

## Career
- Role: 
- Industry: 
- Current projects: 

## Skills
- Primary skills: 
- Learning: 

## Work Habits
- Preferred working hours: 
- Most productive time: 

## Scheduling Rules
<!-- The AI will follow these rules when assigning dates -->
- No work tasks on weekends
- Max 3 tasks per workday
- Programming tasks in the morning
- Exercise on Mon/Wed/Fri
- Meetings only in the afternoon

## Preferences
- Task priority style: deadline-driven
- Preferred task granularity: detailed steps
```

其中 **Scheduling Rules** 一节的影响最直接：在为未解析的任务挑选日期时，LLM 会把其中每一条都当作硬性约束。可通过托盘菜单 **Profile** 或 `python main.py profile edit` 编辑个人档案。

---

## 主题

内置两套配色：马卡龙浅蓝的浅色主题，以及降低饱和度的蓝色深色主题。

- **Light**（浅色）：粉彩底色，浅蓝强调色，深海军蓝主文字。
- **Dark**（深色）：带蓝调的石板灰底色，降低饱和度的浅蓝强调色，米白主文字。操作按钮在较浅的强调色上使用深色文字，以满足 WCAG AA 对比度（浅蓝底配白字达不到 AA）。

通过托盘菜单 **Theme ▶ Light / Dark / Follow System** 切换主题。“Follow System”选项读取 Windows 注册表值 `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`。

切换会在你下次打开输入窗口或向导时生效。如果切换时某个窗口正显示着，它会保持原样（免得打断你手上的事），下次打开时再用新配色重建。

---

## 备份与恢复

```powershell
python main.py backup --out my-backup.json
python main.py restore my-backup.json
```

备份包含：
- `config.json`（API 密钥会被替换为 `*** REDACTED ***`）
- `profile.md`
- `history.json`
- `templates.json`
- `recurring.json`
- 日历数据库中前后各 1 年（±1 年）的任务

恢复会覆盖 `profile.md`、`history.json`、`templates.json` 和 `recurring.json`。任务会**追加**到数据库中（如果在已有数据的数据库上恢复，可能出现重复）。API 密钥沿用你现有 `config.json` 中的值；备份从不包含真实密钥，即使使用 `--overwrite-config` 创建也是如此。

---

## DesktopCal 集成原理

CalendarTaskAI 直接写入 DesktopCal 的 SQLite 数据库，位于 `%APPDATA%\CalendarTask\Db\calendar.db`。

**表结构**：
- 表：`item_table`
- 键字段：`it_unique_id`，格式为 `dkcal_mdays_YYYYMMDD`（例如 `dkcal_mdays_20260325`）
- 内容字段：`it_content`。同一天的任务存为一个字符串，以 `\r\n` 分隔。已完成的任务带有 `[+]` 前缀。

**刷新**：DesktopCal 会把显示内容缓存在内存里。写入之后它不会察觉，直到你在 DesktopCal 中切换到别的月份再切回来。设置 `auto_restart_desktopcal: true` 可让 CalendarTaskAI 在每次写入后强制重启 DesktopCal（注意：DesktopCal 其他面板中未保存的内容会丢失）。

---

## 架构

写给好奇的开发者。约 25 个模块、6 000 行生产环境 Python 代码；197 个单元测试。

### 处理流程

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│  task_parser.preprocess_input               │
│  ├─ split_tasks                             │
│  ├─ recurring.parse_recurring_rule          │  → expand 12 weeks
│  ├─ extract_date  (regex)                   │
│  └─ extract_time  (regex, separate module)  │
│  Returns: (resolved, unresolved, pending_recurring)
└─────────────────────────────────────────────┘
    │                  │                  │
    │ resolved         │ unresolved       │ pending_recurring
    │                  ▼                  │
    │      ┌─────────────────────┐        │
    │      │  ai_client.analyze  │        │
    │      │  + provider routing │        │
    │      └──────────┬──────────┘        │
    ▼                 ▼                   │
   merge ─────────────────────────────────┤
                      │                   │
                      ▼                   ▼
              calendar_db.write_tasks   recurring.register_rule
                      │                  (only on user confirm)
                      ▼
              DesktopCal calendar.db
```

### 关键模块

| 模块 | 用途 |
|--------|---------|
| `main.py` | 入口；分流 CLI 与 GUI，把带 CLI 参数启动的 GUI exe 转交给 CLI exe |
| `cli.py` | 基于 Click 的 CLI（add/today/next/done/undo/backup/restore/...） |
| `ui.py` | Tkinter 悬浮输入窗口，跟随主题 |
| `tray.py` | pystray 图标 + 菜单（模板子菜单、主题子菜单、开机自启、撤销） |
| `setup_wizard.py` | 首次运行的 BYOK Tkinter 向导（服务商选择、掩码密钥输入框、Test 按钮） |
| `task_parser.py` | 拆分多任务输入，执行日期提取（中文 + 英文） |
| `time_parser.py` | 一天中时间的提取（24 小时制、12 小时制 + AM/PM、带时段的中文、时间范围） |
| `recurring.py` | 按周 / 按月规则解析 + 提前展开 12 周 + 启动时补齐 |
| `ai_client.py` | 跨服务商编排：指定服务商、自动回退、构建提示词 |
| `providers/` | `LLMProvider` 抽象基类 + `OpenAICompatibleProvider` 基类 + 10 个具体服务商（Gemini / OpenAI / Claude / Grok / Mistral / DeepSeek / Kimi / Qwen / GLM / OpenRouter）+ 工厂 |
| `calendar_db.py` | 针对 DesktopCal 表结构的 SQLite 读写；LIKE 转义、锁冲突重试 |
| `last_op.py` | 记录最近添加的一批任务，用于单步撤销 |
| `templates.py` | 5 个内置模板 + 用户自定义；托盘子菜单 |
| `backup.py` | 带 schema 版本号的完整状态 JSON 导出 / 恢复 |
| `theme.py` | 浅色 + 深色配色 token；解析系统偏好 |
| `history.py` | 交互日志 + 为提示词生成行为模式摘要 |
| `retry_queue.py` | 失败 AI 请求的离线缓存；在启动时或通过 CLI 重试 |
| `config_manager.py` | `config.json` 加载 / 保存；交互式设置 |
| `profile_manager.py` | `profile.md` 加载 / 编辑 |
| `logger.py` | `%APPDATA%\CalendarTaskAI\logs\` 下的轮转日志文件处理器 |
| `constants.py` | 集中管理的路径 + DEFAULT_CONFIG |

---

## 故障排除

**API 密钥错误 / “Not configured”** 运行 `python main.py config setup`（或打开 GUI 使用向导），重新输入密钥。

**快捷键无效**
- 确认已安装 `keyboard`（`pip show keyboard`）。
- 尝试以管理员身份运行（Windows 会阻止某些应用在没有管理员权限时注册全局快捷键）。
- 在 `config.json` 中修改快捷键：`"hotkey": "ctrl+shift+t"`。

**数据库被锁定** 暂时关闭 DesktopCal；应用会重试 3 次，每次退避 0.5 秒，但在其他进程持有排他锁时无法写入。

**任务已写入，但 DesktopCal 不显示** DesktopCal 会缓存内存中的视图。切换到另一个月份再切回来。或者设置 `auto_restart_desktopcal: true`。

**托盘图标不出现** 必须安装 Pillow + pystray（`pip install pillow pystray`）。展开系统托盘的隐藏图标区域；Windows 经常把新图标隐藏起来。

**API 限流 / 配额用尽** 失败的请求会保存到 `pending.json`，并在下次启动时重试。也可以换用其他服务商或等配额恢复后，运行 `python main.py retry`。

**打包的 exe 无法启动** 右键单击 `CalendarTaskAI.exe` → 属性 → 如果有“解除锁定”，勾选它（Windows 对下载文件的来源保护）。确认 Windows 版本为 10 或更高。

**日志在哪里？** `%APPDATA%\CalendarTaskAI\logs\app.log`。达到 1 MB 时轮转，保留 5 个备份。

---

## 参与贡献

欢迎提交 Pull Request。仓库遵循 Conventional Commits 规范（`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`），每个发布标签都会运行完整的测试套件。

运行测试：

```powershell
pip install -r requirements-dev.txt
pytest tests/
```

在本地构建发布包：

```powershell
python build_release.py
```

---

## 许可证与致谢

MIT。见 [LICENSE](LICENSE)。

CalendarTaskAI 是 DesktopCal 的**非官方**插件，与 DesktopCal 作者没有关联，也未获其认可。

基于以下项目构建：
- [DesktopCal](https://www.desktopcal.com/)，本插件写入的日历应用。
- 它支持的十家 LLM 服务商：Google Gemini、OpenAI、Anthropic Claude、xAI Grok、Mistral AI、DeepSeek、Moonshot Kimi、Alibaba Qwen、Zhipu GLM 和 OpenRouter。
- 承担主要工作的开源依赖：pystray、Pillow、keyboard、click、google-genai、PyInstaller。

> 本文由英文版机器翻译而来，尚未经过母语者逐行审校。如有出入，以 [English](README.md) 版本为准。
