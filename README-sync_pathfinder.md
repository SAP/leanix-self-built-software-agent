# sync_pathfinder.py — LeanIX Synchronization Script

---

## What does this script do?

After running `main.py` for AI service discovery from your GitHub environment, use `sync_pathfinder.py` to **sync your local database with LeanIX EAM workspace**.  
It creates/updates Microservice FactSheets, tech stack FactSheets, and contributors in LeanIX via its GraphQL API.

---

## When should I run it?

**Run only after completing AI discovery with `main.py`.**  
This script is the next step to push your latest findings to LeanIX.

---

## How to use

1. **Set environment variables**  
   Add `LEANIX_TOKEN` and `LEANIX_DOMAIN` to your `.env` file for LeanIX authentication.

2. **Install dependencies**
   ```bash
   uv venv && uv sync
    ```
---

## Run the script
   ```bash
   python sync_pathfinder.py
   ```
**What happens?**
- Fetches discovered services from your database
- Creates or updates FactSheets in LeanIX
- Links each service to its tech stack and contributors

---

## Requirements

- [x] **Python 3.8+**
- [x] **All dependencies from `pyproject.toml`**
- [x] **Access to the same database as `main.py`**
- [x] **LeanIX EAM workspace Token**

---

## Troubleshooting

**Missing environment variables?**
- Check your `.env` for `LEANIX_TOKEN` and `LEANIX_DOMAIN`.

**Database errors?**
- Ensure your database is running and accessible.

**LeanIX API errors?**
- Verify your token, domain, and network connection.

**Logs**
- Progress and errors are printed to the console for easy debugging.
