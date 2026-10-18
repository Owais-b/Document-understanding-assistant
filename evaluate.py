
import io
import json
import re
from pathlib import Path

from document_processor import process_document, process_document_ai

# --------------------------------------------------
# Configuration
# --------------------------------------------------

DATA_DIR = Path("data/evaluation_documents")
GROUND_TRUTH_PATH = DATA_DIR / "ground_truth.json"
RESULTS_PATH = DATA_DIR / "evaluation_results.json"

ENTITY_TYPES = [
    "people",
    "organizations",
    "dates",
    "emails",
    "amounts",
]


# --------------------------------------------------
# File wrapper
# --------------------------------------------------

class NamedBytesIO(io.BytesIO):
    """A file-like object that retains the original filename."""

    def __init__(self, content, name):
        super().__init__(content)
        self.name = name


# --------------------------------------------------
# Load ground truth
# --------------------------------------------------


def load_ground_truth():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as file:
        ground_truth = json.load(file)

    documents = ground_truth.get("documents", [])

    # Your ground-truth file stores documents as a list.
    if isinstance(documents, list):
        return {
            item["file"]: item
            for item in documents
            if isinstance(item, dict) and "file" in item
        }

    # Also support a dictionary format.
    if isinstance(documents, dict):
        return documents

    raise ValueError(
        "Invalid ground_truth.json: 'documents' must be a list or dictionary."
    )



# --------------------------------------------------
# Helpers for ground-truth fields
# --------------------------------------------------

def get_expected_type(expected):
    return (
        expected.get("document_type")
        or expected.get("expected_document_type")
        or expected.get("type")
        or "Other"
    )


def get_expected_entities(expected):
    entities = expected.get("entities", {})

    if not isinstance(entities, dict):
        entities = {}

    return {
        key: entities.get(key, expected.get(key, [])) or []
        for key in ENTITY_TYPES
    }


def get_summary_facts(expected):
    facts = (
        expected.get("summary_key_facts")
        or expected.get("key_facts")
        or expected.get("important_facts")
        or []
    )

    if isinstance(facts, str):
        return [facts]

    return facts


# --------------------------------------------------
# Entity evaluation
# --------------------------------------------------

def normalize_values(values):
    return {
        re.sub(r"\s+", " ", str(value).strip()).casefold()
        for value in values
        if str(value).strip()
    }


def evaluate_entities(expected_entities, predicted_entities):
    expected_all = set()
    predicted_all = set()
    details = {}

    for entity_type in ENTITY_TYPES:
        expected = normalize_values(
            expected_entities.get(entity_type, [])
        )
        predicted = normalize_values(
            predicted_entities.get(entity_type, [])
        )

        correct = expected & predicted
        missing = expected - predicted
        extra = predicted - expected

        details[entity_type] = {
            "expected": sorted(expected),
            "predicted": sorted(predicted),
            "correct": sorted(correct),
            "missing": sorted(missing),
            "extra": sorted(extra),
        }

        # Include entity type so different categories are not conflated.
        expected_all.update(
            (entity_type, value) for value in expected
        )
        predicted_all.update(
            (entity_type, value) for value in predicted
        )

    true_positives = len(expected_all & predicted_all)
    false_positives = len(predicted_all - expected_all)
    false_negatives = len(expected_all - predicted_all)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives else 1.0
    )

    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives else 1.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "entity_details": details,
    }


# --------------------------------------------------
# Summary evaluation
# --------------------------------------------------

def evaluate_summary(summary, key_facts):
    summary_lower = str(summary).casefold()

    found = [
        fact for fact in key_facts
        if str(fact).casefold() in summary_lower
    ]

    missing = [
        fact for fact in key_facts
        if str(fact).casefold() not in summary_lower
    ]

    coverage = len(found) / len(key_facts) if key_facts else 1.0

    return {
        "key_facts_found": found,
        "key_facts_missing": missing,
        "key_fact_coverage": round(coverage, 4),
        "note": (
            "This is a simple text-match measure, not a complete "
            "assessment of summary quality. Paraphrased facts require "
            "human review."
        ),
    }


# --------------------------------------------------
# Evaluate one processing method
# --------------------------------------------------

def evaluate_method(processor, file_path, expected):
    content = file_path.read_bytes()
    uploaded_file = NamedBytesIO(content, file_path.name)

    output = processor(uploaded_file)

    # Current document_processor.py returns a wrapper containing data.
    result = output.get("data", output)
    validation = output.get("validation", {})

    expected_type = get_expected_type(expected)
    predicted_type = result.get("document_type", "")

    expected_entities = get_expected_entities(expected)
    predicted_entities = result.get("entities", {})

    return {
        "document_type": {
            "expected": expected_type,
            "predicted": predicted_type,
            "correct": (
                str(expected_type).strip().casefold()
                == str(predicted_type).strip().casefold()
            ),
        },
        "entities": evaluate_entities(
            expected_entities,
            predicted_entities,
        ),
        "summary": evaluate_summary(
            result.get("summary", ""),
            get_summary_facts(expected),
        ),
        "schema_valid": validation.get("valid", False),
        "review_required": result.get("review_required", False),
    }


# --------------------------------------------------
# Main evaluation
# --------------------------------------------------

def main():
    ground_truth = load_ground_truth()
    results = {
        "dataset": "Arrowstack Project 2 Synthetic Evaluation Dataset",
        "documents": {},
        "notes": [
            "Synthetic evaluation dataset.",
            "Entity scores use case-insensitive exact string matching.",
            "Summary key-fact coverage is a simple text-match measure.",
            "Review errors and paraphrases manually before drawing conclusions.",
        ],
    }

    for filename, expected in ground_truth.items():
        if not isinstance(expected, dict):
            print(f"Skipping invalid ground-truth entry: {filename}")
            continue

        file_path = DATA_DIR / filename

        if not file_path.is_file():
            print(f"Skipping missing document: {file_path}")
            continue

        print(f"\nEvaluating: {filename}")

        results["documents"][filename] = {}

        for method_name, processor in [
            ("baseline", process_document),
            ("local_ai", process_document_ai),
        ]:
            try:
                evaluation = evaluate_method(
                    processor,
                    file_path,
                    expected,
                )

                results["documents"][filename][method_name] = evaluation

                print(
                    f"  {method_name}: "
                    f"schema_valid={evaluation['schema_valid']}, "
                    f"entity_F1={evaluation['entities']['f1']:.4f}, "
                    f"type_correct={evaluation['document_type']['correct']}, "
                    f"summary_coverage="
                    f"{evaluation['summary']['key_fact_coverage']:.2%}"
                )

            except Exception as error:
                results["documents"][filename][method_name] = {
                    "error": str(error)
                }
                print(f"  {method_name} ERROR: {error}")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
