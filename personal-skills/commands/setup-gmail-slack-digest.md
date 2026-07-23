---
name: setup-gmail-slack-digest
description: Set up, repair, test, pause, resume, or update the Gmail → Slack unread-mail digest on Claude Code or Codex. Dynamically choose the host-native workflow: Claude MCP plus launchd, or Codex Gmail/Slack connectors plus Codex automation. Use for Gmail unread digests, Gmail-to-Slack memos, knowledge-mail classification, or /setup-gmail-slack-digest.
---

# Setup: Gmail → Slack Daily Digest Automation

Sets up (or repairs) the full local automation that, on a schedule confirmed with the user (time + frequency), checks the target account's unread Gmail, categorizes it, posts a digest to their Slack self-DM, and — if they reacted with any emoji on the previous digest — marks those shown messages as read.

**This skill source file must never contain a hardcoded email, Slack user ID, or person's name.** Which account this runs for is resolved fresh every time it's invoked (Step 1) — never assume it's the same person as a previous run. The only things baked in are file paths under the current OS user's home directory (`~/.claude/...`, `~/Library/LaunchAgents/...`), which are fine since they never leave this machine. The *generated* prompt file (Step 7) and plist do contain the resolved email/Slack ID — that's expected and correct, since they're local, per-machine artifacts, not something committed or shared.

State lives entirely **inside Slack** — as a thread reply under each digest message — not in a local file. This was a deliberate redesign: an earlier version stored state as a local JSON file, but `~/.claude/` is treated as a sensitive path by the permission system and non-interactive (`claude -p`) writes to it are silently blocked even with an explicit `permissions.allow` rule (confirmed by direct testing). Moving state into Slack itself avoids that wall entirely and removes any local-file dependency.

## Choose the runtime first

Detect which host is executing this skill before taking setup actions:

- **Codex:** if running in Codex or Codex automation tools are available, follow **Codex native workflow** below. Gmail/Slack connector availability does not affect this routing decision; the Codex workflow handles missing connections. Do not run the Claude prerequisites or Steps 0–10.
- **Claude Code:** if Claude plugin/MCP tools are available, follow the existing Claude workflow beginning at **Prerequisites**.
- If the host is unclear, ask which runtime the user wants to configure. Never configure both unless the user explicitly requests both.

The two workflows share the same product behavior, knowledge classification preferences, Slack self-DM format, reaction-to-mark-read rule, and Slack thread state format.

## Prerequisites (check before Step 0)

This skill configures and schedules the automation; a few underlying tools need to exist first. Where there's a standard, deterministic install command, run it automatically. Where installing correctly requires a judgment call this skill can't make safely on its own, stop and ask the user instead of guessing.

