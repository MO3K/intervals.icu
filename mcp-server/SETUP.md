# Intervals.icu MCP Server — Setup

This folder is part of the `intervals.icu` project and can be synced via cloud storage (Google Drive, OneDrive, etc.). After syncing, follow these steps to connect on a new computer.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager

Install uv (Windows):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 1. Configure credentials

Copy `.env.example` to `.env` and fill in your credentials:
```
ATHLETE_ID=iXXXXXX
API_KEY=your_api_key_here
```

Find your Athlete ID and API key at [intervals.icu/settings](https://intervals.icu/settings).

---

## 2. Add to Claude Desktop config

Open `%APPDATA%\Claude\claude_desktop_config.json` and add the `Intervals.icu` block to `mcpServers`:

```json
"Intervals.icu": {
  "command": "uv",
  "args": [
    "run",
    "--with",
    "mcp[cli]",
    "--with-editable",
    "PATH_TO_THIS_FOLDER",
    "mcp",
    "run",
    "PATH_TO_THIS_FOLDER\\src\\intervals_mcp_server\\server.py"
  ],
  "env": {
    "API_KEY": "your_api_key_here",
    "ATHLETE_ID": "iXXXXXX"
  }
}
```

Replace `PATH_TO_THIS_FOLDER` with the actual path to this `mcp-server` directory.

**Example** (if synced to `G:\intervals.icu\mcp-server`):
```json
"Intervals.icu": {
  "command": "uv",
  "args": [
    "run",
    "--with",
    "mcp[cli]",
    "--with-editable",
    "G:\\intervals.icu\\mcp-server",
    "mcp",
    "run",
    "G:\\intervals.icu\\mcp-server\\src\\intervals_mcp_server\\server.py"
  ],
  "env": {
    "API_KEY": "your_api_key_here",
    "ATHLETE_ID": "iXXXXXX"
  }
}
```

Note: if `uv` is not in PATH, use the full path to the uv executable:
- Windows default: `C:\Users\USERNAME\.local\bin\uv.exe`

---

## 3. Restart Claude Desktop

After saving the config, restart Claude Desktop — the Intervals.icu MCP server will be available.

---

## Dependencies

Dependencies are installed automatically by `uv` on first run via `pyproject.toml` and `uv.lock`. No manual `pip install` needed.
