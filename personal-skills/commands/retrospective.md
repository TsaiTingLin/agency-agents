---
description: "Review recorded session issues and propose updates to skills, agents, or CLAUDE.md. Use when the user says 總結檢討, 總結反省, 看一下問題, 有什麼要改的, or similar."
argument-hint: ""
---

# Retrospective — 總結反省

讀取本次 session 記錄的問題，分析哪些值得更新系統設定。

---

## Step 1 — 讀取問題記錄

```bash
python3 ~/.claude/tools/mentor_memory.py read-issues
```

若輸出為空 → 告知使用者「本次 session 沒有記錄任何問題」，結束。

---

## Step 2 — 分類問題

逐行分析每個問題的「解法」欄，判斷性質：

| 性質 | 說明 | 行動 |
|---|---|---|
| 一次性問題 | 只在這個情境發生，不會再犯 | 略過 |
| 流程缺失 | skill 步驟沒有涵蓋到 | 提案更新對應 skill |
| 判斷原則 | Claude 的判斷方向不對 | 提案更新 agent 或 CLAUDE.md |
| 工具問題 | hook / MCP 設計有缺陷 | 提案更新 tools/ 或 settings.json |

---

## Step 3 — 提案

列出所有「值得更新」的項目，格式：

```
## 建議更新

1. **[skill/agent/CLAUDE.md]** `<檔案名稱>`
   問題：<發生了什麼>
   建議改法：<具體要加什麼或改什麼>

2. ...
```

詢問使用者：「以上哪些要現在更新？」

---

## Step 4 — 執行更新

等使用者確認後，逐項執行：

- **Skill 更新** → 直接編輯 `~/.claude/commands/<skill>.md`
- **Agent 更新** → 編輯 `~/agency-agents/engineering/<agent>.md`，完成後執行：
  ```bash
  cd ~/agency-agents && ./scripts/install.sh --tool claude-code
  ```
- **CLAUDE.md 更新** → 直接編輯 `~/.claude/CLAUDE.md`
- **settings.json 更新** → 直接編輯 `~/.claude/settings.json`

每項更新完成後告知使用者。

---

## Step 5 — 收尾

```
已完成 N 項更新。
可以關閉 terminal，session 記憶會自動清除。
```
