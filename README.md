<div align="center">

# ModularMarkets

**A market-making system for hosting buy/sell sites for non-liquid commodities across platforms — games, services, and IRL items.**

[![GitHub Stars](https://img.shields.io/github/stars/ModularMarkets/ModularMarkets?style=for-the-badge&logo=github)](https://github.com/ModularMarkets/ModularMarkets/stargazers)
[![Code size](https://img.shields.io/github/languages/code-size/ModularMarkets/ModularMarkets?style=for-the-badge)](https://github.com/ModularMarkets/ModularMarkets)
[![Languages](https://img.shields.io/github/languages/count/ModularMarkets/ModularMarkets?style=for-the-badge)](https://github.com/ModularMarkets/ModularMarkets)
[![Top language](https://img.shields.io/github/languages/top/ModularMarkets/ModularMarkets?style=for-the-badge)](https://github.com/ModularMarkets/ModularMarkets)
[![License](https://img.shields.io/github/license/ModularMarkets/ModularMarkets?style=for-the-badge)](./LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/ModularMarkets/ModularMarkets?style=for-the-badge)](https://github.com/ModularMarkets/ModularMarkets/commits/main)

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Run Instructions](#-how-to-run) • [Platforms](#-platforms)

</div>

---
<!-- Replace the path below with your own screenshot (e.g. docs/screenshot.png or docs/demo.gif) -->
<p align="center">
  <img src="https://github.com/user-attachments/assets/592cca2d-fa36-43b9-98e7-190e602502b2" width="513">
</p>
</div>

## Features

- **Multi-platform** — Plug in games (e.g. Minecraft), services, or IRL items via the abstract `Platform` interface.
- **Market making** — Merchants with configurable buy/sell prices, caps, and pluggable algorithms (e.g. inventory-based MM).
- **User system** — Accounts, balances, roles (Guest / User / Admin), and linked platform identities.
- **REST API** — FastAPI backend with OpenAPI docs at `/docs`.
- **Web UI** — React + TypeScript + Vite frontend for managing merchants and trading.
- **Optional Minecraft** — Bot “warehouses” (Node + mineflayer) for in-game delivery/retrieval.

---

## Quick Start

**Backend (required):**

```bash
git clone https://github.com/ModularMarkets/ModularMarkets.git
cd ModularMarkets

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
echo "DATABASE_URL=sqlite:///marketmaker.db" > .env   # optional; this is the default

python backend/main.py
```

- API: **http://localhost:8000**  
- API docs: **http://localhost:8000/docs**

**Frontend (optional):**

```bash
cd frontend
npm install
npm run dev
```

- App: **http://localhost:3000** (proxies `/api` to the backend)

---

## How to Run

### 1. Backend (API server)

From the **project root**:

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Optional: set environment (defaults work for local dev)
echo "DATABASE_URL=sqlite:///marketmaker.db" > .env

# Start the API (default: http://0.0.0.0:8000)
python backend/main.py
```

| Variable         | Default                     | Description        |
|------------------|-----------------------------|--------------------|
| `PORT`           | `8000`                      | API server port    |
| `HOST`           | `0.0.0.0`                   | Bind address       |
| `DATABASE_URL`   | `sqlite:///marketmaker.db`  | Database URL       |

### 2. Frontend (web UI)

In a **second terminal**, from the project root:

```bash
cd frontend
npm install
npm run dev
```

- Frontend: **http://localhost:3000**
- Ensure the backend is running on **port 8000**.

### 3. Minecraft platform (optional)

Only if you use the Minecraft integration:

**Python dependencies:**

```bash
pip install -r src/platforms/minecraft/requirements.txt
```

**Node service (mineflayer bots):**

```bash
cd src/platforms/minecraft/node_service
npm install
npm start
```

Configure `src/platforms/minecraft/confs/` (`config.yml`, `items.yml`, `bots.yml`) as described in [Minecraft Platform README](src/platforms/minecraft/README.md). Do not commit real passwords in `bots.yml`.

### 4. Nix (alternative setup)

```bash
nix develop                    # All platforms
nix develop .#minecraft-only   # Minecraft only
nix develop .#core-only        # Core only (no platforms)
```

Then from the project root:

- **API:** `python backend/main.py`
- **Frontend:** `cd frontend && npm install && npm run dev`
- **Minecraft Node service:** `cd src/platforms/minecraft/node_service && npm start`

### 5. Tests

From the project root:

```bash
pytest tests/
```

---

## Architecture

### Project structure

```
src/
├── algorithm.py         # Algorithm interface and Result class
├── database.py          # Database connection and initialization
├── merchant.py          # Merchant class for item trading
├── models.py            # SQLAlchemy database models
├── shop.py              # Shop interface for managing merchants
├── platforms/
│   ├── platform.py      # Platform abstract base class
│   ├── minecraft.py     # Minecraft platform implementation
│   └── carboncredit/    # Carbon credit platform
├── algorithms/          # Pricing algorithms (e.g. inventory MM, stub)
└── users/
    └── user.py          # User class for account management

backend/
└── main.py              # FastAPI app entry (uvicorn)
frontend/                # React + TypeScript + Vite UI
```

### Core concepts

| Concept    | Description |
|-----------|-------------|
| **User**  | Accounts, authentication, balances, roles (0=Guest, 10=User, 100=Admin), linked platform accounts. |
| **Merchant** | Single-item trader: buy/sell prices, caps, and algorithm-driven price updates. |
| **Shop**  | Collection of merchants; belongs to a platform. |
| **Platform** | Abstract interface for external systems (games, services) that provide items/services. |
| **Algorithm** | Abstract interface for market-making logic that computes buy/sell prices. |

### Dependencies

- **Backend:** SQLAlchemy, FastAPI, uvicorn, python-dotenv, requests (see `requirements.txt`).
- **Frontend:** React, TypeScript, Vite, axios (see `frontend/package.json`).
- **Minecraft:** Node + mineflayer (see `src/platforms/minecraft/node_service/package.json`).

---

## Platforms

- **Minecraft** — Bot warehouses, item config (YAML), trading modes: drop, chat, plugin. See [Minecraft README](src/platforms/minecraft/README.md).
- **Carbon credit** — Placeholder platform in `src/platforms/carboncredit/`.

New platforms implement the `Platform` abstract class and live under `src/platforms/<name>/`.

---

## Notes

- Database: SQLAlchemy ORM; SQLite by default, PostgreSQL via `DATABASE_URL`.
- Platform code stays under `src/platforms/<platform>/` and does not modify core `src/` files.
- Algorithms implement the `Algorithm` abstract class and live in `src/algorithms/`.

---

<div align="center">

**ModularMarkets** — commodity market-making across games, services, and IRL.

[Report bug](https://github.com/ModularMarkets/ModularMarkets/issues) · [Request feature](https://github.com/ModularMarkets/ModularMarkets/issues)

</div>
