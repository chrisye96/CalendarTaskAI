# CalendarTaskAI

[English](README.md) | [简体中文](README.zh-CN.md) | **繁體中文**

[![v1.0.0 released](https://img.shields.io/badge/v1.0.0-released-brightgreen?logo=github)](https://github.com/chrisye96/CalendarTaskAI/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![Build status](https://img.shields.io/github/actions/workflow/status/chrisye96/CalendarTaskAI/release.yml?label=build&logo=githubactions)](https://github.com/chrisye96/CalendarTaskAI/actions/workflows/release.yml)

> **為 [DesktopCal](https://www.desktopcal.com/)（桌面日曆）打造的 AI 任務排程工具。** 用中文或英文隨手寫下任務；明確的日期和時間由確定性的正規表示式解析器直接鎖定，模糊的部分交給 LLM 安排，它了解你日曆上的任務量和你的習慣。非官方外掛，BYOK（自備 API 金鑰）；可從 10 家主流供應商中任選，包括 Gemini、ChatGPT、Claude、Grok、Mistral、DeepSeek、Kimi、Qwen、GLM 和 OpenRouter。

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

## 快速入門

### A. Windows 使用者（不需要 Python）

1. 從[最新版本](https://github.com/chrisye96/CalendarTaskAI/releases/latest)下載 `CalendarTaskAI-v1.0.0.zip`。
2. 解壓縮到任意位置（例如 `C:\Apps\CalendarTaskAI`）。
3. 按兩下 `CalendarTaskAI.exe`。設定精靈會開啟；選擇供應商，貼上你的 API 金鑰，按一下 **Test**，再按 **Save**。
4. 按 `Ctrl+Alt+Space` 開始輸入任務。系統匣圖示（淺藍底上的 CT）會出現在系統匣中；按右鍵可開啟完整選單。

> 首次啟動時 Windows SmartScreen 可能會發出警告（套件未簽署）。按一下 **其他資訊**（More info），再按 **仍要執行**（Run anyway）。

### B. Python 開發者

```powershell
git clone https://github.com/chrisye96/CalendarTaskAI.git
cd CalendarTaskAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pythonw main.py        # GUI 模式（不顯示主控台視窗）
# 或是：python main.py today        # CLI 模式
```

你需要向任一支援的供應商申請 API 金鑰。快速連結：

- [Google Gemini](https://aistudio.google.com/apikey)（有免費額度）
- [OpenAI ChatGPT](https://platform.openai.com/api-keys)（付費）
- [Anthropic Claude](https://console.anthropic.com/settings/keys)（付費）
- [xAI Grok](https://console.x.ai/)（付費）
- [Mistral AI](https://console.mistral.ai/api-keys)（歐盟託管）
- [DeepSeek](https://platform.deepseek.com/api_keys)（便宜）
- [Moonshot Kimi](https://platform.moonshot.cn/console/api-keys)（月之暗面；有免費額度）
- [Alibaba Qwen / DashScope](https://bailian.console.aliyun.com/?tab=model#/api-key)（通義千問；適合中國大陸連線）
- [Zhipu GLM](https://open.bigmodel.cn/usercenter/apikeys)（智譜；適合中國大陸連線）
- [OpenRouter](https://openrouter.ai/keys)（300+ 個模型，一把金鑰）

---

## CalendarTaskAI 是什麼？

[DesktopCal](https://www.desktopcal.com/)（桌面日曆）是一款廣受喜愛的免費 Windows 日曆，直接畫在桌布上。要在裡面新增任務，得先點選日期，開啟一個很小的內嵌編輯框，再打字。加一筆任務還好。但大多數人實際做規劃的方式是把一串任務一口氣列出來，期待日曆自己搞清楚每件事該排在哪天，這時就很痛苦了。

CalendarTaskAI 在 DesktopCal 旁邊執行，直接寫入它的 SQLite 資料庫。它接受自由格式的輸入，並分兩層來理解：

1. **確定性解析器**處理它能辨識的所有日期與時間格式（12 種中文寫法、8 種英文寫法，外加五種格式的時間與時間範圍）。這些任務完全不經過 LLM：即時、免費、可離線使用。
2. **可抽換的 LLM 後端**只為沒有明確日期提示的任務挑選日期。提示詞會看到你的個人檔案（工作時間、排程規則）、目前的任務量、近期的互動紀錄，以及你的滿意度評分。

結果是：一般輸入中 70-90% 不需要任何 API 呼叫就能解析。剩下的 10-30% 交給你設定的 LLM（預設 Gemini；可選擇啟用 DeepSeek，Gemini 失敗時自動改用它）。

---

## 功能

**輸入**
- 自由格式的自然語言任務輸入，中英文可混用
- 多任務輸入：用換行、`;`/`；` 或中文頓號 `、` 分隔
- 明確日期：`今天`、`明天`、`下周一`、`3月25日`、`2026-12-01`、`next monday`、`in 3 days` 等
- 明確時間：`9点`、`9点半`、`下午3-5点`、`9:00-10:30`、`9am` 等
- 重複規則：`每周一健身房`、`每月15号交房租`、`every monday standup`

**排程**
- 確定性優先：由正規表示式解析明確的提示，其餘才交給 LLM
- 內建支援 10 家主流 LLM 供應商：Google Gemini、OpenAI ChatGPT、Anthropic Claude、xAI Grok、Mistral AI、DeepSeek、Moonshot Kimi、Alibaba Qwen、Zhipu GLM 和 OpenRouter（一把金鑰即可使用 300+ 個模型）
- 跨供應商自動備援：設定了 DeepSeek 時，Gemini 失敗會自動改用 DeepSeek-flash 重試，暫時性的 API 問題不會讓你的輸入白費
- 確認畫面中的手動升級按鈕：**Re-run with DeepSeek-flash** / **Re-run with DeepSeek Pro**
- 結合個人檔案的提示詞：LLM 會遵守 `profile.md` 中的排程規則
- 行為學習：每個被接受、拒絕或移動的任務都會回饋到之後的提示詞中

**工作流程**
- 全域快速鍵（預設 `Ctrl+Alt+Space`）開啟浮動輸入視窗
- 系統匣圖示選單：新增任務、範本子選單、今日任務、復原上次新增、重試待處理請求、重新整理日曆、主題、開機自動啟動
- 5 個內建範本（Standup / 周报 / Sprint planning / 健身计划 / 读书清单），另可在 `data/templates.json` 中加入使用者自訂項目
- 一鍵復原最近新增的一批任務（CLI 對應指令：`python main.py undo`）
- 離線快取：失敗的 API 請求會在下次啟動時自動重試

**發行方式**
- 一個 zip 內含兩個 Windows 執行檔：`CalendarTaskAI.exe`（無視窗執行，系統匣 + 快速鍵）和 `CalendarTaskAI-cli.exe`（附主控台的 CLI）
- 也可以在 Python 3.10+ 上從原始碼執行
- JSON 備份 / 還原，涵蓋設定（金鑰已遮蔽）、個人檔案、歷史紀錄、重複規則、範本，以及前後各 1 年（±1 年）的任務

**細節打磨**
- 淺色 + 深色主題，可從系統匣選單切換（Light / Dark / Follow System）
- 所有操作按鈕在兩種主題下都符合 WCAG AA 對比標準
- 支援高 DPI（在 4K 筆電上也很清晰）
- 日誌寫入 `%APPDATA%\CalendarTaskAI\logs\app.log`（輪替，1 MB × 5）

---

## 安裝

### 選項 A：預先建置的 Windows 執行檔

建議非開發者使用。

1. 前往 [Releases](https://github.com/chrisye96/CalendarTaskAI/releases) 頁面，下載 `CalendarTaskAI-vX.Y.Z.zip`（約 25 MB）。
2. 解壓縮到一個你自己管理的資料夾（例如 `C:\Apps\CalendarTaskAI`）。
3. 解壓縮後你會看到：
   - `CalendarTaskAI.exe`：GUI 啟動程式（不開主控台視窗）。日常使用就執行這個。
   - `CalendarTaskAI-cli.exe`：附主控台的 CLI 版本。用它執行 `today`、`add`、`next`、`backup` 等指令。
4. （選用）把 `CalendarTaskAI.exe` 釘選到工作列 / 傳送到開始功能表，或從系統匣選單啟用開機自動啟動。

### 選項 B：從原始碼執行

適用於 Windows 上的 Python 3.10+。

```powershell
git clone https://github.com/chrisye96/CalendarTaskAI.git
cd CalendarTaskAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

然後執行：

| 模式 | 指令 |
|------|---------|
| GUI（不開主控台） | `pythonw main.py` |
| GUI（開啟主控台，方便除錯） | `python main.py` |
| CLI | `python main.py <command>`（見 [CLI 模式](#cli-模式)） |

### 選項 C：自行建置執行檔

```powershell
pip install -r requirements-dev.txt
python build_release.py
```

會先執行測試套件，再產生 `dist/CalendarTaskAI-vX.Y.Z.zip`。也可以推送 `v[0-9]*` 標籤到 GitHub 來觸發發行工作流程，它會在乾淨的 Windows runner 上做同樣的事，並把 zip 以草稿形式附加到 GitHub Release。

---

## 首次執行設定

### GUI

首次啟動會顯示一個 Tkinter 精靈：

1. 從可捲動的清單中**選擇供應商**（新使用者預設為 Gemini；有免費額度）。
2. 按一下「Get a {provider} API key」連結，在瀏覽器中開啟該供應商的 API 金鑰頁面。
3. 把金鑰貼到遮罩輸入框中。
4. （建議）按一下 **Test**，發出一次很小的實際 API 呼叫，確認金鑰可用。
5. 按一下 **Save**。

金鑰只會儲存在你的電腦上，位置是 `%APPDATA%\CalendarTaskAI\data\config.json`。之後要修改，可以直接編輯該檔案，或從系統匣選單的 **Config** 開啟它。

### CLI

```powershell
python main.py config setup
```

以逐項提示的方式帶你填寫相同的欄位。按 Enter 保留目前的值，輸入 `q` 儲存並結束。

---

## 日常使用

### GUI 模式

1. 按 `Ctrl+Alt+Space`（或在系統匣圖示上按右鍵 → **Add Task**）。
2. 在浮動視窗中輸入任務。一行可以寫多個任務，用 `;`/`；`/`、` 分隔，或直接換行。
3. 按 `Ctrl+Enter`（或按一下 **Submit**）。
4. AI 分析輸入後，會顯示建議的分配結果，列出每個任務的日期。
5. 按一下 **Confirm** 寫入 DesktopCal，按 **Edit** 修改輸入，或按 **Cancel** 放棄。
6. （設定了 DeepSeek 時）確認畫面會多出兩個按鈕：**Re-run with DeepSeek-flash** 用來換個方式再試一次，**Re-run with DeepSeek Pro** 用於確實複雜的輸入。

需要讓 DesktopCal 重新載入（它在記憶體中的畫面不會自動更新）。你可以：
- 切換到其他月份再切回來，或手動重新啟動 DesktopCal；或者
- 在 `config.json` 中設定 `auto_restart_desktopcal: true`（預設關閉；注意：這會強制結束 DesktopCal，它其他面板中未儲存的內容會遺失）。

### CLI 模式

| 指令 | 用途 | 範例 |
|---------|---------|---------|
| `add [TEXT]` | 透過 AI 新增任務（未提供 TEXT 時從 stdin 讀取） | `python main.py add "明天买菜"` |
| `today` | 顯示今天的任務 | `python main.py today` |
| `next [N]` | 顯示未來 N 天的任務（預設 7 天） | `python main.py next 14` |
| `list [DATE]` | 顯示某個日期或日期範圍內的任務 | `python main.py list 2026-03-25` |
| `done KEYWORD` | 將符合的任務標記為已完成 | `python main.py done "买菜"` |
| `undone KEYWORD` | 取消已完成標記 | `python main.py undone "报告"` |
| `delete KEYWORD` | 刪除符合的任務 | `python main.py delete "取消的任务"` |
| `move KEYWORD DATE` | 將符合的任務移到 DATE | `python main.py move "会议" 2026-04-01` |
| `search KEYWORD` | 在所有日期中搜尋任務 | `python main.py search "复盘"` |
| `undo` | 復原最近新增的一批任務 | `python main.py undo` |
| `backup [--out FILE]` | 將完整狀態匯出為 JSON | `python main.py backup --out my-backup.json` |
| `restore FILE` | 從備份 JSON 還原 | `python main.py restore my-backup.json` |
| `export [--format md\|txt]` | 輸出某個日期範圍內的任務 | `python main.py export --start 2026-03-01 --end 2026-03-31` |
| `retry` | 重試待處理的失敗 AI 請求 | `python main.py retry` |
| `refresh` | 輸出讓 DesktopCal 重新載入畫面的操作說明 | `python main.py refresh` |
| `profile [view\|edit\|reset]` | 管理個人檔案 | `python main.py profile edit` |
| `config [show\|set\|setup]` | 管理設定 | `python main.py config show` |

---

## 系統匣選單

在系統匣圖示（一個 64×64 的方塊，馬卡龍淺藍底上寫著「CT」）上按右鍵，可以看到：

- **Add Task**：開啟輸入視窗（預設動作；按左鍵也可以）
- **Add from template ▶**：已儲存範本的子選單；選一個即可預先填入輸入視窗
- **Today's Tasks**：以訊息方塊列出今天未完成的任務
- **Undo last add**：復原最近新增的一批任務（沒有可復原的內容時會顯示為灰色）
- **Retry Pending**：重試離線快取中所有失敗的 AI 請求
- **Config**：用系統編輯器開啟 `config.json`
- **Profile**：用系統編輯器開啟個人檔案 `profile.md`
- **Theme ▶**：選擇主題，Light / Dark / Follow System（單選選單）
- **Auto Start**：開啟或關閉登入時自動啟動 CalendarTaskAI 的 Windows 登錄檔項目
- **Quit**：結束

---

## 設定

所有執行階段資料都位於 `%APPDATA%\CalendarTaskAI\` 下：

```
%APPDATA%\CalendarTaskAI\
├─ data\
│   ├─ config.json       （供應商金鑰、快速鍵、主題等）
│   ├─ profile.md        （你的工作習慣 + 排程規則）
│   ├─ history.json      （互動紀錄 + 行為分析）
│   ├─ pending.json      （等待重試的失敗 AI 請求）
│   ├─ recurring.json    （已登錄的重複規則）
│   ├─ templates.json    （首次啟動時寫入的 5 個內建範本 + 使用者新增的範本）
│   └─ last_op.json      （最近一批，供 Undo 使用）
└─ logs\
    └─ app.log           （輪替保存，1 MB × 5）
```

### `config.json` 參考

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

| 欄位 | 說明 |
|-------|-------------|
| `llm_provider` | 值為 `"gemini"`、`"openai"`、`"claude"`、`"grok"`、`"mistral"`、`"deepseek"`、`"kimi"`、`"qwen"`、`"glm"`、`"openrouter"` 其中之一。預設 Gemini。 |
| `<provider>_api_key` | 所選供應商的 BYOK 金鑰。除了傳給該供應商，絕不會離開你的電腦。只有目前使用的供應商需要金鑰；其他的可以留空。 |
| `gemini_model` | Gemini 模型的確切名稱。發生 404 會直接報錯（不會悄悄改用另一個 Gemini 模型）。 |
| `openai_model` | OpenAI 模型名稱。預設為 `gpt-4o`；常見的替代值有 `gpt-5`、`gpt-4o-mini`、`o4-mini`。 |
| `claude_model` | Anthropic 模型名稱。預設為 `claude-sonnet-4-6`。需要更強的推理能力時可改為 `claude-opus-4-5`，想要更快、更便宜的呼叫可改為 `claude-haiku-4-5`。 |
| `claude_max_tokens` | Anthropic API 要求必填。預設值 2048，用於日期分配綽綽有餘。 |
| `grok_model` | xAI 模型名稱。預設為 `grok-4`。SuperGrok-Heavy 使用者可在 `grok-4.3` 結束測試版後改用它。 |
| `mistral_model` | Mistral 模型名稱。預設為 `mistral-large-latest`（Mistral Large 3）。想要更便宜的呼叫可改為 `mistral-small-latest`。 |
| `deepseek_model_flash` / `_pro` | DeepSeek 的「fast」與「smart」兩個等級。輸入超過 `deepseek_pro_threshold` 時，應用程式會選用 pro。 |
| `deepseek_pro_threshold` | 未解析的任務數超過此值時，DeepSeek 會自動改用 pro 而非 flash。預設 5。 |
| `kimi_model` | Moonshot 的上下文長度等級：`moonshot-v1-8k` / `-32k` / `-128k`。預設 32k。 |
| `qwen_model` | Alibaba Qwen 模型。預設為 `qwen-plus`（均衡）。可改為 `qwen3-max`（旗艦）或 `qwen3.5-flash`（最便宜）。 |
| `qwen_endpoint` | DashScope 的 OpenAI 相容端點。預設使用中國大陸節點；國際使用者可改用 `dashscope-intl.aliyuncs.com`（新加坡）或 `dashscope-us.aliyuncs.com`。 |
| `glm_model` | Zhipu GLM 模型。預設為 `glm-4.6`。帳號取得權限後可改為 `glm-5` / `glm-5.1`。 |
| `openrouter_model` | OpenRouter 模型 id。預設為 `openrouter/auto`（由 OpenRouter 為每則提示詞挑選模型）。可改為特定 id，例如 `anthropic/claude-opus-4-7` 或 `meta-llama/llama-4-maverick`。 |
| `<provider>_endpoint` | OpenAI 相容 API / Anthropic API 的基礎 URL。只有在透過企業閘道或自架端點轉送時才需要修改。 |
| `hotkey` | 開啟輸入視窗的全域快速鍵（使用 [keyboard](https://github.com/boppreh/keyboard) 的語法）。 |
| `db_path` | DesktopCal 的 `calendar.db` 完整路徑。預設為 `%APPDATA%\CalendarTask\Db\calendar.db`，除非 DesktopCal 安裝在非標準位置，否則維持原樣即可。 |
| `auto_start` | Windows 登入時執行。可從系統匣選單切換。 |
| `retry_on_startup` | 每次啟動時自動重試失敗的 AI 請求。 |
| `auto_restart_desktopcal` | **預設關閉**。開啟後，寫入任務後會強制結束並重新啟動 DesktopCal（畫面會自動更新，但它其他面板中未儲存的內容可能會遺失）。 |
| `request_timeout_sec` | 每次 LLM API 呼叫的逾時時間。 |
| `rating_interval` | 每 N 次操作請你做一次滿意度評分。 |
| `theme` | `"light"` / `"dark"` / `"system"`。`"system"` 會跟隨 Windows 的應用程式主題。 |

---

## 輸入參考

### 日期提示

| 你輸入 | 解析為 |
|----------|-------------|
| `今天` `今日` `今晚` | 今天 |
| `明天` `明日` | 明天 |
| `后天` `大后天` | 後天 / 3 天後 |
| `下周` | 下週一 |
| `下周一` ~ `下周日` | 下週的週一/週二/.../週日 |
| `这周三` `这周末` | 本週三 / 本週六 |
| `周一` ~ `周日`, `星期一` ~ `星期天`, `礼拜一` ~ `礼拜天` | 接下來最近的那個星期幾 |
| `下个月` `这个月` `月初` `月底` | 下個月 1 日 / 本月 1 日 / 本月第一天或最後一天 |
| `3天后` `三天后` `2周后` `1个月后` | 相對位移（阿拉伯數字或中文數字皆可） |
| `2026年3月25日` `2026-03-25` `2026.03.25` `2026/03/25` | 完整的 ISO / 中文日期 |
| `3月25日` `3月25` `0325` `3.25` `3/25` `3-25` | 短日期（自動推斷年份；已過的日期順延到明年） |
| `today` `tonight` `tomorrow` `next week` `next monday` | 對應的英文寫法 |
| `in 3 days` `in 2 weeks` `end of month` | 英文相對日期 |

### 時間提示

時間前綴會以 `[HH:MM]` 或 `[HH:MM-HH:MM]` 的形式加在任務文字前。這部分完全由確定性解析器負責（LLM 不得自行編造時間，以免格式走樣）。

| 你輸入 | 結果 |
|----------|---------|
| `9点开会` | `[09:00] 开会` |
| `9点半开会` | `[09:30] 开会` |
| `9点45分会议` | `[09:45] 会议` |
| `上午9点开会` `下午3点开会` `晚上9点睡觉` `凌晨2点起床` `中午12点吃饭` | 依時段轉換為 24 小時制 |
| `9-10点 开会` `下午3-5点 讨论` | 中文時間範圍 |
| `9:00 daily standup` `3pm meeting` `9:00-10:30 review` `9-11am sprint` | 西式時間範圍，AM/PM |

可以組合：`明天9点开会` 解析為 date=明天，task=`[09:00] 开会`。

### 重複規則

| 你輸入 | 排定結果 |
|----------|---------------------|
| `每周一 健身房` | 未來 12 週的每週一排入「健身房」 |
| `每周一三五 健身` | 每週一 / 週三 / 週五 |
| `每周一、三、五 健身` | 以頓號分隔的等效寫法 |
| `每周三 上午10-11点 团队会议` | 每週三 `[10:00-11:00] 团队会议` |
| `每月15号 交房租` | 每月 15 日排入「交房租」 |
| `每月1日 报销` | 每月 1 日排入「报销」 |
| `every monday 9am standup` | 每週一 `[09:00] standup` |
| `every fri team review` | 每週五「team review」 |

特性：
- **預先展開約 12 週**。新產生的項目會顯示在確認畫面中；你可以取消整批。
- **規則只在確認時儲存**。取消的輸入不會在 `recurring.json` 中留下任何痕跡。
- **啟動時補齊**。每次啟動都會把滾動的 12 週視窗補滿。同一天內重複執行結果不變（冪等）。
- **不在支援範圍內**：隔週、每月日期範圍、「每隔一個週二」、完整的 cron 語法。如果你真的會用到其中某項，歡迎開 issue。

### 分隔符號行為

| 分隔符號 | 是否拆分？ |
|-----------|---------|
| 換行 | 是 |
| `;` `；`（英文 / 中文分號） | 是 |
| `、`（中文頓號） | 是 |
| `,` `，`（一般逗號） | **否**（會把「买菜, 然后洗衣服」這樣的句子拆壞） |
| 空格 | **否**（會把「完成项目报告」這樣的詞組拆開） |

---

## 個人檔案

個人檔案位於 `%APPDATA%\CalendarTaskAI\data\profile.md`，每次呼叫 LLM 都會放進提示詞。首次啟動時會產生一份範本：

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

其中 **Scheduling Rules** 這一節的影響最直接：為未解析的任務挑選日期時，LLM 會把其中每一條都當成硬性限制。可從系統匣選單 **Profile** 或 `python main.py profile edit` 編輯個人檔案。

---

## 主題

內建兩套配色：馬卡龍淺藍的淺色主題，以及降低飽和度的藍色深色主題。

- **Light**（淺色）：粉彩底色，淺藍強調色，深海軍藍主要文字。
- **Dark**（深色）：帶藍調的石板灰底色，降低飽和度的淺藍強調色，米白主要文字。操作按鈕在較淺的強調色上使用深色文字，以符合 WCAG AA 對比標準（淺藍底配白字達不到 AA）。

從系統匣選單 **Theme ▶ Light / Dark / Follow System** 切換主題。「Follow System」選項會讀取 Windows 登錄檔值 `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`。

切換會在你下次開啟輸入視窗或精靈時生效。如果切換時某個視窗正在顯示，它會維持原樣（免得打斷你手上的工作），下次開啟時再以新配色重建。

---

## 備份與還原

```powershell
python main.py backup --out my-backup.json
python main.py restore my-backup.json
```

備份內容包括：
- `config.json`（API 金鑰會被替換為 `*** REDACTED ***`）
- `profile.md`
- `history.json`
- `templates.json`
- `recurring.json`
- 日曆資料庫中前後各 1 年（±1 年）的任務

還原會覆寫 `profile.md`、`history.json`、`templates.json` 和 `recurring.json`。任務會**附加**到資料庫中（如果在已有資料的資料庫上還原，可能會出現重複）。API 金鑰沿用你現有 `config.json` 中的值；備份絕不包含真實金鑰，即使是用 `--overwrite-config` 建立的也一樣。

---

## DesktopCal 整合原理

CalendarTaskAI 直接寫入 DesktopCal 的 SQLite 資料庫，位置在 `%APPDATA%\CalendarTask\Db\calendar.db`。

**資料表結構**：
- 資料表：`item_table`
- 鍵欄位：`it_unique_id`，格式為 `dkcal_mdays_YYYYMMDD`（例如 `dkcal_mdays_20260325`）
- 內容欄位：`it_content`。同一天的任務存成一個字串，以 `\r\n` 分隔。已完成的任務會加上 `[+]` 前綴。

**重新整理**：DesktopCal 會把顯示內容快取在記憶體中。寫入之後它不會察覺，直到你在 DesktopCal 中切換到其他月份再切回來。設定 `auto_restart_desktopcal: true` 可讓 CalendarTaskAI 在每次寫入後強制重新啟動 DesktopCal（注意：DesktopCal 其他面板中未儲存的內容會遺失）。

---

## 架構

寫給好奇的開發者。約 25 個模組、6 000 行正式環境 Python 程式碼；197 個單元測試。

### 處理流程

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

### 主要模組

| 模組 | 用途 |
|--------|---------|
| `main.py` | 進入點；分流 CLI 與 GUI，把帶 CLI 參數啟動的 GUI exe 轉交給 CLI exe |
| `cli.py` | 基於 Click 的 CLI（add/today/next/done/undo/backup/restore/...） |
| `ui.py` | Tkinter 浮動輸入視窗，跟隨主題 |
| `tray.py` | pystray 圖示 + 選單（範本子選單、主題子選單、開機自動啟動、復原） |
| `setup_wizard.py` | 首次執行的 BYOK Tkinter 精靈（供應商選擇、遮罩金鑰輸入框、Test 按鈕） |
| `task_parser.py` | 拆分多任務輸入，執行日期擷取（中文 + 英文） |
| `time_parser.py` | 一天中時間的擷取（24 小時制、12 小時制 + AM/PM、帶時段的中文、時間範圍） |
| `recurring.py` | 每週 / 每月規則解析 + 預先展開 12 週 + 啟動時補齊 |
| `ai_client.py` | 跨供應商協調：指定供應商、自動備援、建構提示詞 |
| `providers/` | `LLMProvider` 抽象基底類別 + `OpenAICompatibleProvider` 基底類別 + 10 個具體供應商（Gemini / OpenAI / Claude / Grok / Mistral / DeepSeek / Kimi / Qwen / GLM / OpenRouter）+ 工廠 |
| `calendar_db.py` | 依 DesktopCal 資料表結構進行 SQLite 讀寫；LIKE 跳脫、鎖定重試 |
| `last_op.py` | 記錄最近新增的一批任務，用於單步復原 |
| `templates.py` | 5 個內建範本 + 使用者自訂；系統匣子選單 |
| `backup.py` | 帶 schema 版本號的完整狀態 JSON 匯出 / 還原 |
| `theme.py` | 淺色 + 深色配色 token；解析系統偏好設定 |
| `history.py` | 互動紀錄 + 為提示詞產生行為模式摘要 |
| `retry_queue.py` | 失敗 AI 請求的離線快取；於啟動時或透過 CLI 重試 |
| `config_manager.py` | `config.json` 載入 / 儲存；互動式設定 |
| `profile_manager.py` | `profile.md` 載入 / 編輯 |
| `logger.py` | `%APPDATA%\CalendarTaskAI\logs\` 下的輪替日誌檔案處理常式 |
| `constants.py` | 集中管理的路徑 + DEFAULT_CONFIG |

---

## 疑難排解

**API 金鑰錯誤 / 「Not configured」** 執行 `python main.py config setup`（或開啟 GUI 使用精靈），重新輸入金鑰。

**快速鍵沒有作用**
- 確認已安裝 `keyboard`（`pip show keyboard`）。
- 試著以系統管理員身分執行（Windows 會阻止某些應用程式在沒有系統管理員權限時註冊全域快速鍵）。
- 在 `config.json` 中修改快速鍵：`"hotkey": "ctrl+shift+t"`。

**資料庫遭鎖定** 暫時關閉 DesktopCal；應用程式會重試 3 次，每次退避 0.5 秒，但在其他處理程序持有獨占鎖定時無法寫入。

**任務已寫入，但 DesktopCal 沒有顯示** DesktopCal 會快取記憶體中的畫面。切換到其他月份再切回來。或者設定 `auto_restart_desktopcal: true`。

**系統匣圖示沒有出現** 必須安裝 Pillow + pystray（`pip install pillow pystray`）。展開系統匣的隱藏圖示區域；Windows 常會把新圖示隱藏起來。

**API 速率限制 / 配額用盡** 失敗的請求會儲存到 `pending.json`，並在下次啟動時重試。也可以改用其他供應商或等配額恢復後，執行 `python main.py retry`。

**打包的 exe 無法啟動** 在 `CalendarTaskAI.exe` 上按右鍵 → 內容 → 如果有「解除封鎖」，請勾選（Windows 對下載檔案的來源保護）。確認 Windows 版本為 10 或更新版本。

**日誌在哪裡？** `%APPDATA%\CalendarTaskAI\logs\app.log`。達到 1 MB 時輪替，保留 5 份備份。

---

## 參與貢獻

歡迎提交 Pull Request。儲存庫遵循 Conventional Commits 規範（`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`），每個發行標籤都會執行完整的測試套件。

執行測試：

```powershell
pip install -r requirements-dev.txt
pytest tests/
```

在本機建置發行版：

```powershell
python build_release.py
```

---

## 授權與致謝

MIT。請參閱 [LICENSE](LICENSE)。

CalendarTaskAI 是 DesktopCal 的**非官方**外掛，與 DesktopCal 作者沒有關聯，也未獲其認可。

基於以下專案打造：
- [DesktopCal](https://www.desktopcal.com/)，本外掛寫入的日曆應用程式。
- 它支援的十家 LLM 供應商：Google Gemini、OpenAI、Anthropic Claude、xAI Grok、Mistral AI、DeepSeek、Moonshot Kimi、Alibaba Qwen、Zhipu GLM 和 OpenRouter。
- 負責主要工作的開源相依套件：pystray、Pillow、keyboard、click、google-genai、PyInstaller。

> 本文由英文版機器翻譯而來，尚未經過母語人士逐行審閱。如有出入，以 [English](README.md) 版本為準。
