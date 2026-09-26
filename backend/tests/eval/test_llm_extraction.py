import pytest

from app.schemas.extraction import ExtractionEventSchema


def test_extraction_schema_valid_null():
    payload = {
        "event_type": None,
        "event_description": None,
    }
    parsed = ExtractionEventSchema(**payload)
    assert parsed.event_type is None


def test_extraction_schema_valid_provenance():
    payload = {
        "event_type": "MACHINE_FAILURE",
        "event_description": "Machine broken",
        "root_cause_candidate": {"value": "belt snapped", "provenance": "EXPLICIT"},
        "downtime_minutes": {"value": 15, "provenance": "MODEL_DERIVED"},
    }
    parsed = ExtractionEventSchema(**payload)
    assert parsed.event_type == "MACHINE_FAILURE"
    assert parsed.root_cause_candidate.provenance == "EXPLICIT"
    assert parsed.root_cause_candidate.value == "belt snapped"
    assert parsed.downtime_minutes.provenance == "MODEL_DERIVED"
    assert parsed.downtime_minutes.value == 15


def test_extraction_schema_invalid_empty_string():
    # Schema should reject invalid enums
    payload = {
        "event_type": "",
        "event_description": "Machine broken",
    }
    with pytest.raises(ValueError):
        ExtractionEventSchema(**payload)


def test_extraction_schema_root_cause_explicitness():
    # If the model infers a root cause, it should be marked as MODEL_DERIVED.
    payload = {
        "root_cause_candidate": {"value": "overheating", "provenance": "MODEL_DERIVED"}
    }
    parsed = ExtractionEventSchema(**payload)
    assert parsed.root_cause_candidate.provenance == "MODEL_DERIVED"
    assert parsed.root_cause_candidate.value == "overheating"
