"""Streamlit dashboard with separate operator and guardrail workflows."""
import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
import streamlit as st

from src.client.agent_loop import openai_model, run_agent, schema_for
from src.client.fixture_model import PROMPT, fixture_model
from src.client.mcp_client import connect, discover, invoke

PROBES = {
    "Single-statement policy": ("query_database", {"sql_query": "SELECT 1; SELECT 2"}),
    "Arithmetic-only policy": ("calculate_expression", {"expression": "abs(-5)"}),
}


async def read_catalog():
    async with connect() as session:
        return [schema_for(tool) for tool in await discover(session)]


async def run(prompt, mode, key, model_name, publish, history):
    async with asyncio.timeout(80), connect() as session:
        if mode == "Scripted Seattle demo":
            return await run_agent(PROMPT, session, fixture_model, publish=publish)
        async with AsyncOpenAI(api_key=key, timeout=12, max_retries=0) as client:
            return await run_agent(prompt, session, openai_model(client, model_name),
                                   publish=publish, history=history)


async def probe(name, arguments):
    async with connect() as session:
        return await invoke(session, name, arguments)


def draw_timeline(events):
    for event in events:
        label = f"Turn {event['turn']} · {event['tool']}"
        if event["phase"] == "dispatch":
            st.text(f"{label} · dispatch")
            continue
        status = "Returned" if event["payload"].get("ok") else "Rejected or unavailable"
        with st.expander(f"{label} · {status} · {event['latency_ms']} ms"):
            st.caption(f"MCP call ID · {event['id']}")
            st.markdown("**Arguments**")
            st.json(event["args"])
            st.markdown("**Tool response**")
            st.json(event["payload"])


def main():
    load_dotenv()
    st.set_page_config(page_title="Logistics Operations Console", layout="wide")
    st.title("Logistics Operations Console")
    st.caption("Synthetic order and inventory data · MCP over stdio")
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("events", [])
    mode = st.sidebar.radio("Execution mode", ["Scripted Seattle demo", "OpenAI"])
    if st.session_state.get("previous_mode") != mode:
        st.session_state.history = []
        st.session_state.events = []
        st.session_state.previous_mode = mode
    key = os.getenv("OPENAI_API_KEY", "").strip()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    if mode == "OpenAI":
        st.sidebar.caption(f"Model · {model_name}")
        if not key:
            st.sidebar.info("Set OPENAI_API_KEY in your local .env file to enable live model calls.")
    else:
        st.sidebar.caption("Fixed tool sequence for the Seattle prompt. Weather still uses Open-Meteo.")
    try:
        if "catalog" not in st.session_state or st.sidebar.button("Refresh tool discovery"):
            st.session_state.catalog = asyncio.run(read_catalog())
        for tool in st.session_state.catalog:
            with st.sidebar.expander(tool["function"]["name"]):
                st.json(tool["function"])
    except Exception:
        st.sidebar.error("MCP discovery failed. Check the local environment and retry.")

    console, guardrails = st.tabs(["Operator console", "Security workbench"])
    with console:
        left, right = st.columns([3, 2])
        with left:
            if mode == "Scripted Seattle demo":
                st.code(PROMPT, language=None)
                prompt = PROMPT if st.button("Run Seattle scenario", type="primary") else None
            else:
                prompt = st.chat_input("Ask about an order, weather, or insurance", max_chars=3000, disabled=not key)
            transcript = st.container()
        with right:
            st.subheader("Tool call timeline")
            live = st.empty()
            log = st.container()
        if prompt:
            history = st.session_state.history[-6:] if mode == "OpenAI" else []
            st.session_state.history = [*history, {"role": "user", "content": prompt}]

            def publish(event):
                live.text(f"Turn {event['turn']} · {event['tool']} · {event['phase']}")

            try:
                outcome = asyncio.run(run(prompt, mode, key, model_name, publish, history))
                st.session_state.events = outcome.events
                st.session_state.history.append({"role": "assistant", "content": outcome.text})
            except Exception:
                st.session_state.events = []
                st.session_state.history.append({
                    "role": "assistant", "content": "The application could not complete this run. Retry after checking configuration."
                })
            live.empty()
        with transcript:
            for message in st.session_state.history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        with log:
            if not st.session_state.events:
                st.caption("Run a scenario to inspect tool calls.")
            draw_timeline(st.session_state.events)
    with guardrails:
        st.subheader("Test the tool boundary")
        st.caption("These checks send fixed inputs directly through MCP so the result comes from the tool.")
        option = st.selectbox("Guardrail check", PROBES)
        name, arguments = PROBES[option]
        st.json(arguments)
        if st.button("Run guardrail check"):
            try:
                st.json(asyncio.run(probe(name, arguments)))
                st.caption("Server response shown above.")
            except Exception:
                st.error("The workbench could not reach the MCP server.")


if __name__ == "__main__":
    main()
