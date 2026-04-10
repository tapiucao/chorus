import pytest
from pydantic import ValidationError
from core.schemas import OptionDraft, ProjectSpec
from agents.nodes import OptionsList, MaturityClassification

def test_maturity_classification_strict_literal():
    # Valid
    valid = MaturityClassification(maturity="raw", summary="test")
    assert valid.maturity == "raw"
    
    # Invalid
    with pytest.raises(ValidationError):
        MaturityClassification(maturity="semi-mature", summary="test")

def test_options_list_enforces_three_categories():
    draft = OptionDraft(
        id="1", title="A", summary="A", benefits=["A"], trade_offs=["A"],
        complexity="low", operational_risk="low", implementation_effort="low", alignment_with_vibe="Good"
    )
    
    # Missing scalable and minimal_cost
    with pytest.raises(ValidationError):
        OptionsList(simplest_viable=draft)
        
    # Valid
    valid = OptionsList(simplest_viable=draft, scalable=draft, minimal_cost=draft)
    assert valid.simplest_viable.id == "1"
