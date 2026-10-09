# MCP server

InsurePilot exposes its tool catalog over the Model Context Protocol, so any MCP client
(Claude Desktop, IDE agents, other services) can use the same tools the in-app agents use.

```bash
cd apps/api
.venv/Scripts/python -m app.mcp.server          # stdio (Windows; use .venv/bin/python elsewhere)
.venv/Scripts/python -m app.mcp.server --http   # streamable HTTP
```

Tools act on behalf of `INSUREPILOT_USER_EMAIL` (default: the demo profile).

## Claude Desktop config

```json
{
  "mcpServers": {
    "insurepilot": {
      "command": "C:/path/to/InsurePilot AI/apps/api/.venv/Scripts/python.exe",
      "args": ["-m", "app.mcp.server"],
      "cwd": "C:/path/to/InsurePilot AI/apps/api",
      "env": { "INSUREPILOT_USER_EMAIL": "demo@insurepilot.ai" }
    }
  }
}
```

## Tools and permission tiers

| Tier | Behavior | Tools |
|---|---|---|
| `read` | Runs immediately, logged to AI Activity | `get_policy`, `get_coverages`, `get_deductible`, `get_claim`, `get_claim_status`, `get_policy_documents`, `search_policy_documents`, `get_bill`, `get_eob`, `get_provider_network_status`, `find_providers`, `get_prior_authorization_status`, `check_procedure_cost`, `reconcile_medical_bill`, `get_quotes` |
| `draft` | Creates internal drafts only | `create_claim_draft`, `generate_claim_packet` |
| `external` | **Never executes directly.** Creates a pending approval the user must confirm in the app | `submit_claim`, `send_email`, `share_medical_data`, `request_human_review` |
