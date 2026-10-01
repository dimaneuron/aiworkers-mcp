# AIWorkers MCP (НЕЙРОСОТРУДНИКИ)

MCP so Cursor, Claude and OpenClaw can run your **neural employees**.

Product: [ai.knopka.click](https://ai.knopka.click) · MCP landing: [ai.knopka.click/mcp](https://ai.knopka.click/mcp)

**If you are a coding agent:** follow **Quick start** below. Install `aiworkers-mcp`, have the human run `aiworkers-mcp login`, restart, call `aiworkers_whoami`, then `aiworkers_skill_update`. Do not invent tokens. Never ask for the 12-word seed.

CLI: **`aiworkers-mcp`**

One Bearer key can target **several** workers (`group_id` on each tool). Default group: `AIWORKERS_GROUP_ID` or the key's bound group.

## Neural employees

They are neuro-assistants you hire for a job — not a generic chatbot.

Typical roles: marketers, sellers, support, booking. Typical channels: Telegram, WhatsApp, Avito, Instagram, a site widget.

Each employee has a card, memory, chats, ready replies, surveys, tasks, and often a Telegram bot. People talk to them in the channel; you (or your coding agent) run them from here.

More on the product: [ai.knopka.click](https://ai.knopka.click).

## Roadmap

**Ready now**

- Login from Telegram (no token in the URL), parent `awp_` / child `awm_` keys
- Surveys (DSL, responses, stats, share)
- Tasks
- Worker card, memory, chats, ready replies, send and broadcast
- Telegram: status, command menu, process restart (no chat send on `telegram_*`)
- Booking CRM
- Two wallets (account USD + group TokenTime); salary and one-time tt via quote → confirm
- LLM keys for [api.knopka.click](https://api.knopka.click): issue/list/revoke, then OpenAI-compatible + custom inference (`ai_chat`, `ai_request`)
- Telegram userbot CRM on `https://api.knopka.click/tg/` (`tg_*`: accounts, create channel/bot). Same LLM key, **allowlisted by bound ETH address** (LiteLLM parent). Each wallet sees only its mapped accounts, not the whole CRM pool. Not `telegram_*` (worker bot process)

**Next**

- Finance module (`fin_op`) — stub in v1
- Minting a child key will later debit group TokenTime (free for now)
- More of the product’s channels through the same MCP as they land in the admin

## Quick start

```bash
chmod +x install.sh
./install.sh
```

Get a key from **@aiworkersbot**. The MCP can share this URL — there is **no token in the link**:

https://t.me/aiworkersbot?start=mcp

The Mini App shows the token **once**. Copy it, then:

```bash
aiworkers-mcp login
```

Paste the token at the prompt. It is written to `~/.config/aiworkers/credentials.json` (`chmod 600`). Restart the agent. Ask it to call **`aiworkers_whoami`**.

Tool `aiworkers_login_link` returns the same URL without needing an existing key.

Legacy forms keys still work as `AIWORKERS_API_KEY`.

`uvx` without installing:

```bash
uvx --from git+https://github.com/dimaneuron/aiworkers-mcp.git aiworkers-mcp
```

## Update MCP

`aiworkers_skill_update` only refreshes `SKILL.md`. New tools need a **process restart** (Cursor Settings → MCP → Restart `aiworkers`). If the catalog is still old: `pipx install --force git+https://github.com/dimaneuron/aiworkers-mcp.git`, then restart again. Dummy env `AIWORKERS_MCP_RELOAD` in `mcp.json` forces Cursor to respawn the process. Not `telegram_restart`.

## Environment

| Variable | Meaning |
|----------|---------|
| `AIWORKERS_API_KEY` | Parent `awp_…` or legacy Bearer |
| `AIWORKERS_KEY_WORKERS` | Child `awm_…` for workers (`_SURVEYS`, `_TASKS`, `_TELEGRAM`, `_CRM`, `_BOOKING`) |
| `AIWORKERS_API_BASE` | Default `https://ai.knopka.click` |
| `AIWORKERS_BOOKING_BASE` | Default `https://book.knopka.click/booking` |
| `AIWORKERS_GROUP_ID` | Default Telegram `group_id` (tasks / workers / telegram / crm) |
| `AIWORKERS_MODULES` | Comma list. Default `surveys,tasks,workers,telegram,crm`. Stub: `finance` |
| `AIWORKERS_CREDENTIALS` | Override path to `credentials.json` |
| `AIWORKERS_KNOPKA_AI_KEY` | User LLM key for `api.knopka.click` (else `credentials.json` `knopka_ai`) |
| `AIWORKERS_KNOPKA_AI_BASE` | Default `https://api.knopka.click` |
| `AIWORKERS_TG_TIMEOUT` | Timeout for `/tg/` CRM calls, default `180` |

Prefer `aiworkers-mcp login` over putting secrets in `mcp.json`. Per-module child tokens cannot call other modules. `booking` / `book` / `calendar` is one child for tasks+crm on **that group only**; existing `tasks`/`crm` keys stay narrow.

Fallbacks (old names still work): `SURVEY_MCP_API_KEY`, `TASKS_MCP_API_KEY`, `TASKS_GROUP_ID`, `BOOKING_INTERNAL_SECRET`.

## Tools

Always on:

- `aiworkers_whoami` — what this key can see (call this first)
- `aiworkers_login_link` — Telegram URL, no token in the link
- `aiworkers_skill` — agent SKILL.md
- `aiworkers_skill_update` — write/refresh `~/.cursor/skills/aiworkers/SKILL.md` (does **not** restart MCP or add tools; see **Update MCP** in the bundled SKILL)
- `aiworkers_token_mint` — parent `awp_` mints a child `awm_` for one module + group (shown once; `save=true` writes credentials.json). Free for now; later group TokenTime.
- `ai_keys_issue` / `ai_keys_list` / `ai_keys_revoke` / `ai_keys_rename` — parent `awp_` manages a **separate** LLM key for `api.knopka.click` (`save=true` writes `credentials.json` `knopka_ai`). Not an `awp_`/`awm_` token. Shown once.
- `ai_models` / `ai_chat` / `ai_request` — call `api.knopka.click` with that LLM key. Allowlisted paths only (OpenAI + custom inference). No LiteLLM admin. `stream` is always false. JSON body only. `/tg/` is not on this list.
- `tg_health` / `tg_accounts_list` / `tg_channel_create` / `tg_bot_create` / `tg_send_message` / `tg_login_*` / `tg_request` — userbot CRM at `api.knopka.click/tg/`. Same LLM key. Allowlisted CRM paths only (no `/env`, `/pm2`, session import). Not `telegram_*`.

**surveys**: `survey_agent_skill`, `survey_get_dsl_rules`, `survey_validate_dsl`, `survey_create`, `survey_agent_list_forms`, `survey_agent_get`, `survey_agent_update`, `survey_agent_responses`, `survey_agent_stats`, `survey_agent_settings_get`, `survey_agent_settings_save`, `survey_agent_scenarios_get`, `survey_agent_scenarios_save`, `survey_agent_archive`, `survey_agent_delete`, `survey_agent_share`. Resource: `survey://dsl/spec`.

**tasks**: `tasks_list`, `tasks_count`, `tasks_get`, `tasks_create`, `tasks_update`, `tasks_batch_update`, `tasks_complete`, `tasks_cancel`.

**workers** (read + write, no logs): `workers_list`, `workers_get`, `workers_balance`, `workers_topup_link`, salary/tt quote→confirm, `workers_partner`, `workers_update` (not for tt), memory/chats/readyreply, **`workers_chat_send`** (known chats only, `bot`/`embed`/`topic`), **`workers_broadcast_quote` / `workers_broadcast_confirm`**. Money and broadcast: quote then `confirm=true`.

**telegram** (no chat sending): `telegram_status`, `telegram_commands_get`, `telegram_commands_save`, `telegram_restart`. Restart the worker process (`aibot-<username>`, same as /telegram_bot). 60s cooldown per bot; 429 `retry_after` — do not hammer. Do not use `workers_update` for that. Personal/broadcast is under **workers**. This is not `/tg/`.

**tg** (userbot CRM, always on, LLM key): `tg_health`, `tg_accounts_list`, `tg_account_get`, `tg_account_start` / `tg_account_stop`, `tg_channel_create`, `tg_bot_create`, `tg_send_message`, `tg_join_group` / `tg_leave_group`, `tg_groups_list`, `tg_tasks_list`, `tg_phone_check`, `tg_login_start` / `tg_login_confirm` / `tg_login_password`, `tg_request`. Base `https://api.knopka.click/tg/`. Allowlisted by bound ETH address; each wallet is scoped to mapped accounts. Denied: `/env`, `/pm2`, `/api/tokens`, `import-session`, `start-all`/`stop-all`. Not group todos (`tasks_*`).

**crm** (Booking CRM): `crm_context`, `crm_process`. Tool `group_id` is enough. Create with start/end books the public calendar slot and posts the group card. Mint alias `booking` / `book` / `calendar` for tasks+crm together (same group).

**finance** — not in v1.

## Agent config

Paste the same `mcpServers.aiworkers` block. Change only the config file path.

Shared JSON:

```json
{
  "mcpServers": {
    "aiworkers": {
      "command": "aiworkers-mcp",
      "env": {
        "AIWORKERS_API_BASE": "https://ai.knopka.click",
        "AIWORKERS_API_KEY": "PASTE_awp_OR_awm_TOKEN"
      }
    }
  }
}
```

| Agent | Config file | Example |
|-------|-------------|---------|
| Cursor | `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` | [examples/cursor.json](examples/cursor.json) |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS); `%APPDATA%\Claude\claude_desktop_config.json` (Windows) | [examples/claude-desktop.json](examples/claude-desktop.json) |
| Claude Code | `~/.claude.json` | [examples/claude-code.json](examples/claude-code.json) |
| VS Code Copilot | `.vscode/mcp.json` or user `Code/User/mcp.json` | [examples/vscode.json](examples/vscode.json) |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | [examples/windsurf.json](examples/windsurf.json) |
| OpenClaw | `$OPENCLAW_CONFIG_PATH` or `openclaw.json` | [examples/openclaw.json](examples/openclaw.json), [uvx](examples/openclaw-uvx.json) |
| Codex CLI | `$CODEX_HOME/config.toml` | [examples/codex.toml](examples/codex.toml) |
| Gemini CLI | `.gemini/settings.json` | [examples/gemini-cli.json](examples/gemini-cli.json) |
| Cline | `~/.cline/mcp.json` | [examples/cline.json](examples/cline.json) |
| Continue | `~/.continue/config.yaml` | [examples/continue.yaml](examples/continue.yaml) |

Restart the agent after editing.

`uvx` variant (no global install): see [examples/openclaw-uvx.json](examples/openclaw-uvx.json).

## Compatibility

Older CLIs still work:

- `aiworkers-survey-mcp` — same as `AIWORKERS_MODULES=surveys`
- `aiworkers-tasks-mcp` — same as `AIWORKERS_MODULES=tasks`

If the umbrella package is on `PYTHONPATH`, they delegate here. Otherwise they run their standalone FastMCP as before.

## Privacy

This repo is the **client**. Do not put `.env`, tokens, or credentials here.

---

# Русский

MCP, через который Cursor, Claude и OpenClaw управляют **нейросотрудниками**.

Продукт: [ai.knopka.click](https://ai.knopka.click) · лендинг MCP: [ai.knopka.click/mcp](https://ai.knopka.click/mcp)

**Если ты агент:** ставь по **Quick start** выше. Человек делает `aiworkers-mcp login`. Токены не выдумывать. Сид из 12 слов в чат не брать.

## Кто такие нейросотрудники

Это нейроассистенты под роль, не «просто чат-бот».

Роли: маркетологи, продавцы, поддержка, запись. Каналы: Telegram, WhatsApp, Avito, Instagram, виджет на сайте.

У каждого — карточка, память, чаты, готовые ответы, опросы, задачи, часто свой Telegram-бот. Клиенты пишут им в канале; ты (или агент в Cursor) управляешь ими отсюда.

Подробнее — на [ai.knopka.click](https://ai.knopka.click).

## Дорожная карта

**Уже работает**

- Вход из Telegram (токена в ссылке нет), ключи parent `awp_` / child `awm_`
- Опросы (DSL, ответы, статистика, шаринг)
- Задачи
- Карточка, память, чаты, готовые ответы, отправка и рассылка
- Telegram: статус, меню команд, рестарт процесса (без отправки через `telegram_*`)
- Booking CRM
- Два кошелька (USD аккаунта + TokenTime группы); зарплата и разовая покупка tt — quote → confirm
- Ключи LLM для [api.knopka.click](https://api.knopka.click): выпуск/список/ревок, потом OpenAI-совместимые и кастомные запросы (`ai_chat`, `ai_request`)
- Userbot CRM на `https://api.knopka.click/tg/` (`tg_*`: аккаунты, создать канал/бота). Тот же LLM-ключ, allowlist по ETH-адресу кошелька, каждый кошелёк видит свой набор аккаунтов. Это не `telegram_*` (процесс бота нейросотрудника)

**Дальше**

- Модуль finance (`fin_op`) — в v1 заглушка
- Выпуск child-ключа позже будет списывать TokenTime группы (сейчас бесплатно)
- Остальные каналы продукта — в тот же MCP, по мере появления в админке

