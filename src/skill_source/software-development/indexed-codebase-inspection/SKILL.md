---
name: indexed-codebase-inspection
description: "Use Codebase Memory MCP for graph-aware codebase discovery, impact analysis, and implementation inspection before falling back to grep."
version: 1.0.0
author: Tapas Manager
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [codebase-memory, inspection, impact-analysis, debugging, repository]
    related_skills: [systematic-debugging, codebase-inspection]
---

# Indexed Codebase Inspection

Use this skill when a repository may already be indexed in Codebase Memory and the task requires understanding implementation behavior, call relationships, ownership, impact, or where to patch code.

This complements file search and LOC-oriented inspection. For semantic codebase work, graph-aware inspection is usually faster and less noisy than broad grep.

## When to Use

- User asks to inspect, debug, modify, or review an existing codebase.
- User points to a class, function, resolver, topic, API route, event, or behavior and asks how to fix it.
- You need to find publishers/subscribers, callers/callees, related tests, or impacted symbols.
- User explicitly says to use Codebase Memory or that it is more efficient.
- Broad `search_files` output would be large or ambiguous.

Do not use this for simple file content reads when the exact file is already known and no relationship context is needed.

## Workflow

1. **List indexed projects first.**

   ```text
   mcp_codebase_memory_list_projects()
   ```

   Use the exact returned project name. Do not guess aliases. For example, `/opt/data/workspace/unicorn` may be indexed as `opt-data-workspace-unicorn`, not `unicorn`.

2. **Search graph for definitions and likely seams.**

   ```text
   mcp_codebase_memory_search_graph(
     project="<exact-project>",
     query="InMemoryPubSub publish subscribe pubsub",
     include_connected=true,
     limit=50,
   )
   ```

3. **Use code search for exact patterns when needed.**

   ```text
   mcp_codebase_memory_search_code(
     project="<exact-project>",
     pattern="subscribe\\(|publish\\(|BULLETIN_CHANGES",
     regex=true,
     mode="compact|full",
   )
   ```

4. **Hydrate exact symbols before changing code.**

   ```text
   mcp_codebase_memory_get_code_snippet(
     project="<exact-project>",
     qualified_name="<qualified-name-from-search_graph>",
     include_neighbors=true,
   )
   ```

5. **Trace relationships for impact.**

   ```text
   mcp_codebase_memory_trace_path(
     project="<exact-project>",
     function_name="<qualified-name>",
     direction="inbound|outbound|both",
     depth=2,
     include_tests=true,
   )
   ```

6. **After editing, ask Codebase Memory for change impact if indexed state supports it.**

   ```text
   mcp_codebase_memory_detect_changes(
     project="<exact-project>",
     since="HEAD",
     scope="path/or/symbol",
     depth=2,
   )
   ```

7. **Fall back deliberately.**

   Use `search_files`, `read_file`, and `terminal` when Codebase Memory is unavailable, stale, returns no relevant graph edges, or you need exact live file contents after edits.

## Pitfalls

- **Wrong project name:** Codebase Memory tools require the exact indexed project name from `list_projects`.
- **Graph search is not a replacement for tests:** use it to find seams and impact, then still reproduce, patch, and verify.
- **Tool output may be stale after edits:** read the live file or run tests before final claims.
- **Dirty-tree audit confusion:** when the task asks about current committed support, capture the exact commit and `git status` first. Use the graph to discover seams, but verify modified files against `HEAD` (for example with `git show HEAD:<path>`) so unrelated local instrumentation is not reported as shipped behavior. Preserve and explicitly disclose pre-existing changes.
- **Do not drown the context:** prefer graph/search results with limits and hydrate only the exact symbols you need.

## References

- `references/inmemory-pubsub-session.md` — example of using Codebase Memory to inspect an event-loss bug and identify publishers/subscribers before patching.
