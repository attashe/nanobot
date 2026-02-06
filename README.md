<div align="center">
  <h1>nanobot: Telegram AI Bot</h1>
  <p>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </p>
</div>

A minimal, Telegram-only AI assistant with agent capabilities: tool use, cron scheduling, subagents, skills, and memory.

## Quick Start

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Configure** (`~/.nanobot/config.json`)

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  }
}
```

Get API keys: [OpenRouter](https://openrouter.ai/keys) (LLM) · [Brave Search](https://brave.com/search/api/) (optional, for web search)

Get your Telegram bot token from [@BotFather](https://t.me/BotFather) and your user ID from [@userinfobot](https://t.me/userinfobot).

**3. Run**

```bash
python server.py
```

## Local Models (vLLM)

```json
{
  "providers": {
    "vllm": {
      "apiKey": "dummy",
      "apiBase": "http://localhost:8000/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "meta-llama/Llama-3.1-8B-Instruct"
    }
  }
}
```

## Configuration

Config file: `~/.nanobot/config.json`

| Provider | Purpose | Get API Key |
|----------|---------|-------------|
| `openrouter` | LLM (recommended, access to all models) | [openrouter.ai](https://openrouter.ai) |
| `vllm` | Local LLM (OpenAI-compatible server) | — |
| `moonshot` | LLM (Moonshot/Kimi) | [moonshot.cn](https://platform.moonshot.cn) |

### Security

| Option | Default | Description |
|--------|---------|-------------|
| `tools.restrictToWorkspace` | `false` | Restricts all agent tools to the workspace directory |
| `channels.telegram.allowFrom` | `[]` | Whitelist of Telegram user IDs. Empty = allow everyone |

## Docker

```bash
docker build -t nanobot .
docker run -v ~/.nanobot:/root/.nanobot nanobot
```

## Project Structure

```
server.py              # Entry point: python server.py
requirements.txt       # Python dependencies
Dockerfile             # Docker image
lib/
  agent/               # Core agent logic (loop, context, memory, skills, tools)
  bus/                 # Message routing
  channels/            # Telegram channel
  config/              # Configuration schema & loader
  cron/                # Scheduled tasks
  providers/           # LLM providers (OpenRouter, vLLM, Moonshot)
  session/             # Conversation sessions
  utils/               # Helpers
  skills/              # Built-in skills
workspace/             # Templates for ~/.nanobot/workspace/
tests/                 # Tests
```

## Extending

- **Add tools**: Create a `Tool` subclass in `lib/agent/tools/`, register in `AgentLoop._register_default_tools()`
- **Add skills**: Create `workspace/skills/<name>/SKILL.md`
- **Modify prompts**: Edit files in `workspace/` (AGENTS.md, SOUL.md, TOOLS.md)
