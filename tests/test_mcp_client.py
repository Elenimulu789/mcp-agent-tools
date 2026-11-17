import json
from types import SimpleNamespace

from src.client.agent_loop import FunctionCall, ToolCall, Turn, openai_model, run_agent, schema_for
from src.client.mcp_client import connect, discover, invoke


def call(id_, name, args):
    return Turn(tool_calls=[ToolCall(id=id_, function=FunctionCall(name=name, arguments=json.dumps(args)))])


async def test_stdio_discovery_and_direct_call():
    async with connect() as session:
        tools = {tool.name: schema_for(tool) for tool in await discover(session)}
        assert set(tools) == {"query_database", "get_current_weather", "calculate_expression"}
        assert tools["query_database"]["type"] == "function"
        assert tools["query_database"]["function"]["parameters"]["required"] == ["sql_query"]
        assert (await invoke(session, "calculate_expression", {"expression": "4 * 5"}))["result"] == "20"
        assert (await invoke(session, "absent", {}))["ok"] is False


async def test_two_tool_chain_matches_ids_and_terminates():
    count = 0

    async def model(messages, tools):
        nonlocal count
        count += 1
        assert len(tools) == 3
        if count == 1:
            return call("lookup", "query_database", {
                "sql_query": "SELECT total_cents FROM orders WHERE order_id = 4492"})
        if count == 2:
            assert messages[-1]["tool_call_id"] == "lookup"
            value = json.loads(messages[-1]["content"])["rows"][0][0]
            return call("math", "calculate_expression", {"expression": f"{value} / 100 * 0.035"})
        assert messages[-1]["tool_call_id"] == "math"
        result = json.loads(messages[-1]["content"])["result"]
        return Turn(content=f"Insurance is {result} USD.")

    async with connect() as session:
        outcome = await run_agent("Calculate insurance for order 4492", session, model)
    assert outcome.text == "Insurance is 86.975 USD."
    assert count == 3
    assert [item["role"] for item in outcome.messages] == [
        "system", "user", "assistant", "tool", "assistant", "tool", "assistant"]
    assert [event["phase"] for event in outcome.events] == ["dispatch", "result", "dispatch", "result"]


async def test_unknown_tool_reports_error_and_loop_is_bounded():
    counter = 0

    async def model(messages, _tools):
        nonlocal counter
        counter += 1
        if counter > 1:
            assert messages[-1]["role"] == "tool"
            assert not json.loads(messages[-1]["content"])["ok"]
        return call(f"unknown-{counter}", "absent", {})

    async with connect() as session:
        outcome = await run_agent("Test bounds", session, model, max_turns=2)
    assert counter == 2
    assert outcome.messages[-1]["role"] == "assistant"
    assert outcome.text.startswith("The run stopped")


async def test_openai_adapter_accepts_final_message_with_null_calls():
    async def create(**kwargs):
        assert kwargs["model"] == "gpt-4o-mini"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content="Finished", tool_calls=None))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    message = await openai_model(client, "gpt-4o-mini")([], [])
    assert message.content == "Finished"
    assert not message.tool_calls
