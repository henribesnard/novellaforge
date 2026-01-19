import json

import pytest

from app.services.agents.consistency_analyst import ConsistencyAnalyst
from app.services.agents import AgentFactory


@pytest.mark.asyncio
async def test_consistency_analyst_analyze_chapter_counts(monkeypatch):
    payload = {
        "contradictions": [{"severity": "critical"}],
        "timeline_issues": [{"severity": "high"}],
        "character_inconsistencies": [{"severity": "critical"}, {"severity": "low"}],
        "world_rule_violations": [],
    }

    async def fake_call_api(self, prompt, context=None, temperature=0.2, max_tokens=2000):
        return json.dumps(payload)

    monkeypatch.setattr(ConsistencyAnalyst, "_call_api", fake_call_api)
    agent = ConsistencyAnalyst()

    result = await agent.execute({"action": "analyze_chapter", "chapter_text": "Texte"})

    assert result["success"] is True
    assert result["total_issues"] == 4
    assert result["critical_count"] == 2


@pytest.mark.asyncio
async def test_consistency_analyst_analyze_project_returns_analysis(monkeypatch):
    payload = {"overall_project_coherence_score": 8}

    async def fake_call_api(self, prompt, context=None, temperature=0.3, max_tokens=2000):
        return json.dumps(payload)

    monkeypatch.setattr(ConsistencyAnalyst, "_call_api", fake_call_api)
    agent = ConsistencyAnalyst()

    result = await agent.execute({"action": "analyze_project", "all_chapters": []})

    assert result["success"] is True
    assert result["global_analysis"]["overall_project_coherence_score"] == 8


@pytest.mark.asyncio
async def test_consistency_analyst_suggest_fixes(monkeypatch):
    payload = {"fixes": [{"issue": "Issue", "recommendation": "minimal"}]}

    async def fake_call_api(self, prompt, context=None, temperature=0.4, max_tokens=2000):
        return json.dumps(payload)

    monkeypatch.setattr(ConsistencyAnalyst, "_call_api", fake_call_api)
    agent = ConsistencyAnalyst()

    result = await agent.execute({"action": "suggest_fixes", "issues": [{"description": "Issue"}]})

    assert result["success"] is True
    assert result["fixes"]["fixes"][0]["issue"] == "Issue"


def test_agent_factory_lists_consistency_analyst():
    assert "consistency_analyst" in AgentFactory.list_agent_types()
