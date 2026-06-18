"""AI-powered subject categorization for CE listings.

Uses Claude Haiku to classify each listing into a dental subcategory.
Listings that aren't dental-related get tagged 'non_dental' and are
hidden from the public catalog by default (but kept in the database
for auditing and future scope expansion).

Cost: roughly $0.001 per listing with Claude Haiku 4.5.
Speed: ~1-2 seconds per call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from anthropic import Anthropic, APIError

from vetce.config import settings
from vetce.logging import log


# ============================================================
# Taxonomy
# ============================================================

# Slug -> display name. The AI is asked to return a slug.
# `non_dental` is the catch-all for content we exclude from the public catalog.
DENTAL_CATEGORIES: dict[str, str] = {
    "periodontics": "Periodontics",
    "endodontics": "Endodontics",
    "oral_surgery": "Oral Surgery",
    "prosthodontics_restorative": "Prosthodontics & Restorative",
    "orthodontics": "Orthodontics",
    "oral_pathology": "Oral Pathology",
    "anesthesia_pain": "Anesthesia & Pain Management",
    "imaging_radiology": "Imaging & Radiology",
    "dental_equipment": "Dental Equipment & Instruments",
    "patient_handling_workflow": "Patient Handling & Workflow",
    "exotic_specialty_dentistry": "Exotic & Specialty Dentistry",
    "general_dentistry": "General Dentistry",
    "non_dental": "Non-Dental",
}

VALID_SLUGS = set(DENTAL_CATEGORIES.keys())
NON_DENTAL_SLUG = "non_dental"
FALLBACK_SLUG = "general_dentistry"  # used when Claude returns something invalid


# ============================================================
# Prompt
# ============================================================

# Built once; same for every listing. Includes the full taxonomy with
# guidance for each category so Claude has consistent criteria.
SYSTEM_PROMPT = """You are classifying veterinary continuing education listings for a \
dental-focused CE aggregator. Your job is to decide whether a listing is relevant to \
veterinary dental practitioners and assign it to one of the categories below.

Be PERMISSIVE about what counts as dental. If dental work is a significant component \
of the listing — even if it's not the entire focus — it belongs in a dental category. \
A vet anesthesia course that covers dental procedures should be tagged \
'anesthesia_pain', not 'non_dental'. A general imaging course that includes intraoral \
radiography should be tagged 'imaging_radiology'.

Use 'non_dental' ONLY when the listing has no meaningful dental content — for example, \
a webinar on equine colic, or a practice-management course on staff retention with no \
mention of dental workflows.

CATEGORIES:

- periodontics: Gum disease, periodontal scaling, prophylaxis, gingivitis, root planing
- endodontics: Root canals, pulp therapy, endodontic procedures
- oral_surgery: Tooth extractions, oral oncology, jaw fractures, mandibulectomy, \
trauma repair
- prosthodontics_restorative: Crowns, fillings, composite restorations, vital pulp \
therapy preservation
- orthodontics: Malocclusion, bite correction, orthodontic appliances
- oral_pathology: Diagnostic biopsy, oral tumors, lesions, histopathology of dental \
tissues
- anesthesia_pain: Anesthesia or pain management with significant dental application
- imaging_radiology: Intraoral radiography, CBCT, dental imaging, full-mouth radiographs
- dental_equipment: Dental units, hand instruments, ultrasonic scalers, dental \
materials
- patient_handling_workflow: Patient positioning, dental hygiene protocols, scaling \
workflow, dental record-keeping
- exotic_specialty_dentistry: Dentistry for rabbits, rodents, ferrets, birds, reptiles, \
equine dentistry, large animal dentistry
- general_dentistry: Dental content that doesn't clearly fit one of the above, OR \
covers multiple dental topics broadly
- non_dental: No meaningful dental content

Respond with ONLY a JSON object, no other text:
{"category": "<slug>", "confidence": "<high|medium|low>", "reason": "<one short \
sentence>"}

The confidence field reflects how certain you are. Use "low" when the listing \
description is vague or you're guessing. Use "high" when the dental focus is explicit. \
The reason field is one short sentence justifying the choice."""


# ============================================================
# Data classes
# ============================================================

@dataclass(frozen=True, slots=True)
class TaggerResult:
    """One classification result for one listing."""
    category: str          # slug from DENTAL_CATEGORIES
    confidence: str        # "high" | "medium" | "low"
    reason: str            # one-sentence justification
    input_tokens: int      # for cost tracking
    output_tokens: int


# ============================================================
# Core function
# ============================================================

def classify_listing(
    title: str,
    description: str | None,
    *,
    client: Anthropic | None = None,
    model: str = "claude-haiku-4-5",
) -> TaggerResult:
    """Classify one listing into a dental subcategory.

    Args:
        title: The listing's title.
        description: The listing's description (may be None).
        client: Optional Anthropic client. If None, builds one from settings.
        model: Claude model to use. Default is Haiku for cost.

    Returns:
        TaggerResult with category, confidence, reason, and token usage.

    Raises:
        ValueError: if no API key is configured.
        APIError: if the Anthropic API returns an error.
    """
    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file before running the tagger."
        )

    if client is None:
        client = Anthropic(api_key=settings.anthropic_api_key)

    user_message = _build_user_message(title, description)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except APIError as e:
        log.error("tagger_api_error", error=str(e), title=title[:60])
        raise

    raw = response.content[0].text.strip()
    parsed = _parse_response(raw)

    return TaggerResult(
        category=parsed["category"],
        confidence=parsed["confidence"],
        reason=parsed["reason"],
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


# ============================================================
# Private helpers
# ============================================================

def _build_user_message(title: str, description: str | None) -> str:
    """Format the listing data for Claude.

    We deliberately don't pass other fields (provider, format, presenter)
    because they aren't strong signals for subject classification and
    add noise. Title + description is enough.
    """
    desc_text = (description or "").strip()
    if not desc_text:
        desc_text = "(no description available)"
    # Cap description length to limit tokens. Most CE descriptions are
    # under 2000 chars; truncating at 3000 catches outliers without
    # blowing up cost.
    if len(desc_text) > 3000:
        desc_text = desc_text[:3000] + "..."

    return (
        f"TITLE: {title.strip()}\n\n"
        f"DESCRIPTION: {desc_text}\n\n"
        "Classify this listing."
    )


def _parse_response(raw: str) -> dict:
    """Parse Claude's JSON response. Defensive against minor formatting issues.

    Returns a dict with keys: category, confidence, reason.
    Falls back to general_dentistry / non_dental on parse failure
    (depending on what's salvageable).
    """
    # Strip any markdown code fences Claude sometimes adds.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove ```json or ``` from start, ``` from end
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("tagger_parse_failed", raw=raw[:200])
        return {
            "category": FALLBACK_SLUG,
            "confidence": "low",
            "reason": "Failed to parse model response.",
        }

    category = parsed.get("category", FALLBACK_SLUG)
    if category not in VALID_SLUGS:
        log.warning("tagger_invalid_category", got=category, raw=raw[:200])
        category = FALLBACK_SLUG

    confidence = parsed.get("confidence", "low")
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    reason = parsed.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)
    reason = reason[:300]  # cap to avoid storing huge strings

    return {
        "category": category,
        "confidence": confidence,
        "reason": reason,
    }