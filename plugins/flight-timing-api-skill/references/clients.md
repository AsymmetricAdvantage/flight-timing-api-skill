# Install paths by agent

The skill is a plain folder containing `SKILL.md`, following the open
[Agent Skills](https://agentskills.io) format. Every client below reads that
format, so the same folder works everywhere. Only the destination path differs.

Copy the whole `plugins/flight-timing-api-skill/` folder and keep the folder name
`flight-timing-api-skill`. The Agent Skills spec requires the `name` in the
frontmatter to match the parent directory name.

| Agent | Where to put the folder | Notes |
| --- | --- | --- |
| **Hermes Agent** | `~/.hermes/skills/travel/flight-timing-api-skill/` | Category subfolder optional. Hermes requires only `name` and `description`. |
| **Claude Code** | `~/.claude/skills/flight-timing-api-skill/` (personal) or `<project>/.claude/skills/flight-timing-api-skill/` | Also installable as a plugin from the marketplace (below). |
| **OpenAI Codex** | `$CODEX_HOME/skills/flight-timing-api-skill/` (default `~/.codex/skills/`) | Disable with `[[skills.config]]` in `~/.codex/config.toml`. See `agents/openai.yaml` for UI metadata. |
| **Grok** | `~/.agents/skills/flight-timing-api-skill/` or `~/.grok/skills/flight-timing-api-skill/` | Grok also reads Claude Code skills and the `AGENTS.md` family with no extra setup. |
| **OpenClaw** | `~/.agents/skills/flight-timing-api-skill/` or `<workspace>/skills/flight-timing-api-skill/` | Workspace skills take precedence. The skill name comes from the `name` frontmatter. |
| **Muse Code** | `~/.claude/skills/flight-timing-api-skill/` or `$CODEX_HOME/skills/flight-timing-api-skill/` | Muse Code discovers both the Claude and Codex skill roots. |
| **ChatGPT / dots** | Install as a skill or plugin in ChatGPT | Dots run on the same skills and plugin system. Availability varies by plan. |

## Shared roots worth knowing

Three discovery paths cover more than one client, so a single copy can serve
several agents:

- `~/.agents/skills/` is read by **both OpenClaw and Grok**.
- `~/.claude/skills/` is read by **Claude Code, Grok and Muse Code**.
- `$CODEX_HOME/skills/` is read by **Codex and Muse Code**.

## Claude Code and Grok marketplace install

This repository is also a plugin marketplace, which Grok consumes because it is
Claude Code compatible. Once the repository is public:

```
claude plugin marketplace add asymmetricadvantage/flight-timing-api-skill
claude plugin install flight-timing-api-skill@fuji-daily
```

The skill then appears namespaced as
`/flight-timing-api-skill:flight-timing-api-skill`. The doubled name is a side
effect of Claude Code namespacing plugin skills by plugin name; the marketplace
entry name can be shortened later if that becomes annoying.

## Per-surface attribution

Set `TPWL_SUBID` so bookings are attributable to the surface they came from.
Each install can use its own value: `hermes`, `claude-code`, `codex`,
`openclaw`, `grok`, `muse`. Reports then show which installation earns.

## Verifying the skill is loaded

- Hermes: `skills_list` should show `flight-timing-api-skill`.
- Claude Code: `/plugin details flight-timing-api-skill` shows `Skills (1)`.
- Grok: the skill appears in `/skills` and as a slash command.
- OpenClaw: `openclaw skills check` lists it.
- Any client: ask "when is the cheapest time to fly from JFK to Tokyo?" and
  check that a `travel.fujidaily.com` link comes back.