- **macOS only.** Scheduling uses `launchd`/`launchctl`. There's no equivalent step for Linux (systemd timers) or Windows (Task Scheduler) in this skill — nothing to auto-install here; if the user isn't on macOS, say so instead of attempting Step 8.
- **Slack plugin** (`slack@claude-plugins-official`) — Step 6 only handles *authenticating* it, not installing it, so check first: `claude plugin list | grep slack`. If missing, **auto-install** with `claude plugin install slack@claude-plugins-official` — this is a standard, deterministic command, no judgment call needed. After installing, tell the user a reload/restart may be needed (e.g. `/reload-plugins` or restart the session) before `mcp__plugin_slack_slack__*` tools appear.
- **`python3` on PATH** — used in Appendix A's credential-transplant script. If missing and Homebrew is available, `brew install python3` is standard enough to run, but confirm with the user first since it's a real system package install, not just a Claude Code plugin.
- **`workspace-gmail` MCP server registered** in `~/.claude.json` under `mcpServers`. This skill only edits its existing `args`/`env` (Step 4, Appendix A) — it does not add the server entry from scratch, because that requires knowing which underlying Gmail MCP implementation to point it at and what OAuth client to wire up (Appendix A). If `grep -A6 '"workspace-gmail"' ~/.claude.json` finds nothing at all, **stop and ask** the user how they'd like to add it rather than guessing a command/args shape.
- **The `workspace-mcp` binary itself** (the command the MCP entry's `command` field points at, typically a Python venv). If the MCP entry exists but that path doesn't actually exist on disk, **stop and ask** — where to fetch/install it from is a judgment call, not a fixed command.
- **`claude` CLI itself** — if this skill is running at all, `claude` obviously already works; the only thing to resolve (not install) is its absolute path via `which claude`, needed because `launchd` doesn't always inherit the same PATH as an interactive shell (see Step 8).

## Step 0 — Check current state first (idempotent)

Don't redo completed steps. Check:
- `grep -A6 '"workspace-gmail"' ~/.claude.json` — does `args` already lack `--read-only`?
- `ToolSearch select:mcp__workspace-gmail__batch_modify_gmail_message_labels` — already loaded?
- `ToolSearch select:mcp__plugin_slack_slack__slack_send_message` — Slack already authenticated?
- `test -f ~/.claude/scripts/gmail-slack-digest-prompt.txt` — if it exists, `grep` it for the `user_google_email=` and `channel_id=` values already baked in from a prior run; show these to the user in Step 1 as "目前設定的帳號是 X" for confirm/change, rather than re-asking blind.
- `test -f ~/Library/LaunchAgents/com.local.gmail-slack-digest.plist`
- `launchctl list | grep com.local.gmail-slack-digest` — already loaded?

Jump straight to whichever step is still needed.

## Step 1 — Resolve identity: which account is this for?

Never hardcode or assume an email/Slack ID — resolve them fresh each run:

1. If Step 0 found an existing prompt file with a previously-configured email, tell the user what it is and ask whether to keep it or switch to a different account. Otherwise ask directly: "這個自動化要接哪個 Google Workspace 帳號的 Gmail？" → call this `<gmail-account>`.
2. Once Slack is authenticated (Step 6 may need to run first if it isn't yet), call `mcp__plugin_slack_slack__slack_search_users` with `query=<gmail-account>` to resolve the matching Slack **User ID** → call this `<slack-user-id>`. If it doesn't resolve to exactly one user, show the candidates and ask the user to confirm which one.

Hold onto `<gmail-account>` and `<slack-user-id>` — every later step and the generated prompt file substitute these in literally. Do not write the literal example values from this skill's own documentation (there shouldn't be any) — always use what you resolved this run.

## Step 2 — Confirm what counts as 📚 知識相關 (knowledge-related)

Never hardcode a fixed definition or a fixed priority-topic list — these are personal preference and must be reconfirmed (or explicitly kept) every time, same treatment as the schedule in Step 3.

Before asking for preferences, explain the feature in simple, conversational language:

> 這個功能會把 Gmail 未讀信分成三類，再傳到你自己的 Slack 私訊，讓你快速看到重點，也方便之後回來查看。接下來想請你選哪些信算「知識相關」、一天最多顯示幾封，以及哪些主題要優先。

Do not explain OAuth, account permissions, scheduling, or implementation details here. Ask only one question at a time. Prefer the host's interactive choice UI; if unavailable, show short numbered choices. Use free-form questions only for a custom option.

If `~/.claude/scripts/gmail-slack-digest-prompt.txt` already exists, extract its current STEP 3 categorization rule and cap line, show the user in plain language what's currently configured (e.g. "目前知識相關涵蓋：技術電子報、研討會通知；上限 3 封；優先主題：Android/KMP/CMP/Claude AI"), and ask whether to keep it or change it. If they want to keep it, skip straight to Step 3.

Otherwise ask the following questions one at a time (via AskUserQuestion):
1. **哪些信要放進 📚 知識相關？**（multiSelect） — offer: 技術／工程電子報、研討會／課程、產業趨勢／研究報告、公司內部教育訓練, plus "Other". Whatever they pick becomes `<knowledge-criteria>`.
2. **顯示上限要幾封？** — options like `3`（推薦）, `5`, 不限, plus "Other" for a custom number. This becomes `<knowledge-cap>`.
3. **超過上限時，優先顯示哪些主題？** — options: 沿用一組常見預設（可在對話中列出幾個例子讓使用者確認，例如 "Android engineering / KMP / CMP / Claude AI" 僅供參考，不要假設使用者一定要選這個）, or "Other" to type their own topic list, ranked by priority. This becomes `<priority-topics>`.

Whenever a type is excluded or its destination is unclear, ask:

> 這類信要放哪一類？

Offer exactly these choices: `🔴 需要處理`, `📚 知識相關`, `🟢 一般通知`.

Hold onto `<knowledge-criteria>`, `<knowledge-cap>`, `<priority-topics>` — Step 7's prompt-file template substitutes these in.

## Step 3 — Confirm trigger time and frequency

Never assume a schedule — always ask first, even on a repair run.

If `~/Library/LaunchAgents/com.local.gmail-slack-digest.plist` already exists, read its `StartCalendarInterval` and show the user the current schedule in plain language (e.g. "現在排的是每天 11:00"), then ask whether to keep it or change it. If they want to keep it, skip straight to Step 4.

Otherwise, ask (via AskUserQuestion, two questions):
1. **Trigger time** — what local time should it run? (Options like `09:00`, `11:00`, `18:00`, plus "Other" for a custom `HH:MM`.)
2. **Frequency** — every day, weekdays only (Mon–Fri), or custom weekday selection?

Confirm the system timezone (`readlink /etc/localtime`) before treating the answer as local time — `launchd`'s `StartCalendarInterval` fires on system local time, not UTC. If it's not what you'd expect, flag it to the user before assuming the hour lines up with what they meant.

Hold onto the resolved `Hour`/`Minute` (and weekday list if not "every day") — Step 8 needs it to build `StartCalendarInterval`:
- **Every day**: a single dict `{Hour, Minute}`.
- **Weekdays only / custom days**: an array of dicts, one per selected weekday, each `{Hour, Minute, Weekday}` (`Weekday`: 0 or 7=Sunday, 1=Monday, ... 6=Saturday).

## Step 4 — workspace-gmail: minimum-scope mode via `--permissions`

**Checkpoint before touching workspace-gmail:** Steps 1–2 just resolved `<gmail-account>`, `<slack-user-id>`, `<knowledge-criteria>`, `<knowledge-cap>`, and `<priority-topics>` — but none of that is on disk yet (Step 7 normally writes the prompt file much later). If `workspace-gmail` turns out not to exist in `mcpServers` at all, this step falls through to Appendix A, which creates a brand-new server entry — and per the note below, that forces a full session restart with no memory of this conversation. So: if the `workspace-gmail` entry doesn't exist yet, write the Step 7 prompt file **now**, using today's resolved values (the template doesn't depend on Steps 5/6 having run yet). That way, if a restart becomes necessary, the fresh session's Step 0 check finds the file and skips straight back to re-confirming Step 1/2 instead of re-asking from scratch. (If `workspace-gmail` already exists — the common repair-run case — skip this checkpoint; Step 7 will write the file at its normal point.)

The underlying server (`workspace-mcp`, https://github.com/taylorwilsdon/google_workspace_mcp) has a native flag for exactly this — don't remove `--read-only` and rely on trimming the OAuth consent URL by hand; use its own granular permission system instead, confirmed straight from its `--help` output and source (`auth/permissions.py`):

```
--permissions SERVICE:LEVEL [SERVICE:LEVEL ...]
    Gmail levels: readonly, organize, drafts, send, full (cumulative).
    Mutually exclusive with --read-only and --tools.
```

`gmail:organize` maps in source to exactly `[GMAIL_LABELS_SCOPE, GMAIL_MODIFY_SCOPE]` — i.e. read + modify-labels (which is what "mark as read" needs, since that's just removing the UNREAD label) and nothing beyond that (no send, no compose, no settings). This is the right level for this automation.

Read `~/.claude.json`, find `mcpServers["workspace-gmail"].args`. Set it to exactly:
```json
["--single-user", "--permissions", "gmail:organize"]
```
(Note `--permissions` replaces `--tools`/`--read-only` entirely — don't combine them, the flag is documented as mutually exclusive with both.)

If the `workspace-gmail` entry doesn't exist in `mcpServers` at all yet, this is a judgment call per the Prerequisites section — stop and ask the user how to proceed (do they have a prior config to restore, or are they starting fresh via Appendix A) rather than fabricating a full entry including OAuth env vars from nothing.

Tell the user the config changed and ask them to reconnect. **These are two different situations — don't conflate them:**
- If `workspace-gmail` already existed and you only edited its `args` (the common repair-run case), `/mcp` reconnect is normally enough.
- If you just created the `workspace-gmail` entry from scratch via Appendix A, `/mcp` reconnect does **not** work — confirmed by direct testing (after `/mcp`, `ToolSearch` still didn't find the tool in the same session; a brand-new terminal/session started after the edit saw it immediately). A brand-new `mcpServers` entry is only picked up by a fresh `claude` process. In this case, tell the user plainly that this session can't pick it up on its own and they need to either continue in a new terminal/session, or fully restart this one — and remind them the checkpoint above already saved Steps 1–2's answers to the prompt file, so the fresh session's Step 0 will recover them instead of re-asking from zero.

Wait for their confirmation, then verify via `ToolSearch select:mcp__workspace-gmail__batch_modify_gmail_message_labels` that the modify tool is now loaded before continuing.

If `mcp__workspace-gmail__start_google_auth` (or any `mcp__workspace-gmail__*` tool) isn't available at all — not even in read-only form — the OAuth client credentials themselves may not exist yet. See **Appendix A** at the bottom of this file for the one-time Google Cloud Console setup, then come back here.

## Step 5 — Google OAuth

Call `mcp__workspace-gmail__start_google_auth` with `service_name=gmail`, `user_google_email=<gmail-account>` (the value resolved in Step 1).

Because Step 4 already configured `--permissions gmail:organize` on the server itself, the returned URL's `scope=` param should already be minimal (just `openid`, `userinfo.email`, `userinfo.profile`, `gmail.labels`, `gmail.modify`) — **no manual trimming needed this time**. Just hand the user the URL as-is and wait for confirmation.

If authorization fails for some reason, call `start_google_auth` again fresh (the old `state`/`code_challenge` can't be reused after a failed attempt) — but there's no "full scope" fallback to reach for anymore; if it keeps failing, the problem is elsewhere (check the OAuth client's consent screen config in Appendix A, not the scope list).

## Step 6 — Slack plugin auth

If `mcp__plugin_slack_slack__slack_send_message` isn't available via ToolSearch, call `mcp__plugin_slack_slack__authenticate`. Its default scope list includes some write scopes beyond DM use (typically `channels:write`, `groups:write`, `canvases:write`, `reactions:write`) — trim those out of the returned URL's `scope=` param. Keep everything else, especially `chat:write`, `im:write`, `mpim:write`, and all `search:read.*` / `*:read` / `*:history` scopes — those are needed for reading content, reading the previous digest's thread, and sending the DM.

Same fallback as Step 5: if the trimmed URL fails, call `authenticate` again fresh and hand over the untrimmed URL. Wait for confirmation.

Once authenticated, if `<slack-user-id>` wasn't resolved yet in Step 1 (because Slack wasn't authenticated at the time), do it now via `slack_search_users`.

## Step 7 — Write the prompt file

Create `~/.claude/scripts/` and `~/.claude/logs/` if missing.

Write this content to `~/.claude/scripts/gmail-slack-digest-prompt.txt`, substituting the real `<gmail-account>` and `<slack-user-id>` resolved in Step 1, and `<knowledge-criteria>` / `<knowledge-cap>` / `<priority-topics>` resolved in Step 2, everywhere they appear below (this generated file is local-only, so baking in the real values here is correct and expected):

```
You are running as a non-interactive daily automation for <gmail-account>. Do not ask questions — follow these steps exactly.

Slack self-DM channel_id: <slack-user-id>
State is stored IN Slack itself (as a thread reply under the previous digest) — there is no local state file.

STEP 1 — Find the previous digest and check for a reaction:
1. Call mcp__plugin_slack_slack__slack_read_channel with channel_id=<slack-user-id>, limit=20.
2. Find the most recent message whose text starts with "📧 Gmail 未讀信件整理" — that is the previous digest. If none exists (first run ever), skip straight to Step 2.
3. Call mcp__plugin_slack_slack__slack_get_reactions on that message's ts.
4. If it has zero reactions: do nothing further for this step.
5. If it has one or more reactions (any emoji counts): call mcp__plugin_slack_slack__slack_read_thread on that message's ts to get its replies. Find the reply whose text starts with "🔧 automation-state" — it contains a fenced ```json code block with {"message_ids": ["...", ...]}. Parse that array (these are only the messages that were actually SHOWN in that digest — see Step 3's cap on 知識相關 for why it's not necessarily every unread message that existed then).
6. Call mcp__workspace-gmail__batch_modify_gmail_message_labels for user_google_email=<gmail-account> to remove the UNREAD label from every id in that array (mark them read). Then send a short new thread reply via mcp__plugin_slack_slack__slack_send_message (channel_id=<slack-user-id>, thread_ts=that message_ts) saying how many messages were marked as read.

STEP 2 — Fetch all currently unread mail:
Call mcp__workspace-gmail__search_gmail_messages with user_google_email=<gmail-account>, query="is:unread", page_size=100 (paginate with page_token if more exist). This intentionally does NOT restrict to in:inbox — pick up unread mail under any label/category (Updates, Forums, custom labels, etc), not just the inbox view. Collect all message_ids.

If there are zero unread messages, just post "📧 Gmail 未讀信件整理 — 目前 0 封未讀" to <slack-user-id> and stop (no thread-state reply needed since there's nothing to mark read later).

STEP 3 — Categorize:
Call mcp__workspace-gmail__get_gmail_messages_content_batch (format=metadata is enough unless a subject is ambiguous, then fetch that one with format=full) for all collected ids. Sort each message into exactly one of:
- 🔴 需要處理 — sender explicitly needs the account owner to act/reply/review (e.g. GitHub PR requesting their review, Jira ticket assigned to them needing action, "Action required" notices from Google Play/Firebase that affect a real decision, anything addressed to them expecting a reply).
- 📚 知識相關 — <knowledge-criteria>. Do NOT put anything explicitly excluded from this definition here — those go in 一般通知.
- 🟢 一般通知 — everything else automated/informational that needs no reply (form submitted/signed/approved notices, HR announcements, leave lists, test-build-ready notifications, clock-in anomaly notices, etc).

Cap on 📚 知識相關: if more than <knowledge-cap> messages land in this category, only SHOW the top <knowledge-cap> most relevant to these priority topics, in this priority order: <priority-topics>. The remaining 知識相關 messages are NOT shown today and stay unread — they'll be reconsidered (and re-ranked) on a future run so they get read gradually instead of all at once. Do not silently drop them from existence — just don't display or mark them this round. (If `<knowledge-cap>` is "不限"/no cap, show all 知識相關 messages and skip this paragraph's capping logic entirely.)

STEP 4 — Post the digest to Slack:
Compose one Traditional Chinese message in this format and send it with mcp__plugin_slack_slack__slack_send_message to channel_id=<slack-user-id>:

📧 **Gmail 未讀信件整理（今天日期）— 共 N 封未讀**

**🔴 需要處理（N）**
- bullet list, one line per item or group, with the Gmail web link

**📚 知識相關（顯示 N／共 M 封，其餘 M-N 封之後慢慢列出）**
- bullet list for only the shown items (capped at <knowledge-cap>, or all of them if <knowledge-cap> is "不限"), one line each, with the Gmail web link and a one-phrase reason it's relevant

**🟢 一般通知（N）**
- grouped bullet summary (group identical subjects with counts, like "表單核准通知：9 封")

Capture the returned message_ts from the send call — you need it for Step 5.

STEP 5 — Persist state as a thread reply:
Build "shown_ids" = ALL 🔴需要處理 ids + ALL 🟢一般通知 ids + ONLY the 📚知識相關 ids that were actually shown in Step 4 (exclude any 知識相關 messages that were capped/not shown per the <knowledge-cap> rule).

Call mcp__plugin_slack_slack__slack_send_message with channel_id=<slack-user-id>, thread_ts=<the digest message_ts from Step 4>, and message text formatted exactly like:

🔧 automation-state — please don't delete this reply, it's read by tomorrow's automation
```json
{"message_ids": [<shown_ids>]}
```

This is important: shown_ids must NOT include 知識相關 messages that were not shown today, since they haven't been read yet and they must remain unread for a future digest to pick up.

Do not do anything else. Do not send email, do not modify labels other than removing UNREAD in step 1, do not post to any channel other than <slack-user-id>, do not read or write any local files.
```

## Step 8 — Write the launchd plist

Use the schedule confirmed (or kept) in Step 3. Write `~/Library/LaunchAgents/com.local.gmail-slack-digest.plist`, substituting `<StartCalendarInterval-block>` below with the right shape:

- **Every day**:
  ```xml
  <key>StartCalendarInterval</key>
  <dict>
      <key>Hour</key>
      <integer>HH</integer>
      <key>Minute</key>
      <integer>MM</integer>
  </dict>
  ```
- **Specific weekdays**:
  ```xml
  <key>StartCalendarInterval</key>
  <array>
      <dict>
          <key>Hour</key><integer>HH</integer>
          <key>Minute</key><integer>MM</integer>
          <key>Weekday</key><integer>1</integer>
      </dict>
      <!-- one dict per selected weekday, 0 or 7=Sun, 1=Mon, ... 6=Sat -->
  </array>
  ```

First resolve the real `claude` binary path with `which claude` — don't assume it (Apple Silicon Homebrew uses `/opt/homebrew/bin/claude`, Intel Homebrew uses `/usr/local/bin/claude`, other install methods differ again). Call that `<claude-bin>`.

Full plist (note: no `Read`/`Write` in `--allowedTools` — the automation never touches the local filesystem; also note the `Label`/filename deliberately don't include the OS username or account — this lives in `~/Library/LaunchAgents` which is already user-scoped by location, so embedding identity in the name would be redundant personal info):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local.gmail-slack-digest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-lc</string>
        <string><claude-bin> -p "$(cat ~/.claude/scripts/gmail-slack-digest-prompt.txt)" --allowedTools "mcp__workspace-gmail__search_gmail_messages mcp__workspace-gmail__get_gmail_messages_content_batch mcp__workspace-gmail__batch_modify_gmail_message_labels mcp__plugin_slack_slack__slack_get_reactions mcp__plugin_slack_slack__slack_send_message mcp__plugin_slack_slack__slack_read_channel mcp__plugin_slack_slack__slack_read_thread"</string>
    </array>
    <StartCalendarInterval-block>
    <key>StandardOutPath</key>
    <string>/Users/CURRENT_USER/.claude/logs/gmail-slack-digest.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/CURRENT_USER/.claude/logs/gmail-slack-digest.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Substitute `/Users/CURRENT_USER/` with the actual home directory path (`echo $HOME`) — this is a filesystem path, not personal data, but still resolve it rather than hardcoding a guess.

If the plist already existed and is currently loaded (`launchctl list | grep com.local.gmail-slack-digest`), unload it first (`launchctl unload ~/Library/LaunchAgents/com.local.gmail-slack-digest.plist`) before overwriting, then reload in Step 10 so the new schedule actually takes effect.

## Step 9 — Manual test run

Run in the foreground (do NOT background this — inspect the Slack thread reply right after; it can take a few minutes). Use `claude` (bare, resolved via PATH) here rather than the plist's `<claude-bin>` — this run happens in the interactive setup session, not launchd, so PATH is already correct:
```bash
claude -p "$(cat ~/.claude/scripts/gmail-slack-digest-prompt.txt)" --allowedTools "mcp__workspace-gmail__search_gmail_messages mcp__workspace-gmail__get_gmail_messages_content_batch mcp__workspace-gmail__batch_modify_gmail_message_labels mcp__plugin_slack_slack__slack_get_reactions mcp__plugin_slack_slack__slack_send_message mcp__plugin_slack_slack__slack_read_channel mcp__plugin_slack_slack__slack_read_thread" 2>&1 | tee ~/.claude/logs/gmail-slack-digest.log
```
Show the user the Slack message link, and confirm (via `slack_read_thread`) that the `🔧 automation-state` reply was posted under it with a non-empty `message_ids` array.

## Step 10 — Offer to enable

Tell the user it's tested but **not yet live**. Get an explicit yes before running (this is the point where it starts executing for real, every day, unattended):
```bash
launchctl load -w ~/Library/LaunchAgents/com.local.gmail-slack-digest.plist
```
Verify afterward with `launchctl list | grep com.local.gmail-slack-digest`.

To disable later: `launchctl unload ~/Library/LaunchAgents/com.local.gmail-slack-digest.plist`.


## Appendix A — One-time Google Cloud OAuth client setup (only if it doesn't exist yet)

`workspace-gmail` authenticates via an OAuth client whose `client_id`/`client_secret` live as env vars in `~/.claude.json` under `mcpServers.workspace-gmail.env` (`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`) — **not** a `credentials.json`/`token.json` file pair like a raw Google API client library setup. If those env vars are already populated, this appendix is not needed — Step 5's `start_google_auth` call handles the actual user-facing OAuth flow (opens the browser, exchanges the code, stores the resulting token internally). Only follow this appendix if the OAuth client itself needs to be created from scratch (e.g. setting up on a brand new Google Cloud project, or the existing client was deleted/revoked).

**Phase 1 — Create project & enable Gmail API**
1. Open Google Cloud Console.
2. Top-left project dropdown → New Project. Name it (e.g. `Claude-CLI-Integration`), organization = the company's.
3. Inside the project, search "Gmail API" in the top search bar → open it → Enable.

**Phase 2 — OAuth consent screen**
1. Hamburger menu → APIs & Services → OAuth consent screen → Get Started.
2. Branding: App name = `Claude-CLI-Gmail-Access`; User support email = the company Gmail address.
3. Audience: User type = **Internal**.
4. Contact information: same email again.
5. Next → Finish.

**Phase 3 — Create the OAuth client ID**
1. APIs & Services → Credentials → + Create Credentials → OAuth client ID.
2. Application type = **Desktop app**. Name = `Claude-CLI-Credentials`.
3. Create → Download JSON from the success dialog.

**Phase 4 — Wire it into workspace-gmail (differs from a generic Python/Node Gmail API setup)**
Don't rename it to `credentials.json` or drop it in a project folder — `workspace-mcp` doesn't read a credentials file or generate a `token.json`. Instead, transplant `client_id`/`client_secret` straight from the downloaded JSON into `~/.claude.json`.

**Do not `Read` the downloaded JSON directly** — that would put the plaintext `client_secret` into the conversation transcript. Instead run a script that does the extraction and write in one shot, and prints nothing but a fixed success message (never echo/cat the values themselves):

```bash
python3 - <<'PYEOF'
import json, os

creds_path = os.path.expanduser("~/Downloads/<the-downloaded-file>.json")  # ask the user for the actual filename first
config_path = os.path.expanduser("~/.claude.json")

with open(creds_path) as f:
    creds = json.load(f)
info = creds.get("installed") or creds.get("web")

with open(config_path) as f:
    config = json.load(f)

config["mcpServers"]["workspace-gmail"]["env"]["GOOGLE_OAUTH_CLIENT_ID"] = info["client_id"]
config["mcpServers"]["workspace-gmail"]["env"]["GOOGLE_OAUTH_CLIENT_SECRET"] = info["client_secret"]

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print("OAuth client credentials transplanted into ~/.claude.json successfully.")
PYEOF
```

Ask the user for the actual downloaded filename (usually `~/Downloads/client_secret_*.json`) before filling in `creds_path` — don't guess it. The script's only stdout is the fixed success line; the secret values never appear in the tool output or the conversation.

Then:
1. Reconnect the server. If `workspace-gmail` already existed before this Appendix and you only changed its OAuth env vars, `/mcp` reconnect is enough. If you created the entry from scratch as part of this Appendix (the usual case when Appendix A is needed at all), `/mcp` will **not** surface it in the current session — restart the whole session (a new `claude` process). Before doing that, make sure Step 4's checkpoint already wrote the prompt file with Steps 1–2's resolved values, so the fresh session can resume via Step 0 instead of re-asking.
2. Continue from Step 5 above (`start_google_auth`) — that's the actual "first run authorizes in the browser" step; the resulting token is managed by `workspace-mcp` itself, no local `token.json` to babysit.

## Codex native workflow

Use this section only when running in Codex. Use Codex's Gmail and Slack connectors plus a Codex recurring automation. Do not configure Claude CLI, MCP servers, OAuth clients, local prompt files, launchd, or launchctl in this branch.

### Step 1 — Inspect existing setup

Before asking questions:

1. Search for an existing Codex automation whose name or prompt identifies it as the Gmail → Slack digest.
2. If found, view it and summarize the current schedule, status, knowledge criteria, cap, priority topics, and Slack destination in plain language.
3. Check whether Gmail and Slack connector tools are available using tool discovery.
4. If a connector is unavailable, use Codex Plugin Management to suggest installing or connecting the official plugin; do not provide manual install commands or use named connector tools for permission management:
   - Gmail: `gmail@openai-curated-remote`
   - Slack: `slack@openai-curated-remote`
5. Do not continue to a test or automation creation until both connectors are connected.

Ask whether to keep or change an existing configuration. Ask only for unresolved information.

### Step 2 — Resolve the Slack self-DM

Use the connected Slack identity and `slack_search_users` to resolve the user's Slack user ID. A user ID can be used as the self-DM `channel_id`.

If exactly one current authenticated user can be determined, use it without asking for an email address. If there are multiple plausible users, show the candidates and ask the user to choose. Never guess.

The Gmail connector already represents the connected mailbox. Do not ask for Gmail OAuth settings or an email address unless multiple connected Gmail identities genuinely require disambiguation.

### Step 3 — Confirm 📚 知識相關

Before asking for preferences, explain the feature in simple, conversational language:

> 這個功能會把 Gmail 未讀信分成三類，再傳到你自己的 Slack 私訊，讓你快速看到重點，也方便之後回來查看。接下來想請你選哪些信算「知識相關」、一天最多顯示幾封，以及哪些主題要優先。

Ask only one question at a time. Prefer the host's interactive choice UI; if unavailable, show short numbered choices. Use free-form questions only for a custom option.

1. **哪些信要放進 📚 知識相關？** Offer these multi-select choices:
   - 技術／工程電子報
   - 研討會／課程
   - 產業趨勢／研究報告
   - 公司內部教育訓練
   - 其他（自行輸入）
2. **每天最多顯示幾封知識相關？** Suggest `3`, with `5`, unlimited, or a custom number as alternatives.
3. **超過上限時，哪些主題優先？** Ask for an ordered topic list. Examples are illustrative only; never assume them as the user's preference.

Whenever a type is excluded or its destination is unclear, ask `這類信要放哪一類？` with exactly these choices: `🔴 需要處理`, `📚 知識相關`, `🟢 一般通知`.

### Step 4 — Confirm schedule

Ask for:

1. Local run time.
2. Every day, weekdays, or selected weekdays.

Use the user's current timezone. Summarize the schedule in plain language; do not expose a raw recurrence rule.

### Step 5 — Build the automation prompt

Create a self-contained prompt containing the resolved Slack user ID, knowledge criteria, cap, priority topics, and the following runtime instructions.

#### Runtime instructions

You are a recurring Gmail → Slack digest automation. Do not ask questions during a run.

#### A. Process the previous digest

1. Read the latest 20 messages from the Slack self-DM.
2. Find the most recent message beginning with `📧 Gmail 未讀信件整理`.
3. If none exists, continue to B.
4. Read its reactions. If there are no reactions, continue to B without changing Gmail.
5. If any emoji reaction exists, read the digest thread and find the reply beginning with `🔧 automation-state`.
6. Parse its JSON `message_ids`.
7. Use Gmail batch label modification to remove the `UNREAD` label from exactly those message IDs.
8. Reply in the thread with the number marked as read.

Never mark a message read unless its ID came from the reacted digest's automation-state reply.

#### B. Fetch unread Gmail

Search Gmail with `is:unread`, paginating until all results are collected. Do not restrict the search to Inbox. Exclude Spam and Trash.

If there are no unread messages, send:

`📧 Gmail 未讀信件整理 — 目前 0 封未讀`

Then stop without writing an automation-state reply.

#### C. Classify

Read enough message content to classify every unread message into exactly one category:

- 🔴 **需要處理** — the sender explicitly expects the account owner to reply, review, decide, approve, or take action.
- 📚 **知識相關** — use the user's configured knowledge criteria.
- 🟢 **一般通知** — automated or informational mail that needs no reply and is not knowledge-related.

When uncertain between 需要處理 and 一般通知, use 需要處理 only when the message contains a concrete requested action. When uncertain whether something is 知識相關, follow the configured criteria rather than guessing from the sender alone.

If knowledge-related messages exceed the configured cap, show only the highest-ranked messages according to the configured priority topics. Leave hidden knowledge messages unread so they can be reconsidered later.

#### D. Send the digest

Send one Traditional Chinese Slack self-DM:

```text
📧 Gmail 未讀信件整理（今天日期）— 共 N 封未讀

🔴 需要處理（N）
- 每封一行，附 Gmail 連結

📚 知識相關（顯示 N／共 M 封）
- 僅列出本次顯示項目，附 Gmail 連結與一句相關原因

🟢 一般通知（N）
- 相同寄件者或主旨可分組並標示封數
```

If a category is empty, show `無`.

#### E. Save state in the digest thread

Build `shown_ids` from:

- every displayed 需要處理 message;
- every displayed 一般通知 message;
- only the 知識相關 messages actually displayed after applying the cap.

Reply under the new digest:

````text
🔧 automation-state — 請勿刪除此回覆，下一次整理會讀取
```json
{"message_ids":["..."]}
```
````

Do not include capped, undisplayed knowledge messages. Do not send email, delete email, archive email, change any Gmail label other than removing `UNREAD` after a reaction, or post anywhere except the resolved Slack self-DM.

### Step 6 — Test safely

Before the first live automation:

1. Explain that the test sends one real Slack self-DM.
2. Explain that it marks messages read only if the previous digest already has an emoji reaction.
3. Get explicit confirmation.
4. Run the prompt once using the Gmail and Slack connectors.
5. Verify the digest was sent and the `🔧 automation-state` thread reply contains only the IDs actually shown.
6. Report the Slack message link and any classification ambiguity found.

If the test fails, diagnose and fix the connector access, destination, prompt, or classification settings before creating the recurring automation.

### Step 7 — Create or update the Codex automation

Use the Codex automation tools; never create a system cron job or plist.

1. Use `list_projects` to resolve the current local project ID when required.
2. Translate the confirmed schedule into the automation tool's recurrence value without showing the raw value to the user.
3. If a matching automation exists, update it and preserve fields the user did not ask to change.
4. Otherwise create one named `Gmail → Slack 未讀整理`.
5. Use a current supported Codex model with low reasoning effort unless the user requests otherwise.
6. Keep it paused until the test succeeds and the user explicitly says to enable recurring execution.
7. After enabling, view the automation and report its name, plain-language schedule, timezone, and active status.

For pause, resume, schedule changes, or classification changes, update the existing automation instead of creating another one.
