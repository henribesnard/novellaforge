from app.services.memory_service import MemoryService


def test_merge_facts_updates_continuity():
    service = MemoryService.__new__(MemoryService)
    metadata = {
        "continuity": {
            "characters": [{"name": "Lena", "role": "hero", "status": "alive"}],
            "locations": [],
            "relations": [],
            "events": [],
        }
    }
    facts = {
        "summary": "Lena is injured.",
        "characters": [{"name": "Lena", "status": "injured"}],
        "locations": [{"name": "Dock", "description": "Foggy"}],
        "relations": [{"from": "Lena", "to": "Mark", "type": "ally", "detail": "trust"}],
        "events": [{"name": "Ambush", "summary": "Night attack"}],
    }

    updated = service.merge_facts(metadata, facts)
    continuity = updated["continuity"]

    assert continuity["characters"][0]["name"] == "Lena"
    assert continuity["characters"][0]["status"] == "injured"
    assert continuity["locations"][0]["name"] == "Dock"
    assert continuity["relations"][0]["type"] == "ally"
    assert continuity["events"][0]["name"] == "Ambush"
    assert "updated_at" in continuity


def test_build_context_block_formats_names():
    service = MemoryService.__new__(MemoryService)
    metadata = {
        "continuity": {
            "characters": [{"name": "Lena"}, {"name": "Mark"}],
            "locations": [{"name": "Dock"}],
            "relations": [{"from": "Lena", "to": "Mark", "type": "ally"}],
            "events": [{"name": "Ambush"}],
        }
    }

    block = service.build_context_block(metadata)

    assert "Characters: Lena, Mark" in block
    assert "Locations: Dock" in block
    assert "Relations: Lena -[ally]-> Mark" in block
    assert "Events: Ambush" in block
