from app.agents.base import AgentContext
from app.agents.planner import PlannerAgent


def test_planner_agent_replies_with_mock_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()

    context = AgentContext(
        task="what is 2+2?",
        history=[{"role": "user", "content": "what is 2+2?"}],
    )
    result = PlannerAgent().run(context)

    assert result.success is True
    assert "what is 2+2?" in result.output
    assert result.metadata["provider"] == "mock"
    assert result.metadata["turn"] == 1