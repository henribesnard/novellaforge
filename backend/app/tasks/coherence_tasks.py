"""Celery tasks for coherence maintenance."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.project import Project, ProjectStatus

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    name="promote_facts_to_bible",
    queue="maintenance_low",
    soft_time_limit=300,
    time_limit=360,
)
def promote_facts_to_bible(project_id: str) -> Dict[str, Any]:
    """
    Analyze fact frequency and promote recurring facts to Story Bible.

    This task examines facts extracted from chapters and promotes
    frequently occurring patterns to permanent story rules.
    """
    return _run_async(_promote_facts_to_bible_async(project_id))


async def _promote_facts_to_bible_async(project_id: str) -> Dict[str, Any]:
    """Async implementation of fact promotion."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return {"error": "Invalid project ID"}

    async with AsyncSessionLocal() as db:
        # Fetch project
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "Project not found"}

        metadata = project.project_metadata or {}
        continuity = metadata.get("continuity", {})
        story_bible = metadata.get("story_bible", {})

        # Initialize story_bible sections if needed
        if "characters" not in story_bible:
            story_bible["characters"] = []
        if "world_rules" not in story_bible:
            story_bible["world_rules"] = []
        if "locations" not in story_bible:
            story_bible["locations"] = []

        promotions = {
            "character_traits": [],
            "world_rules": [],
            "locations": [],
        }

        # Analyze character trait frequency
        characters = continuity.get("characters", [])
        trait_frequency = _analyze_character_traits(characters)

        for char_name, traits in trait_frequency.items():
            for trait, count in traits.items():
                if count >= settings.FACT_PROMOTION_THRESHOLD:
                    # Promote to story bible
                    _add_character_trait_to_bible(
                        story_bible, char_name, trait, count
                    )
                    promotions["character_traits"].append({
                        "character": char_name,
                        "trait": trait,
                        "frequency": count,
                    })

        # Analyze location rules frequency
        locations = continuity.get("locations", [])
        location_rules = _analyze_location_rules(locations)

        for loc_name, rules in location_rules.items():
            for rule, count in rules.items():
                if count >= settings.FACT_PROMOTION_THRESHOLD:
                    _add_location_rule_to_bible(
                        story_bible, loc_name, rule, count
                    )
                    promotions["locations"].append({
                        "location": loc_name,
                        "rule": rule,
                        "frequency": count,
                    })

        # Analyze recurring event patterns (potential world rules)
        events = continuity.get("events", [])
        world_rules = _extract_world_rules(events)

        for rule, count in world_rules.items():
            if count >= settings.FACT_PROMOTION_THRESHOLD:
                _add_world_rule_to_bible(story_bible, rule, count)
                promotions["world_rules"].append({
                    "rule": rule,
                    "frequency": count,
                })

        # Save updated story bible
        metadata["story_bible"] = story_bible
        metadata["story_bible_last_promotion"] = datetime.now(timezone.utc).isoformat()
        project.project_metadata = metadata
        await db.commit()

        logger.info(
            "Promoted facts to bible for project %s: %s",
            project_id, promotions
        )

        return {
            "success": True,
            "promotions": promotions,
            "total_promoted": sum(len(v) for v in promotions.values()),
        }


