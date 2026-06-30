"""
Compatibility scoring: calls an LLM (Anthropic API) to score tenant <-> listing
match from 0-100 with an explanation. Falls back to a rule-based score if the
LLM call fails or is unavailable, so the flow never breaks.
"""
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def build_prompt(listing, tenant_profile):
    return f"""Given this room listing: location={listing.location}, rent={listing.rent}, \
room_type={listing.room_type}, furnishing={listing.furnishing_status}, \
available_from={listing.available_from}.

And this tenant profile: preferred_location={tenant_profile.preferred_location}, \
budget_min={tenant_profile.budget_min}, budget_max={tenant_profile.budget_max}, \
move_in_date={tenant_profile.move_in_date}.

Compute a compatibility score from 0 to 100 based on budget and location match.
Return ONLY valid JSON, no other text: {{"score": number, "explanation": string}}"""


def rule_based_score(listing, tenant_profile):
    """Deterministic fallback: weighted budget overlap + location match."""
    score = 0
    reasons = []

    # Location match (50 points)
    if tenant_profile.preferred_location and listing.location:
        pref = tenant_profile.preferred_location.strip().lower()
        loc = listing.location.strip().lower()
        if pref == loc:
            score += 50
            reasons.append("exact location match")
        elif pref in loc or loc in pref:
            score += 30
            reasons.append("partial location match")
        else:
            reasons.append("location does not match preference")

    # Budget match (50 points)
    if tenant_profile.budget_min is not None and tenant_profile.budget_max is not None:
        if tenant_profile.budget_min <= listing.rent <= tenant_profile.budget_max:
            score += 50
            reasons.append("rent is within budget")
        else:
            budget_mid = (tenant_profile.budget_min + tenant_profile.budget_max) / 2
            diff_ratio = abs(listing.rent - budget_mid) / max(budget_mid, 1)
            partial = max(0, 50 - diff_ratio * 50)
            score += round(partial)
            reasons.append("rent is outside budget range")

    score = max(0, min(100, round(score)))
    explanation = f"Rule-based score: {', '.join(reasons)}."
    return score, explanation


def get_compatibility_score(listing, tenant_profile):
    """Returns (score, explanation, source) where source is 'llm' or 'fallback'."""
    api_key = current_app.config.get("LLM_API_KEY")
    if not api_key:
        score, explanation = rule_based_score(listing, tenant_profile)
        return score, explanation, "fallback"

    try:
        prompt = build_prompt(listing, tenant_profile)
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": current_app.config.get("LLM_MODEL", "claude-sonnet-4-6"),
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        ).strip()
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        score = int(parsed["score"])
        explanation = str(parsed["explanation"])
        score = max(0, min(100, score))
        return score, explanation, "llm"
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM scoring failed, using fallback: %s", exc)
        score, explanation = rule_based_score(listing, tenant_profile)
        return score, explanation, "fallback"
