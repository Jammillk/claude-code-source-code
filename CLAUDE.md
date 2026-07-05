# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **decompiled TypeScript source** of Claude Code v2.1.88, extracted from the npm package `@anthropic-ai/claude-code`. The published package ships a single bundled `cli.js` (~12MB). The `src/` directory here is the unbundled source for research/study.

**The source is not directly compilable** as a standalone project:
- Uses Bun compile-time intrinsics (`feature()` from `bun:bundle`, `MACRO.VERSION`) resolved during bundling
- ~108 feature-gated modules were dead-code-eliminated and are not present in the npm artifact
- Only the compiled `cli.js` is meant to be run directly (requires Node.js >= 18)

## Commands

```bash
# Type-check the source (needs npm install first)
npm run check                        # tsc --noEmit

# Best-effort build using esbuild (~95% complete, will need manual stub fixes)
npm run build                        # runs prepare-src then build.mjs

# Run the pre-built CLI directly (recommended)
node cli.js --version                # verify it works
node cli.js -p "Hello Claude"        # non-interactive mode

# Transform source in-place for manual inspection
npm run prepare-src                  # patches bun:bundle imports, MACRO references
```

## Architecture

### Core Loop (the agent pattern)

```
User prompt → messages[] → Claude API (streaming) → response
  ├─ stop_reason == "tool_use"? → execute tools → append tool_result → loop
  └─ stop_reason != "tool_use"  → return text result
```

### Key Files

| File | Role |
|------|------|
| `src/entrypoints/cli.tsx` | CLI bootstrap |
| `src/QueryEngine.ts` | SDK/headless query lifecycle engine — `submitMessage()` → `AsyncGenerator<SDKMessage>` |
| `src/query.ts` | **Main agent loop** — the largest file (~785KB), contains the while-true loop calling Claude API |
| `src/Tool.ts` | Tool interface + `buildTool()` factory — every tool implements `call()`, `validateInput()`, `checkPermissions()`, `prompt()` |
| `src/tools.ts` | Tool registry, presets, filtering |
| `src/commands.ts` | ~80 slash command definitions |

### Layered Architecture

```
Entry Layer:        cli.tsx → main.tsx → REPL.tsx (interactive)
                                     → QueryEngine.ts (headless/SDK)
Query Engine:       submitMessage() → system prompt → agent loop → streaming tools
Tool System:        40+ tools (BashTool, FileEditTool, AgentTool, MCPTool, ...)
Service Layer:      api/claude.ts (streaming API), compact/, mcp/, analytics/, plugins/
State Layer:        AppState store (permissions, fileHistory, fastMode)
Task System:        local_bash, local_agent, remote_agent, in_process, dream tasks
```

### Tool Interface (`buildTool()`)

Every tool implements: `validateInput()` → `checkPermissions()` → `call()`. Additional capabilities: `isEnabled()`, `isConcurrencySafe()`, `isReadOnly()`, `isDestructive()`, plus React/Ink rendering methods (`renderToolUseMessage()`, `renderToolResultMessage()`).

### Sub-Agent System

Agents spawn in 3 modes:
- **default**: in-process, shared conversation
- **fork**: child process, fresh `messages[]`, shared file cache
- **worktree**: isolated git worktree + fork
- **remote**: bridge to Claude Code Remote via HTTP

Communication via `SendMessageTool`, shared task board (`TaskCreate/Update/Get/List`), and team management (`TeamCreate/Delete`).

### Context Compaction

Three strategies: `autoCompact` (summarize old messages via API call), `snipCompact` (HISTORY_SNIP flag), `contextCollapse` (CONTEXT_COLLAPSE flag). Compaction boundaries are marked in the message stream.

### MCP Integration

`MCPConnectionManager` supports stdio, SSE, HTTP, WebSocket, and in-process transports. Tools are registered as `mcp__<server>__<tool>`. Supports OAuth 2.0 and API key auth.

### Permission System

Flow: `validateInput()` → PreToolUse hooks → Permission rules (allow/deny/ask) → Interactive prompt → `checkPermissions()`. Rules sourced from settings.json, CLI args, and session decisions.

### Feature Flag System

Bun's `feature('FLAG_NAME')` is a **compile-time intrinsic** — returns `true` in Anthropic's internal build, `false` in published build. The build script replaces all `feature('X')` calls with `false`. Known flags: `COORDINATOR_MODE`, `HISTORY_SNIP`, `DAEMON`, `KAIROS`, `PROACTIVE`, `VOICE_MODE`, `WEB_BROWSER_TOOL`, `EXPERIMENTAL_SKILL_SEARCH`, `WORKFLOW_SCRIPTS`, etc.

### State Management

`AppState` store with React context: permissions (allow/deny rules, bypass), file history (undo snapshots), fast mode, model selection, attribution tracking. Access via `useAppState(selector)` and `useSetAppState()` (immer-style).

### Session Persistence

Sessions stored as append-only JSONL at `~/.claude/projects/<hash>/sessions/<session-id>.jsonl`. User messages written blocking; assistant messages fire-and-forget. Resume via `--continue` or `--resume <id>`.

### Key Design Patterns

- **AsyncGenerator streaming**: full-chain streaming from API to consumer
- **Branded types**: `SystemPrompt`, `asSystemPrompt()` prevent type confusion
- **Discriminated unions**: `Message` types for type-safe message handling
- **Builder + Factory**: `buildTool()` provides safe defaults for tool definitions
- **Lazy schema**: `lazySchema()` defers Zod evaluation for performance

## Build Process Detail

The build script (`scripts/build.mjs`) performs:
1. Copy `src/` → `build-src/`
2. Replace `feature('X')` → `false` in all `.ts`/`.tsx` files
3. Replace `MACRO.VERSION` etc → string literals
4. Remove `import { feature } from 'bun:bundle'`
5. Create stubs for missing feature-gated modules
6. Bundle with esbuild → `dist/cli.js`

Known limitation: esbuild cannot replicate Bun's DCE, so `require()` calls inside `if (false)` branches still resolve and cause missing-module errors. The script iteratively creates stubs (up to 5 rounds).
