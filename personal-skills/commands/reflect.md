---
description: "Record an issue from the current conversation into session memory. Use when the user says 檢討一下, 記錄一下, 這個要記起來, or similar."
argument-hint: "[問題描述（可選）]"
---

# Reflect — 記錄問題

從當前對話脈絡判斷剛才發生了什麼問題，記錄進 session 記憶。

## Step 1 — 判斷問題

從對話脈絡找出最近發生的問題或值得記錄的事：
- 什麼做錯了？
- 為什麼發生？
- 怎麼解決或應該怎麼做？

若 `$ARGUMENTS` 有提供描述，直接用它作為問題摘要。

## Step 2 — 記錄

```bash
python3 ~/.claude/tools/mentor_memory.py log-issue '<問題>' '<發生原因>' '<解法>'
```

## Step 3 — 回報

用一句話告訴使用者記錄了什麼：

```
已記錄：<問題摘要>
```
