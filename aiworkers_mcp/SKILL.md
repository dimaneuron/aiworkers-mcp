---
name: aiworkers
description: >
  Use the AIWorkers / НЕЙРОСОТРУДНИКИ MCP (aiworkers-mcp): login without putting
  a token in a URL, manage workers, memory, chats, ready replies, surveys, tasks,
  telegram commands, restart the Telegram worker process, two-layer balances
  (account USD vs group TokenTime), salary quote→confirm, one-time tt buy,
  partner info, booking CRM, issue LLM keys for api.knopka.click and call
  OpenAI-compatible plus custom inference, Telegram userbot CRM (/tg/:
  accounts, create channel, create bot). Use when the user mentions MCP,
  aiworkers, нейросотрудник, aiworkers-mcp, /mcp, awp_, awm_, баланс, tt, токены,
  «сколько токенов», пополнить, зарплата, contribution, партнёрка,
  «перезапусти бота», restart the bot, api.knopka.click, /tg/, канал, userbot,
  «обнови MCP», «перезапусти MCP», or asks to log in / get an API key.
---

# AIWorkers MCP

Thin MCP client. Business logic stays on `https://ai.knopka.click`. Do not invent tokens or seeds.

Install docs (source of truth): https://github.com/dimaneuron/aiworkers-mcp  
Landing: https://ai.knopka.click/mcp  
Product: https://ai.knopka.click

If this project has no MCP yet: read that README, install `aiworkers-mcp`, have the human run `aiworkers-mcp login`, then `aiworkers_whoami` and `aiworkers_skill_update`.

## Login (no token in the link)

1. Call **`aiworkers_login_link`** (works without a key) and give the human this URL:
   `https://t.me/aiworkersbot?start=mcp`
2. They open it in Telegram, Mini App shows a module token **once**. Seed of 12 words never goes to chat or to the server.
3. Human runs `aiworkers-mcp login` on the Mac and pastes the token. That writes `~/.config/aiworkers/credentials.json` (`chmod 600`).
4. Restart the agent. Call **`aiworkers_whoami`**.

Do not put tokens in git, in `mcp.json` committed to the repo, or in chat. Prefer `aiworkers-mcp login` over env in config.

## Update MCP (do not mix the three layers)

A tool «not in this session» is **not** proof it is missing on the server. Cursor caches the tool catalog until the MCP **process** dies. `aiworkers_skill_update` only rewrites `SKILL.md`. It does **not** restart MCP and does **not** install new tools. Never use `telegram_restart` for this.

When the human says «обнови MCP» / «перезапусти MCP», a tool from this skill is missing from the catalog, or the catalog contradicts a live 200/403 from `ai.knopka.click`:

1. **Skill file** (what you read). Call **`aiworkers_skill_update`**. Same CLI: `aiworkers-mcp skill-update`. Writes `~/.cursor/skills/aiworkers/SKILL.md` (and project `.cursor/skills/aiworkers/` if you are in a repo with `.cursor`). Then **re-read that file**. An old copy in context is stale.

2. **Running process** (tool catalog). Restart the `aiworkers` MCP server.
   - Tell the human: Cursor Settings → MCP → Restart on `aiworkers`.
   - If you can edit config: set env `AIWORKERS_MCP_RELOAD` in `.cursor/mcp.json` or `~/.cursor/mcp.json` to a new stamp (example `20260821-ai-keys`), then kill the process: `pkill -f aiworkers-mcp`. Cursor respawns it. Do not dump the file or any `awp_`/`awm_`/`sk-` values.
   - After restart, the catalog must list the tools from this skill (including `ai_keys_issue` / `ai_chat` / `tg_channel_create` if this skill mentions them). If the catalog still lies, the process did not actually restart.

3. **Installed package** (binary still old after a real restart). Reinstall, then do step 2 again:

```
pipx install --force git+https://github.com/dimaneuron/aiworkers-mcp.git
```

From a local checkout: `./install.sh`. `uvx --from git+https://github.com/dimaneuron/aiworkers-mcp.git` can cache an old wheel — `--force` / reinstall, then restart.

4. **Verify.** Call **`aiworkers_whoami`**. Then try the tool that was «missing». Still absent → tell the human the MCP process is stale; do not invent the tool or call a URL instead.

