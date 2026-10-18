from document_processor import extract_entities, make_summary, validate_data

def test_extracts_email_date_and_amount():
    text = "Invoice date: 12/09/2026. Contact billing@example.com. Amount due: ₹1,250.00"
    entities = extract_entities(text)
    assert "billing@example.com" in entities["emails"]
    assert "12/09/2026" in entities["dates"]
    assert any("1,250.00" in amount for amount in entities["amounts"])

def test_summary_empty_text():
    assert "No readable text" in make_summary("   ")

def test_schema_validation_passes_for_valid_data():
    data = {
        "document_name": "sample.txt",
        "document_type": "General business document",
        "summary": "A sample document.",
        "entities": {
            "people": [], "organizations": [], "dates": [],
            "emails": [], "amounts": []
        },
        "review_required": True
    }
    assert validate_data(data)["valid"] is True