def _analyze_character_traits(
    characters: List[Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    """Count trait occurrences per character."""
    trait_counts: Dict[str, Dict[str, int]] = {}

    for char in characters:
        name = char.get("name", "")
        if not name:
            continue

        if name not in trait_counts:
            trait_counts[name] = {}

        # Count traits
        traits = char.get("traits", [])
        if isinstance(traits, list):
            for trait in traits:
                if isinstance(trait, str) and trait:
                    trait_counts[name][trait] = trait_counts[name].get(trait, 0) + 1

        # Count motivations as traits
        motivations = char.get("motivations", [])
        if isinstance(motivations, list):
            for mot in motivations:
                if isinstance(mot, str) and mot:
                    key = f"motivation:{mot}"
                    trait_counts[name][key] = trait_counts[name].get(key, 0) + 1

    return trait_counts


def _analyze_location_rules(
    locations: List[Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    """Count rule occurrences per location."""
    rule_counts: Dict[str, Dict[str, int]] = {}

    for loc in locations:
        name = loc.get("name", "")
        if not name:
            continue

        if name not in rule_counts:
            rule_counts[name] = {}

        rules = loc.get("rules", [])
        if isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, str) and rule:
                    rule_counts[name][rule] = rule_counts[name].get(rule, 0) + 1

    return rule_counts


def _extract_world_rules(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Extract potential world rules from recurring event patterns."""
    rule_counts: Dict[str, int] = {}

    # Look for patterns in events that suggest world rules
    for event in events:
        impact = event.get("impact", "")
        if isinstance(impact, str) and len(impact) > 20:
            # Normalize and count
            normalized = impact.lower().strip()
            rule_counts[normalized] = rule_counts.get(normalized, 0) + 1

    return rule_counts


def _add_character_trait_to_bible(
    story_bible: Dict[str, Any],
    character_name: str,
    trait: str,
    frequency: int,
) -> None:
    """Add a character trait to the story bible."""
    characters = story_bible.get("characters", [])

    # Find or create character entry
    char_entry = None
    for c in characters:
        if c.get("name", "").lower() == character_name.lower():
            char_entry = c
            break

    if not char_entry:
        char_entry = {
            "name": character_name,
            "traits": [],
            "auto_promoted": True,
        }
        characters.append(char_entry)

    # Add trait if not already present
    if "traits" not in char_entry:
        char_entry["traits"] = []

    existing_traits = [t.get("trait") if isinstance(t, dict) else t for t in char_entry["traits"]]

    if trait not in existing_traits:
        char_entry["traits"].append({
            "trait": trait,
            "source": "auto_promoted",
            "confidence": min(1.0, frequency / 10),
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        })

    story_bible["characters"] = characters


def _add_location_rule_to_bible(
    story_bible: Dict[str, Any],
    location_name: str,
    rule: str,
    frequency: int,
) -> None:
    """Add a location rule to the story bible."""
    locations = story_bible.get("locations", [])

    # Find or create location entry
    loc_entry = None
    for loc in locations:
        if loc.get("name", "").lower() == location_name.lower():
            loc_entry = loc
            break

    if not loc_entry:
        loc_entry = {
            "name": location_name,
            "rules": [],
            "auto_promoted": True,
        }
        locations.append(loc_entry)

    if "rules" not in loc_entry:
        loc_entry["rules"] = []

    existing_rules = [r.get("rule") if isinstance(r, dict) else r for r in loc_entry["rules"]]

    if rule not in existing_rules:
        loc_entry["rules"].append({
            "rule": rule,
            "source": "auto_promoted",
            "confidence": min(1.0, frequency / 10),
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        })

    story_bible["locations"] = locations


def _add_world_rule_to_bible(
    story_bible: Dict[str, Any],
    rule: str,
    frequency: int,
) -> None:
    """Add a world rule to the story bible."""
    world_rules = story_bible.get("world_rules", [])

    existing_rules = [r.get("rule") if isinstance(r, dict) else r for r in world_rules]

    if rule not in existing_rules:
        world_rules.append({
            "rule": rule,
            "source": "auto_promoted",
            "confidence": min(1.0, frequency / 10),
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        })

    story_bible["world_rules"] = world_rules


# Schedule periodic promotion
celery_app.conf.beat_schedule["daily-fact-promotion"] = {
    "task": "promote_all_project_facts",
    "schedule": timedelta(hours=settings.FACT_PROMOTION_SCHEDULE_HOURS),
}


@celery_app.task(name="promote_all_project_facts", queue="maintenance_low")
def promote_all_project_facts() -> Dict[str, Any]:
    """Promote facts for all active projects."""
    return _run_async(_promote_all_project_facts_async())


async def _promote_all_project_facts_async() -> Dict[str, Any]:
    """Async implementation of bulk fact promotion."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project).where(
                Project.status.in_([ProjectStatus.DRAFT, ProjectStatus.IN_PROGRESS])
            )
        )
        projects = result.scalars().all()

    results = []
    for project in projects:
        result = await _promote_facts_to_bible_async(str(project.id))
        results.append({
            "project_id": str(project.id),
            "result": result,
        })

    return {
        "projects_processed": len(projects),
        "results": results,
    }
