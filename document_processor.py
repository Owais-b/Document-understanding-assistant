
import io
import json
import re

import requests
from jsonschema import ValidationError, validate

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"


SCHEMA = {
    "type": "object",
    "properties": {
        "document_name": {"type": "string"},
        "document_type": {
            "type": "string",
            "enum": [
                "Invoice / billing document",
                "Business report",
                "Contract / agreement",
                "General business document",
                "Other",
            ],
        },
        "summary": {"type": "string"},
        "entities": {
            "type": "object",
            "properties": {
                "people": {"type": "array", "items": {"type": "string"}},
                "organizations": {"type": "array", "items": {"type": "string"}},
                "dates": {"type": "array", "items": {"type": "string"}},
                "emails": {"type": "array", "items": {"type": "string"}},
                "amounts": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "people", "organizations", "dates", "emails", "amounts"
            ],
            "additionalProperties": False,
        },
        "summary_key_facts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "review_required": {"type": "boolean"},
    },
    "required": ["document_type", "summary", "entities"],
    "additionalProperties": False,
}


def extract_text(filename, content):
    """Extract text from TXT or PDF bytes."""
    if not content:
        return ""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    try:
        if extension == "txt":
            if isinstance(content, str):
                return content
            return content.decode("utf-8", errors="replace")

        if extension == "pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )

    except Exception:
        return ""

    return ""


def extract_entities(text):
    """Extract common entities using regular expressions."""
    if not text or not text.strip():
        return {
            "people": [],
            "organizations": [],
            "dates": [],
            "emails": [],
            "amounts": [],
        }

    emails = list(dict.fromkeys(re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text,
    )))

    date_pattern = (
        r"\b(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{4}-\d{1,2}-\d{1,2}"
        r"|\d{1,2}\s+(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+\d{4}"
        r")\b"
    )
    dates = list(dict.fromkeys(re.findall(date_pattern, text, re.I)))

    amounts = list(dict.fromkeys(re.findall(
        r"(?i)(?:INR\s*|Rs\.?\s*|₹\s*)[\d,]+(?:\.\d{1,2})?",
        text,
    )))

    organization_pattern = (
        r"\b[A-Z][A-Za-z0-9&.,' -]*?"
        r"(?:Pvt\.?\s*Ltd\.?|Private Limited|Limited|Ltd\.?|"
        r"LLP|LLC|Inc\.?|Foundation|Corporation|Corp\.?)\b"
    )
    organizations = list(dict.fromkeys(
        item.strip(" ,.")
        for item in re.findall(organization_pattern, text)
    ))

    excluded_names = {
        "Invoice", "Invoice Number", "Invoice Date", "Due Date",
        "Business Report", "Service Agreement", "Executive Summary",
        "Key Findings", "Payment Terms", "Total Amount",
        "General Business Document",
    }

    people = []
    person_pattern = (
        r"\b[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)?"
        r"\s+[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)?\b"
    )

    for item in re.findall(person_pattern, text):
        if item not in excluded_names and item not in organizations:
            if item not in people:
                people.append(item)

    return {
        "people": people,
        "organizations": organizations,
        "dates": dates,
        "emails": emails,
        "amounts": amounts,
    }


def classify_document(text):
    """Classify a document using simple keyword rules."""
    content = (text or "").lower()

    if any(word in content for word in [
        "invoice", "bill to", "invoice number", "amount due"
    ]):
        return "Invoice / billing document"

    if any(word in content for word in [
        "service agreement", "terms and conditions",
        "effective date", "contract", "agreement between"
    ]):
        return "Contract / agreement"

    if any(word in content for word in [
        "business report", "executive summary",
        "key findings", "support requests", "quarterly report"
    ]):
        return "Business report"

    return "General business document" if content.strip() else "Other"


def make_summary(text, entities=None):
    """Create a simple summary from the first three sentences."""
    if not text or not text.strip():
        return "No readable text"

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = " ".join(s.strip() for s in sentences[:3] if s.strip())

    if len(summary) > 1000:
        summary = summary[:997].rstrip() + "..."

    return summary


def normalize_document_type(document_type):
    content = str(document_type or "").strip().lower()

    if "invoice" in content or "billing" in content:
        return "Invoice / billing document"
    if "report" in content:
        return "Business report"
    if "contract" in content or "agreement" in content:
        return "Contract / agreement"
    if "general business" in content:
        return "General business document"
    if content == "other":
        return "Other"

    return "General business document"


def validate_data(data):
    """Validate structured output against the JSON schema."""
    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": ["The result must be a JSON object."],
        }

    try:
        validate(instance=data, schema=SCHEMA)
        return {"valid": True, "errors": []}
    except ValidationError as error:
        return {"valid": False, "errors": [error.message]}


def prepare_result(filename, text):
    """Build baseline output using rule-based extraction."""
    entities = extract_entities(text)

    key_facts = []
    for field in [
        "organizations", "dates", "amounts", "emails", "people"
    ]:
        for item in entities[field]:
            if item not in key_facts:
                key_facts.append(item)

    structured_data = {
        "document_name": filename,
        "document_type": classify_document(text),
        "summary": make_summary(text, entities),
        "entities": entities,
        "summary_key_facts": key_facts[:10],
        "review_required": False,
    }

    return structured_data


def format_result(data, text):
    """Return the fields expected by the Streamlit app."""
    return {
        "summary": data.get("summary", ""),
        "entities": data.get("entities", {}),
        "structured_data": data,
        "validation": validate_data(data),
        "text": text,
    }


def process_document(filename, content):
    """Run baseline document processing."""
    text = extract_text(filename, content)
    data = prepare_result(filename, text)
    return format_result(data, text)


def process_document_ai(filename, content):
    """Run document processing with the local Ollama model."""
    text = extract_text(filename, content)

    if not text.strip():
        data = prepare_result(filename, text)
        return format_result(data, text)

    prompt = f"""
Analyze this document and return JSON matching the supplied schema.

Extract:
- Document type
- Concise summary
- People
- Organizations
- Dates, preserving their original formatting
- Emails
- Monetary amounts, preserving their original formatting
- Important key facts

Do not invent information.
Set review_required to true when human verification is needed.
Set document_name to the supplied filename.

Filename: {filename}

Document:
{text}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0},
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        output = response.json().get("response", "")
        data = json.loads(output)

        data["document_name"] = data.get("document_name") or filename
        data["document_type"] = normalize_document_type(
            data.get("document_type", "")
        )

        entities = data.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        for field in [
            "people", "organizations", "dates", "emails", "amounts"
        ]:
            value = entities.get(field, [])
            if not isinstance(value, list):
                value = []
            entities[field] = [
                str(item) for item in value if item is not None
            ]

        data["entities"] = entities

        if not isinstance(data.get("summary"), str):
            data["summary"] = str(data.get("summary", ""))

        facts = data.get("summary_key_facts", [])
        if not isinstance(facts, list):
            facts = []
        data["summary_key_facts"] = [
            str(item) for item in facts if item is not None
        ]

        if not isinstance(data.get("review_required"), bool):
            data["review_required"] = True

        if not validate_data(data)["valid"]:
            data = prepare_result(filename, text)

        return format_result(data, text)

    except (
        requests.RequestException,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ):
        data = prepare_result(filename, text)
        return format_result(data, text)
