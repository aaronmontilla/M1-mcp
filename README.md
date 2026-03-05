# 5G-MAG M1 Interface MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that exposes the **3GPP M1 interface** (TS 26.512) as AI-callable tools, enabling LLM agents to configure 5G Media Streaming (5GMS) sessions through natural language.

## Overview

This server wraps the 5GMS Application Function's M1 REST API into three guided tools that walk users through the standard 3-step provisioning workflow:

```
Step 1 → create_provisioning_session
Step 2 → create_content_hosting_configuration
Step 3 → create_consumption_reporting_configuration
```

Each tool includes detailed inline documentation so an AI agent can explain parameters in plain language and guide users through configuration without needing prior 3GPP knowledge.

## Features

- Full 3-step 5GMS provisioning workflow via MCP tools
- Session state persisted across tool calls (M1 URL and session ID remembered automatically)
- Supports both DASH and HLS entry points
- JSON template support for content hosting configuration
- Clear, structured error messages with troubleshooting hints
- Compatible with any MCP client (Claude Desktop, Claude Code, custom agents)

## Requirements

- Python 3.10+
- A running [5G-MAG Reference Tools](https://github.com/5G-MAG/rt-5gms-application-function) Application Function instance with the M1 interface accessible

## Installation

```bash
git clone https://github.com/<your-username>/5G-MAG_mcp.git
cd 5G-MAG_mcp
pip install -r requirements.txt
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | MCP server framework (FastMCP) |
| `httpx` | Async HTTP client for M1 API calls |

## Usage

### Running the server

```bash
python server.py
```

The server communicates over stdio and is intended to be launched by an MCP host (e.g. Claude Desktop).

### Connecting to Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "5gms-m1": {
      "command": "python",
      "args": ["/path/to/5G-MAG_mcp/server.py"]
    }
  }
}
```

### Connecting to Claude Code

```bash
claude mcp add 5gms-m1 python /path/to/5G-MAG_mcp/server.py
```

## Tools

### 1. `create_provisioning_session`

Creates the top-level provisioning session container. Must be called first.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `asp_id` | Yes | — | Application Service Provider ID |
| `app_id` | Yes | — | Application ID |
| `provisioning_session_type` | No | `DOWNLINK` | `DOWNLINK` or `UPLINK` |
| `m1_url` | Yes (first call) | — | Base URL of M1 interface, e.g. `http://192.168.1.100:7778` |

### 2. `create_content_hosting_configuration`

Defines the media ingest origin and distribution entry point.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `name` | Yes | — | Friendly name for the configuration |
| `ingest_base_url` | Yes | — | Origin server base URL |
| `entry_point_relative_path` | Yes | — | Path to `.mpd` (DASH) or `.m3u8` (HLS) manifest |
| `entry_point_content_type` | No | `application/dash+xml` | MIME type of the manifest |
| `domain_name_alias` | No | None | CDN hostname alias |
| `dash_profiles` | No | `["urn:mpeg:dash:profile:isoff-live:2011"]` | DASH profile URNs |
| `ingest_pull` | No | `true` | Pull vs push ingest |
| `ingest_protocol` | No | HTTP pull URN | Ingest protocol URN |

### 3. `create_consumption_reporting_configuration`

Enables viewer analytics reporting. All parameters are optional.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `reporting_interval` | No | `10` | Seconds between client reports |
| `sample_percentage` | No | `100.0` | Percentage of clients that report |
| `location_reporting` | No | `true` | Include geographic location |
| `access_reporting` | No | `true` | Include network access info |

## Content Hosting Configuration Template

The file `content_hosting_config_template.json` is used as a base for Tool 2. You can edit it to add additional fields that will be merged with the values you provide at runtime:

```json
{
    "name": "My 5GMS Stream",
    "ingestConfiguration": {
        "pull": true,
        "protocol": "urn:3gpp:5gms:content-protocol:http-pull-ingest",
        "baseURL": "https://example.com/media/"
    },
    "distributionConfigurations": [
        {
            "entryPoint": {
                "relativePath": "stream/manifest.mpd",
                "contentType": "application/dash+xml",
                "profiles": ["urn:mpeg:dash:profile:isoff-live:2011"]
            }
        }
    ]
}
```

## Example Workflow

```
User: Set up a 5GMS stream for my live event.

Agent: Step 1 — I'll create a provisioning session.
       [calls create_provisioning_session(asp_id="acme", app_id="live-event-1", m1_url="http://10.0.0.5:7778")]
       → Session ID: abc-123

Agent: Step 2 — Now I'll configure the content hosting.
       [calls create_content_hosting_configuration(
           name="Live Event Stream",
           ingest_base_url="https://origin.acme.com/",
           entry_point_relative_path="live/event1/manifest.mpd"
       )]
       → Content hosting configured.

Agent: Step 3 — Finally, enabling consumption analytics.
       [calls create_consumption_reporting_configuration(reporting_interval=30)]
       → All done! Your 5GMS session is ready.
```

## Project Structure

```
5G-MAG_mcp/
├── server.py                           # MCP server with all 3 tools
├── content_hosting_config_template.json # Base template for Tool 2
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

## Standards Reference

- **3GPP TS 26.512** — 5G Media Streaming (5GMS); Protocols
- **M1 Interface** — Provisioning interface between AF and AS
- **5G-MAG Reference Tools** — Open-source 5GMS implementation

## Related Projects

- [5G-MAG Reference Tools](https://github.com/5G-MAG/rt-5gms-application-function) — The Application Function this server talks to
- [Model Context Protocol](https://modelcontextprotocol.io/) — The protocol used to expose tools to AI agents

## License

MIT — see [LICENSE](LICENSE) for details.
