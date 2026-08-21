#!/usr/bin/env bash
# Install aiworkers-mcp for MCP clients (Cursor, Claude, OpenClaw, …)
set -euo pipefail

PKG_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v pipx >/dev/null 2>&1; then
  echo "Installing with pipx…"
  pipx install --force "$PKG_DIR"
elif command -v uv >/dev/null 2>&1; then
  echo "Installing with uv tool…"
  uv tool install --force "$PKG_DIR"
else
  echo "Installing with pip --user…"
  python3 -m pip install --user --upgrade "$PKG_DIR"
fi

echo ""
echo "Done. CLI: aiworkers-mcp"
echo "Set AIWORKERS_API_KEY and add to your agent — see README.md"
echo ""
echo "Minimal Cursor snippet (.cursor/mcp.json):"
cat <<'EOF'
{
  "mcpServers": {
    "aiworkers": {
      "command": "aiworkers-mcp",
      "env": {
        "AIWORKERS_API_BASE": "https://ai.knopka.click",
        "AIWORKERS_API_KEY": "PASTE_YOUR_KEY_FROM_ADMIN"
      }
    }
  }
}
EOF
