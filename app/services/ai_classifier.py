"""
AI-powered ticket classification service.

Uses Google Gemini API when AI_API_KEY is configured, otherwise falls back to
rule-based keyword classification.
"""

import json
import re

import httpx

from app import AI_CLASSIFICATION_ENABLED, AI_API_KEY, AI_API_URL, AI_MODEL
from app.schemas.schemas import ClassificationResult

VALID_CATEGORIES = [
    "billing", "technical", "account", "general",
    "feature_request", "bug", "security",
]

VALID_PRIORITIES = ["low", "medium", "high", "critical"]

# ── Keyword-based fallback classifier ─────────────────

KEYWORD_RULES: dict[str, list[str]] = {
    "billing": [
        r"\bbill(?:ing|s)?\b", r"\bpayment\b", r"\binvoic", r"\brefund\b",
        r"\bcharge\b", r"\bsubscription\b", r"\bpric", r"\bcost\b",
    ],
    "technical": [
        r"\berror\b", r"\bbug\b", r"\bcrash(?:es)?\b", r"\bnot work",
        r"\bfail(?:ed|ure)?\b", r"\bbroken\b", r"\binstall", r"\bconfig",
        r"\bserver\b", r"\btimeout\b", r"\bconnection\b",
    ],
    "account": [
        r"\baccount\b", r"\blogin\b", r"\bpassword\b", r"\breset\b",
        r"\baccess\b", r"\bauth(?:orization|enticate)?\b", r"\bregister",
        r"\bsign[\s-]?up\b", r"\bprofil",
    ],
    "security": [
        r"\bsecurity\b", r"\bhack\b", r"\bbreach\b", r"\bvulnerabilit",
        r"\bmalware\b", r"\bphish", r"\bunauthoriz",
    ],
    "feature_request": [
        r"\bfeature\b", r"\brequest\b", r"\bwould like\b", r"\bsuggest",
        r"\benhanc", r"\bimprov", r"\bwish\b", r"\bcould you add\b",
    ],
    "bug": [
        r"\bbug\b", r"\bissue\b", r"\bdefect\b", r"\bglitch\b",
        r"\bunexpected\b", r"\breproducib",
    ],
}

PRIORITY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        r"\burgent\b", r"\bcritical\b", r"\bemergency\b", r"\bdown\b",
        r"\bproduction\b", r"\boutage\b", r"\bdata loss\b",
    ],
    "high": [
        r"\bimportant\b", r"\bhigh\b", r"\bblocked\b", r"\bblock(?:ing)?\b",
        r"\bdeadline\b",
    ],
    "low": [
        r"\blow\b", r"\bminor\b", r"\bwhenever\b", r"\bno rush\b",
        r"\btrivial\b",
    ],
}


def _keyword_classify(title: str, description: str) -> ClassificationResult:
    text = f"{title} {description}".lower()

    best_category = "general"
    best_score = 0

    for category, patterns in KEYWORD_RULES.items():
        score = sum(1 for p in patterns if re.search(p, text))
        if score > best_score:
            best_score = score
            best_category = category

    # Priority detection
    priority = "medium"
    for prio, patterns in PRIORITY_KEYWORDS.items():
        if any(re.search(p, text) for p in patterns):
            priority = prio
            break

    confidence = min(0.5 + best_score * 0.1, 0.95) if best_score > 0 else 0.4

    return ClassificationResult(
        category=best_category,
        confidence=round(confidence, 2),
        priority=priority,
        analysis=f"Rule-based classification: matched {best_score} keyword(s) for '{best_category}'",
    )


# ── AI-powered classifier using Google Gemini API ─────

async def _ai_classify(title: str, description: str) -> ClassificationResult | None:
    if not AI_API_KEY:
        return None

    prompt = f"""Analyze this customer support ticket and classify it.

Title: {title}
Description: {description}

Respond with ONLY a JSON object in exactly this format (no markdown, no code fences, no extra text):
{{"category": "one of: billing, technical, account, general, feature_request, bug, security", "priority": "one of: low, medium, high, critical", "confidence": 0.85, "analysis": "brief 1-2 sentence explanation"}}"""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{AI_MODEL}:generateContent?key={AI_API_KEY}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 300,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract text from Gemini response structure
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            ).strip()

            # Strip markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            result = json.loads(text)

            category = result.get("category", "general")
            if category not in VALID_CATEGORIES:
                category = "general"

            priority = result.get("priority", "medium")
            if priority not in VALID_PRIORITIES:
                priority = "medium"

            return ClassificationResult(
                category=category,
                confidence=float(result.get("confidence", 0.7)),
                priority=priority,
                analysis=result.get("analysis", ""),
            )
    except Exception:
        return None


# ── Public interface ──────────────────────────────────

async def classify_ticket(title: str, description: str) -> ClassificationResult | None:
    if not AI_CLASSIFICATION_ENABLED:
        return None

    # Try AI first, fall back to keywords
    result = await _ai_classify(title, description)
    if result:
        return result

    return _keyword_classify(title, description)
