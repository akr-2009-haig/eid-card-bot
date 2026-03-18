# Workspace

## Overview

pnpm workspace monorepo using TypeScript, plus a standalone Python Telegram bot project.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Structure

```text
artifacts-monorepo/
├── artifacts/              # Deployable applications
│   └── api-server/         # Express API server
├── lib/                    # Shared libraries
│   ├── api-spec/           # OpenAPI spec + Orval codegen config
│   ├── api-client-react/   # Generated React Query hooks
│   ├── api-zod/            # Generated Zod schemas from OpenAPI
│   └── db/                 # Drizzle ORM schema + DB connection
├── scripts/                # Utility scripts (single workspace package)
│   └── src/                # Individual .ts scripts
├── eid_card_bot/           # Python Telegram Bot (standalone, no web server)
└── package.json            # Root package with hoisted devDeps
```

## Eid Card Bot (Python Telegram Bot)

Located in `eid_card_bot/`. Pure long-polling Telegram bot using Pyrogram + Pillow.

### Setup

1. Edit `eid_card_bot/config.py` — set `BOT_TOKEN` and your Telegram user ID in `ADMIN_IDS`
2. Run: `cd eid_card_bot && python main.py`
3. A sample template is pre-created at `data/templates/sample_template.jpg`
4. To add more templates, use `/admin` → Manage Templates inside the bot

### Structure

```
eid_card_bot/
├── main.py                     # Entry point — runs the bot
├── config.py                   # BOT_TOKEN, ADMIN_IDS, paths
├── requirements.txt
├── setup_font.py               # One-time font downloader
├── database/
│   ├── db.py                   # All SQLite operations
│   └── bot.db                  # Auto-created on first run
├── handlers/
│   ├── start.py                # /start, back_home, how_to_use
│   ├── user.py                 # design_card flow, name input
│   ├── admin.py                # /admin panel, stats, menus
│   ├── admin_text_handler.py   # Text editing state handler
│   ├── templates.py            # Template upload/delete/view
│   ├── forcesub.py             # check_sub callback
│   ├── forcesub_admin.py       # Add/delete/view channels (admin)
│   ├── texts_buttons.py        # Edit texts, manage buttons
│   └── ads.py                  # Broadcast to users/channels
├── keyboards/
│   ├── user_keyboard.py        # User inline keyboards
│   └── admin_keyboard.py       # Admin inline keyboards
├── services/
│   ├── image_generator.py      # Pillow card generation
│   ├── template_manager.py     # Template file management
│   ├── subscription_checker.py # Check user channel membership
│   └── broadcast.py            # Async broadcast helpers
├── utils/
│   ├── helpers.py              # Logging, is_admin
│   └── rate_limit.py           # Simple rate limiter
├── data/
│   ├── templates/              # Template image files
│   ├── fonts/arabic.ttf        # Arabic font (auto-downloaded)
│   └── generated/              # Temp generated cards
└── logs/bot.log
```

### Features

- Force-subscribe to channels/groups before use
- Admin panel: `/admin`
- Full template management (add/delete/view)
- Fully customizable messages and buttons from admin panel
- Broadcast to all users or channels
- Statistics dashboard
- Arabic font rendering with shadow effect
- Rate limiting per user
- SQLite database (auto-initialized)