Live API `GET https://ai.knopka.click/api/mcp/skill` is what `aiworkers_skill_update` prefers after a Flask deploy. New **tools** still need steps 2–3.

## Tokens

| Kind | Prefix | Scope |
|------|--------|--------|
| Parent | `awp_…` | All groups this Telegram user admins. Can mint children. |
| Child | `awm_…` | One `module` + one `group_id`. No escalation. |
| Legacy | forms / getApiKey | Still works; no module field. |

Modules: `surveys`, `tasks`, `workers`, `telegram`, `crm`, `booking`. Aliases for booking: `book`, `calendar`. Finance is not in v1.

Parent `awp_` can mint children: **`aiworkers_token_mint(module, group_id)`**. Writes `awm_` into `credentials.json` when `save=true` (default). Token is shown once in the tool result — tell the human the **prefix** + module + group; do not dump the full secret unless they need it on another machine (`aiworkers-mcp login`). Generation is **free** for now; later it will debit **group TokenTime**. If 402 — not enough `group.tt`.

Wrong module → 403 `нужен child для <module>, не общий`. Child `awm_` workers: only that group + the key owner's wallet. `booking` / `book` / `calendar` mint the same child: tasks + crm on **that group only**. Existing `tasks` and `crm` children stay narrow (not widened). Never surveys/workers/telegram. Other groups → 403.

## First call

`aiworkers_whoami` — groups, `kind`, `module`, `eth_address`. If there is no key, it returns the login URL.

## Two wallets (do not mix)

1. **Account** — `users.balance` USD. One per person, shared across groups. Top-up: `https://t.me/aiworkersbot?start=addBalance`, or with amount `…?start=addBalance_10` (integer USD only; a dot in start payload is invalid). **`workers_topup_link` does not credit tt.** There is no `tt_credit` on that tool. The bot opens the same payment screen and shows **Change amount**. Bare `addBalance` is the old picker.
2. **Group TokenTime** — `group.tt`. Chat spend hits this. Subscription: **+$1 contribution → +3600 tt**. One-time: **$10 → 3600 tt** (10×), solary unchanged.

`workers_balance(group_id)` always returns both layers plus `hints`. `workers_list` has group tt on each row and **one** `account` object at the root.

Rates in the payload: `tt_per_usd_subscription` = 3600, `tt_per_usd_onetime` = 360. Do not invent other numbers.

## Money: quote → confirm

Nothing is charged until `confirm=true` on the matching confirm tool. Quote lives ~5 min. Reuse / missing / expired quote → 409.

- **Salary (own contribution only):** `workers_salary_quote(add_usd)` then `workers_salary_confirm(quote_id, confirm=true)`. Integer USD, must increase. Quote shows my contribution / others / new solary. Other admins can raise their own share — say that. Cannot decrease via MCP (human writes @dimaneuron).
- **One-time tt:** `workers_tt_buy_quote(amount_usd=10)` or `tt=…` then `workers_tt_buy_confirm(quote_id, confirm=true)`. Does **not** change solary.
- Never write tt via `workers_update`.

## Zero balance

If `account.usd <= 0`: give addBalance (`workers_topup_link` / `hints.topup_url`), say other admins can raise salary (`hints.other_admins_can_raise`), call **`workers_partner`**. Do not invent partner percents — use `rates` from that tool (empty dict means no published %).

If `group.tt <= 0` but the account has money: offer salary (subscription 3600 tt/$) vs one-time 10×, ask what the human wants.

## Tools (by module)

Always: `aiworkers_login_link`, `aiworkers_whoami`, `aiworkers_skill`, `aiworkers_skill_update`, **`aiworkers_token_mint`** (parent `awp_` → child `awm_`), **`ai_keys_issue` / `ai_keys_list` / `ai_keys_revoke` / `ai_keys_rename`**, **`ai_models` / `ai_chat` / `ai_request`**, **`tg_*`**.

