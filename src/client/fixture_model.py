"""A deterministic integration demo for the single documented Seattle scenario."""
import json
from src.client.agent_loop import FunctionCall, ToolCall, Turn

PROMPT = ("Check whether Seattle inventory can fulfill order #4492 for SKU-90210, "
          "look up current Seattle weather for dispatch, and calculate shipping insurance at 3.5%.")


def _call(call_id: str, name: str, **args) -> ToolCall:
    return ToolCall(id=call_id, function=FunctionCall(name=name, arguments=json.dumps(args)))


async def fixture_model(messages: list[dict], _tools: list[dict]) -> Turn:
    start = max(i for i, msg in enumerate(messages) if msg["role"] == "user")
    results = {msg["tool_call_id"]: json.loads(msg["content"])
               for msg in messages[start:] if msg["role"] == "tool"}
    if "stock" not in results:
        return Turn(tool_calls=[
            _call("stock", "query_database", sql_query=(
                "SELECT o.quantity, i.on_hand, o.total_cents FROM orders o "
                "JOIN inventory i ON i.city = o.city AND i.sku = o.sku WHERE o.order_id = 4492 "
                "AND o.city = 'Seattle' AND o.sku = 'SKU-90210'"
            )),
            _call("weather", "get_current_weather", city="Seattle"),
        ])
    stock = results["stock"]
    if not stock.get("ok") or not stock.get("rows"):
        return Turn(content="The fixture order or inventory could not be loaded.")
    quantity, on_hand, cents = stock["rows"][0]
    if "insurance" not in results:
        return Turn(tool_calls=[_call("insurance", "calculate_expression", expression=f"{cents} / 100 * 0.035")])
    weather = results.get("weather", {})
    conditions = (f'{weather["condition"]}, {weather["precipitation_mm"]} mm precipitation '
                  f'at {weather["time_utc"]}.' if weather.get("ok") else "Current conditions could not be verified.")
    insurance = results["insurance"].get("result")
    return Turn(content=f"""**Stock** · Seattle has {on_hand} units and the order needs {quantity}.
Fulfillment stock is {'sufficient' if on_hand >= quantity else 'insufficient'}.

**Dispatch weather** · {conditions} Check carrier guidance before dispatch.

**Insurance** · {f'${insurance} USD at 3.5%.' if insurance is not None else 'The calculation did not complete.'}""")
