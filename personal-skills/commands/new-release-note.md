---
description: "Generate Android release notes from Jira fixVersion, create git tag, and publish GitHub release. Use when the user wants to create, build, or generate release notes (e.g. '我想要建立release note', '幫我做release note', 'create release note', 'generate release notes')."
argument-hint: "<版本號，例：2.104.0>"
---

# Create Release

根據 Jira fixVersion 的 tickets 產生 release notes，建立 git tag，並發布 GitHub release。

**版本號：** `$ARGUMENTS`

---

## Step 1 — 確認版本號

若 `$ARGUMENTS` 有提供版本號（如 `2.104.0`），直接使用。否則詢問使用者。

---

## Step 2 — 確認 fixVersion 並抓取 tickets

**2a. 找出符合版本號的 fixVersions**

用 Atlassian MCP 列出專案所有版本，過濾名稱包含 `{version}` 的項目：
```
cloudId: {{JIRA_WORKSPACE_ID}}
使用 Jira versions API：GET /rest/api/3/project/{{JIRA_PROJECT_KEY}}/versions
過濾：name 包含 {version}
```

- 若只有一個 → 直接使用
- 若有多個 → 列出讓使用者選，例如：
  ```
  找到多個符合 {version} 的版本，請選擇：
  1. Android 2.104.0
  2. iOS 2.104.0
  ```
- 若查無結果 → 告知使用者並停止

**2b. 抓取該 fixVersion 的 tickets**

```
cloudId: {{JIRA_WORKSPACE_ID}}
jql: project = {{JIRA_PROJECT_KEY}} AND fixVersion = "{selectedVersion}" ORDER BY issuetype ASC
fields: ["summary", "issuetype", "parent", "description", "fixVersions"]
maxResults: 100
```

從任一 ticket 的 `fixVersions[0].id` 取得 version ID，組成 Jira release report 連結：
```
{{JIRA_BASE_URL}}/projects/{{JIRA_PROJECT_KEY}}/versions/{versionId}/tab/release-report-all-issues
```

---

## Step 3 — 分組 tickets

依以下規則分類，**互斥且依序判斷**：

**1. Epic section（issuetype = "Epic" 或 "大型工作"）**
- 每個 Epic 獨立成一個 section
- Section 標題：Epic summary，去掉平台前綴（如 `[Android]`、`[iOS]`）
- 從 Epic description 的 `<custom data-type="smartlink">` 或任何 `atlassian.net/wiki/` URL 提取 Confluence 連結

**2. Bug section（issuetype = "Bug" 或 "漏洞"）**

**3. Modularization section**
- issuetype 非 Epic / Bug 類（見上方定義）
- summary 含以下任一關鍵字（不分大小寫）：`Modularize`、`Modularization`、`Module`

**4. New feature section**
- issuetype 非 Epic / Bug 類（見上方定義）
- 非 Modularization 關鍵字
- `parent` 欄位不指向本次 fixVersion 裡的任何 Epic（指向則略過）

**5. 略過**
- `parent` 是本次 fixVersion 裡某個 Epic 的 child tasks

---

## Step 4 — 產生 release note 草稿

格式：

```markdown
## {Epic Summary}

{{JIRA_BASE_URL}}/browse/{epic-key}
{confluence URL（若有，否則省略）}

## New feature
[{{JIRA_PROJECT_KEY}}-XXXX]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX) {summary}
...

## Bug Fixes
[{{JIRA_PROJECT_KEY}}-XXXX]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX) {summary}
...

## Modularization
[{{JIRA_PROJECT_KEY}}-XXXX]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX) {summary}
...

## Version Stack
App: 待補
Database Schema: 待補
{{JIRA_BASE_URL}}/projects/{{JIRA_PROJECT_KEY}}/versions/{versionId}/tab/release-report-all-issues
```

規則：
- 沒有 Epic → 直接從 New feature 開始
- 某個 section 完全沒有 ticket → 整個 section 省略不輸出
- ticket summary 保留原文，不修改

顯示草稿後問使用者：
> 「Release note 草稿如上，有需要調整嗎？說 **ok** 繼續，或告訴我要改哪裡。」

**等使用者確認後再繼續。**

---

## Step 5 — 建立 git tag

```bash
git checkout master
git pull
git tag v{version}
git push origin v{version}
```

確認 tag 建立成功後繼續。

---

## Step 6 — 建立 GitHub release

```bash
gh release create v{version} \
  --title "Release v{version}" \
  --notes "{release note content}" \
  --draft
```

回傳 GitHub release URL。

---

## 完成

```
✓ Tag      : v{version}
✓ Release  : {GitHub release URL}

提醒：如有平台產物需手動上傳至 GitHub release（例如 Android APK、mapping.txt）。
```