- **ai / api.knopka.click**: LLM key is **not** `awp_`/`awm_`. Parent `awp_` issues it via **`ai_keys_issue(save=true)`** → `credentials.json` `knopka_ai`. Budget $1, models `*`. List/revoke/rename never need the Mini App 12 words. After save, **`ai_models`**, **`ai_chat(model, messages_json)`**, **`ai_request(method, path, body_json)`** hit `https://api.knopka.click` directly. `stream` is always false. JSON body only. Paths are allowlisted (OpenAI `/v1/chat/completions`, embeddings, images, audio, `/v1/messages`, `/cursor/`, `/v1/videos`, `/rag/`, `/key/info`). Admin LiteLLM (`/key/generate`, `/user/delete`, `/global/…`) → 400 `path not allowed`. **`ai_request` does not call `/tg/`** — that is the **tg** module. Tell the human **prefix + alias**; do not dump the full `sk-` unless they need it on another machine. Never put it in git or `mcp.json`. Env: `AIWORKERS_KNOPKA_AI_KEY`, `AIWORKERS_KNOPKA_AI_BASE`.

- **workers**: list/get/update card; memory; chats (no logs dump beyond the tool); ready replies. **`workers_chat_send`** — one message to a known chat (`workers_chats_list` only): `channel=auto|bot|embed|topic` (default auto = bot DM, or widget outbox). Mirrors the same content into the user's forum topic (no extra agent label). **`workers_broadcast_quote` / `workers_broadcast_confirm`** — one-shot DM blast of a ready reply to people who already wrote this bot; quote then `confirm=true`. Status stays in the mailing topic like native «Разослать»; MCP audit goes to the main-admin error log. Not arbitrary Telegram ids, not folders, not pyrogram. **`workers_readyreply_upsert`** posts the donor into the native ready-reply topic (`P{message_id}` + customization button). Re-upsert of an item without `message_id` publishes it; changing `text` edits the Telegram post. No bot token in responses. **`workers_balance`**, **`workers_topup_link`** (account only), **`workers_salary_quote` / `workers_salary_confirm`**, **`workers_tt_buy_quote` / `workers_tt_buy_confirm`**, **`workers_partner`**. Empty `group_id` → credentials / `AIWORKERS_GROUP_ID`, else «нужен group_id».
- **surveys**: DSL (`Q1*` = required), validate, create (mismatch `group_id` → 403, no silent remap), agent get/update/responses/stats/settings/scenarios, archive/delete, `survey_agent_share` (`form_url` + `chat_text` for `workers_chat_send` / readyreply). `survey_id` may be the full id, public slug from `/form/XXXXXXX`, or a pasted form URL. Resource `survey://dsl/spec`. Writes via POST, not PUT.
- **tasks**: list/count/get/create/update/complete/cancel. Need `group_id` or credentials.
- **telegram**: status + command menu of the **neural-employee bot**; **`telegram_restart(group_id)`** — start/restart pm2 `aibot-<username>` (same as /telegram_bot «Перезапустить скрипт»). Rate-limited: 60s cooldown per bot, in-flight lock, hourly cap. On 429 wait `retry_after` — do not loop. **Do not send chats via telegram_*.** Personal/broadcast is **`workers_chat_send`** / **`workers_broadcast_*`**. If the user says «перезапусти бота» / restart the bot → call `telegram_restart`, not `workers_update`. This is **not** `/tg/` userbot CRM.
- **tg** / **api.knopka.click/tg**: userbot CRM (Moon-Userbot behind the LiteLLM tariff proxy). Same LLM key as **ai**, not `awm_`, not `telegram_*`. Always-on module. **Allowlisted by bound ETH address** (LiteLLM parent key / `metadata.parent_user`) and optional exact alias. Other valid `sk-` → 403 `tg_key_not_allowed`, not a CRM login. The proxy checks Bearer, then sends CRM `X-CRM-Token` plus `X-CRM-Allowed-Accounts` from `tg-acl.yaml` on llm2aiw. ACL key is the bound checksum ETH address (LiteLLM parent `key_alias` + `metadata.user` / `parent_user`); exact child `key_alias` can override. Named account groups and/or phones; optional metadata `tg_groups` / `tg_accounts`. Missing map → 403 `tg_no_accounts`. Cookie godmode is gone. Named tools: **`tg_health`**, **`tg_accounts_list`**, **`tg_account_get`**, **`tg_account_start` / `tg_account_stop`**, **`tg_channel_create(account, title, description?, username?)`**, **`tg_bot_create(account, bot_name, bot_username)`** (`bot_username` must end with `bot`; token comes back once — do not commit), **`tg_send_message`**, **`tg_join_group` / `tg_leave_group`**, **`tg_groups_list`**, **`tg_tasks_list`**, **`tg_phone_check`**, **`tg_login_start` → `tg_login_confirm` → `tg_login_password`** (2FA). Extra CRM paths: **`tg_request(method, path, body_json)`** allowlist only (`/accounts`, `/groups-channels`, `/tasks`, `/messages`, login, phone check). Denied: `/env`, `/pm2`, web `/login`, `/api/tokens`, `import-session`, `start-all` / `stop-all`. `create-channel` / `create-bot` hit live Telegram — confirm with the human first. Not group todos (`tasks_*`). Not booking CRM (`crm_*`).
- **crm** / **booking**: `crm_context(group_id)` returns `employees`, preferred `employee_id`, `cal_link`. Unknown `username` → 404 `not_linked`. **`crm_process(group_id, payload_json)`** — tool `group_id` is enough. payload: `{action: create|update|cancel, event: {title, uid, startTime, endTime, attendees, organizer?}}`. Create with `startTime`/`endTime` books the public cal.diy slot (same as book.knopka.click) **and** posts the gpt_206 card. Do not follow with `tasks_create` hold. `cancel`/`update` need `event.uid` and cancel also frees the calendar slot. `notify_topic`/`notify_dm` false skips the Telegram card. Not a dry-run. Not admin CRM dialogs.
- **booking** (aliases `book`, `calendar`): one child for **tasks + crm** on that `group_id` only. Mint `module=booking|book|calendar`. Does not unlock surveys/workers/telegram. Does not widen already-minted `tasks` / `crm` keys.

