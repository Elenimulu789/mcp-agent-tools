import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_discovers_tools_and_shows_rejection():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src" / "app.py"), default_timeout=15)
    app.run()
    assert not app.exception
    assert set(expander.label for expander in app.sidebar.expander) == {
        "query_database", "get_current_weather", "calculate_expression",
    }
    button = next(item for item in app.button if item.label == "Run guardrail check")
    button.click().run()
    assert not app.exception
    outputs = [json.loads(item.value) for item in app.json]
    assert any(item.get("code") == "sql_rejected" for item in outputs)
    app.selectbox[0].select("Arithmetic-only policy")
    button = next(item for item in app.button if item.label == "Run guardrail check")
    button.click().run()
    assert any(json.loads(item.value).get("code") == "math_rejected" for item in app.json)
