# Demo and submission

Target **6:10**. Keep your webcam and screen visible throughout. Start with
the dashboard and terminal open. Run once before recording so you know which
weather and model responses are available in your environment.

| Time | What to show and say |
| --- | --- |
| 0:00–1:00 | Open the README sequence diagram. “The host runs Streamlit and owns the model conversation. FastMCP serves three typed tools from a separate child process. The host discovers the schemas over stdio, maps them to OpenAI tools, and puts each result back in the conversation with its matching call ID.” |
| 1:00–2:30 | Open `ai_prompt_log.md`. Show Findings 1 and 2. “The first FastMCP draft returned a bare dictionary, so the client received no structured result. A typed mapping fixed the protocol result. I also traced why a valid count-style read failed in SQLite. The authorizer now recognizes that SQLite can report an allowed empty-column read without a schema name.” Point out the read-only URI and deny-by-default authorizer. |
| 2:30–4:00 | Select OpenAI mode, paste the README prompt, and expand each event after the run. Explain the SQL join, observed weather timestamp or availability status, and how the order total from SQL becomes the calculator input. Compare inventory capacity with order quantity and review the raw insurance result before rounding it for a quote. If you use the scripted mode, identify it aloud as scripted. |
| 4:00–5:30 | Open the Security workbench. Run the single-statement check and arithmetic-only check. “Two harmless SELECT statements are rejected by the single-statement policy. A regular function call is rejected because the calculator only allows numbers and arithmetic operators.” Open the returned error objects and return to the console to show that the server still responds. |
| 5:30–6:10 | Run `uv run python -m pytest -v`. Point to discovery, the real stdio tool calls, call ID reconciliation, weather mocks, and policy tests. “The regression suite exercises real local MCP transport. OpenAI and weather behavior in the automated tests use fixtures.” |

Upload your recording as **Unlisted** or **Public** and test the link in a private
window. Use the actual video duration and repository URL when submitting.

## Week 5 Hands-On Assignment Submission

- **Student name** — Eleni Mulu
- **GitHub repository URL** — [Add the URL after publishing]
- **Deployment** — [Use your deployed URL, or note that you demonstrated Docker locally after running it]
- **YouTube video link and duration** — [Add verified link and MM:SS]
- **MCP transport** — stdio
- **Tools** — Read-only SQLite query tool with AST validation, Open-Meteo weather tool, and Python AST arithmetic evaluator
- **Model** — [Enter the model displayed in the console. The supplied default is gpt-4o-mini.]
