# Quick Start Guide

> **Supported Tools**: VS Code Copilot, Cursor, and Rovodev

This guide will help you get ai-session-bridge up and running in 5 minutes.

## Installation

**Quick Start** (using pipx - recommended):
```bash
# Install pipx if you don't have it
brew install pipx  # macOS
# or: python3 -m pip install --user pipx

# Install ai-session-bridge
git clone https://github.com/frknyldz/ai-session-bridge
cd ai-session-bridge
pipx install .
```

**For Development** (using venv):
```bash
git clone https://github.com/frknyldz/ai-session-bridge
cd ai-session-bridge
./setup.sh  # Automated setup
# or
pip install -e ".[dev]"  # Manual setup
```

**From PyPI** (when published):
```bash
pipx install ai-session-bridge
```

## Basic CLI Usage

### 1. List Your Sessions

```bash
# List all sessions in current workspace
ai-session-bridge list

# List only Copilot sessions
ai-session-bridge list --tool copilot

# List sessions for specific workspace
ai-session-bridge list --workspace /path/to/project
```

### 2. View a Session

```bash
# Show full conversation
ai-session-bridge show <session-id> --tool copilot
```

### 3. Search Across Sessions

```bash
# Search for "authentication"
ai-session-bridge search "authentication"

# Search in specific tool
ai-session-bridge search "bug fix" --tool rovodev
```

## MCP Server Setup

> **Note**: Replace `/absolute/path/to/ai-session-bridge` with your actual installation path

### For VS Code Copilot

1. Open VS Code settings (⌘+, on Mac, Ctrl+, on Windows/Linux)
2. Search for "mcp"
3. Edit `settings.json` and add:

```json
{
  "servers": {
    "ai-session-bridge": {
      "command": "/Users/YOUR_USERNAME/.local/bin/ai-session-bridge",
      "args": ["serve"]
    }
  }
}
```

**Or if using venv for development:**
```json
{
  "servers": {
    "ai-session-bridge": {
      "command": "/absolute/path/to/ai-session-bridge/venv/bin/ai-session-bridge",
      "args": ["serve"]
    }
  }
}
```

4. Restart VS Code
5. Your Copilot can now access previous conversations!

### For Cursor

1. Edit `~/.config/mcp/mcp.json` (or Cursor settings.json)
2. Add:

```json
{
  "mcpServers": {
    "ai-session-bridge": {
      "command": "/Users/YOUR_USERNAME/.local/bin/ai-session-bridge",
      "args": ["serve"]
    }
  }
}
```

**Or if using venv for development:**
```json
{
  "mcpServers": {
    "ai-session-bridge": {
      "command": "/absolute/path/to/ai-session-bridge/venv/bin/ai-session-bridge",
      "args": ["serve"]
    }
  }
}
```

3. Restart Cursor

### For Rovodev

1. Edit `~/.config/mcp/mcp.json`
2. Add:

```json
{
  "mcpServers": {
    "ai-session-bridge": {
      "command": "/Users/YOUR_USERNAME/.local/bin/ai-session-bridge",
      "args": ["serve"]
    }
  }
}
```

**Or if using venv for development:**
```json
{
  "mcpServers": {
    "ai-session-bridge": {
      "command": "/absolute/path/to/ai-session-bridge/venv/bin/ai-session-bridge",
      "args": ["serve"]
    }
  }
}
```

3. Restart Rovodev

---

**After PyPI Release**: Replace the `command` with `"uvx"` and `args` with `["ai-session-bridge", "serve"]`

## Testing MCP Tools

Once configured, try these prompts with your AI assistant:

### Example 1: List Recent Sessions
```
"Show me my recent AI conversations"
```

The assistant will use `list_sessions` to show your conversation history.

### Example 2: Continue Previous Work
```
"Continue where we left off"
```

The assistant will use `get_recent_context` to understand what you were working on.

### Example 3: Find Past Discussion
```
"Did we discuss authentication in any previous conversations?"
```

The assistant will use `search_sessions` to find relevant discussions.

### Example 4: View Specific Session
```
"Show me the full conversation from session abc123"
```

The assistant will use `get_session` to retrieve the complete conversation.

## Configuration (Optional)

Create `~/.config/ai-session-bridge/config.yaml` for customization:

```yaml
# Enable/disable specific tools
tools:
  copilot: true
  cursor: true
  rovodev: true

# Cache settings
cache:
  enabled: true
  max_age_days: 30

# Search settings
search:
  enabled: true
  use_fts: true

# Content filtering (security)
filtering:
  enabled: true  # Redacts API keys, secrets, etc.
```

## Troubleshooting

### Sessions Not Found

1. Make sure you're in the correct workspace
2. Check that the AI tool has created sessions (have you had conversations?)
3. Try: `ai-session-bridge list --workspace /full/path/to/workspace`

### MCP Server Not Working

1. Verify your venv binary path is correct in the config
2. Test the server manually: `ai-session-bridge serve` (or `python -m ai_session_bridge.server`)
3. Check AI tool's logs for MCP connection errors
4. Try restarting the AI tool
5. After PyPI release: Install via `pip install ai-session-bridge` and use `uvx` command

### Search Not Working

```bash
# Clear cache and rebuild index
ai-session-bridge cache clear

# Then list sessions to rebuild index
ai-session-bridge list
```

## Next Steps

- Read the [full README](README.md) for more details
- Customize your [configuration](examples/config.yaml)
- Check out the [PLAN.md](PLAN.md) for technical details

## Support

- Report issues: https://github.com/frknyldz/ai-session-bridge/issues
- Contribute: Pull requests welcome!