Pass `group_id` when the tool has it. Default comes from credentials / `AIWORKERS_GROUP_ID`.

## Hard rules

- Never log or repeat the 12-word seed.
- Never ask the human to paste the seed into the agent chat.
- `whoami` must not show bot tokens (API already strips them).
- Child key for `workers` cannot call `tasks` or another group.
- LLM `sk-` for `api.knopka.click` is not an MCP token. Do not commit it. Do not paste the full secret in chat unless the human asked to copy it elsewhere.
- `ai_request` only allowlisted inference paths. Do not try LiteLLM admin. Need a new custom path → change the allowlist, not `*`. `/tg/` is **not** on that list.
- `/tg/` userbot CRM is **`tg_*` / `tg_request`**, same LLM key, **allowlisted by bound ETH address** (LiteLLM parent key) and optional exact alias. Foreign `sk-` → 403 `tg_key_not_allowed`. No yaml map → 403 `tg_no_accounts`. Accounts in `tg_health` / `tg_accounts_list` are that wallet's subset, not the whole CRM pool. Not `telegram_*`, not `workers_chat_send`, not `tasks_*`. Do not call `/env`, `/pm2`, `/api/tokens`, or `import-session`. Bot token from `tg_bot_create` is a secret.
- Child `booking`/`book`/`calendar` can call `tasks_*` and `crm_*` only for its bound `group_id`. Other groups → 403. Surveys/workers/telegram stay forbidden. Existing `awm_` `tasks` or `crm` keys are not widened.
- Surveys/tasks 403 «Токен не привязан к group_id» on a parent key → `aiworkers_token_mint(module=surveys|tasks|booking, group_id=…)`, not Mini App as the only path.
- Send: only `workers_chat_send` / `workers_broadcast_*`. Recipient must already be in `workers_chats_list`. Never invent a Telegram chat id. Broadcast needs quote then `confirm=true`.
- «Перезапусти бота» (нейросотрудник / `aibot-<username>`) is `telegram_restart`, never `workers_update`. Start/stop a **userbot account** is `tg_account_start` / `tg_account_stop`.
- «Сколько токенов» / баланс / tt → `workers_balance` (one group) or `workers_list` (all). Not a loop of `workers_get`.
- «Пополнить» the **account** → `workers_topup_link`. With a USD amount the URL is `start=addBalance_N` (integer). Still no tt. To add **tt** → salary quote or one-time tt quote, after the human confirms. Never patch `tt` with `workers_update`.
- Partner: `workers_partner` only. Do not mix with worker-bot `/ref`. Do not invent %.
- A tool missing from the Cursor catalog ≠ missing on the server. Follow **Update MCP**: skill_update, then restart the MCP process, then reinstall the package if still stale. Not `telegram_restart`.
