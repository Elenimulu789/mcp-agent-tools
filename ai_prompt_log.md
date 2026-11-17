# AI prompt and verification log

## Initial prompt

> Build a Python 3.11 MCP logistics console using the official SDK. Expose
> one bounded SQLite SELECT tool over a synthetic operations dataset, an async
> Open-Meteo city lookup, and a restricted decimal AST calculator. Discover tools
> over stdio, map schemas to OpenAI function definitions, correlate tool outputs
> by call ID, bound the loop, and add a Streamlit inspector and pytest coverage.
> Keep tool execution separate from the model and use safe policy-rejection
> examples for demonstrations.

ChatGPT drafted the implementation and ran the integration checks below.
The initial draft already avoided general-purpose Python execution and used
a read-only SQLite URI. The following defects were observed in the draft and
corrected during review.

## Finding 1 · MCP result schema mismatch

The FastMCP tool used a bare `dict` return annotation. The protocol trace
showed no output schema and `structuredContent=None`, even though the
calculator returned a value. The host requires structured results, so the
first stdio integration and SQL-to-math chain tests failed.

```diff
- def calculate_expression(expression: str) -> dict:
+ def calculate_expression(expression: str) -> dict[str, Any]:
```

Applied to all three tools. A typed mapping now produces a JSON object in
`structuredContent`. The stdio integration test asserts that result directly.

## Finding 2 · Valid SQLite reads rejected

The authorizer required the database argument to equal `main` on every read.
SQLite emitted an empty-column read with an unspecified schema during a valid
cross join. The row-limit test failed before the query returned.

```diff
- if action == sqlite3.SQLITE_READ and database == "main" and table in TABLES:
-     return sqlite3.SQLITE_OK
+ if action == sqlite3.SQLITE_READ and table in TABLES:
+     if database == "main" or (database is None and arg2 == ""):
+         return sqlite3.SQLITE_OK
```

The narrow exception preserves the table allowlist. The authorizer still
denies unknown operations and functions. The read-only URI and AST check are
independent controls. Policy tests confirm the fixture database's bytes stay
unchanged after rejections.

## Finding 3 · Optional tool calls on final OpenAI responses

During source review, the original adapter passed the SDK message directly
into a model that expects a list. A final response can supply a null
`tool_calls` field, which would fail validation. The adapter now replaces
null with an empty list and maps supported call objects. A regression test
covers this response shape.

```diff
- return Turn.model_validate(message.model_dump())
+ return Turn.model_validate({
+     "content": message.content,
+     "tool_calls": [call.model_dump() for call in message.tool_calls or []],
+ })
```

## Verification and boundaries

- Tests use a real local MCP subprocess, a deterministic substitute for the
  model in orchestration tests, and a mock HTTP transport for weather.
- The UI workbench sends fixed, harmless policy probes to the MCP server.
  Two SELECT statements and a regular function call both fail policy checks.
- No credential, cloud deployment, Docker runtime, browser recording, or
  real model response is assumed from these local checks.
