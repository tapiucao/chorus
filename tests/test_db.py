import pytest
from sqlmodel import Session, SQLModel, create_engine
from core.models import Run, Artifact, ArtifactType, RunStatus
from db.operations import save_artifact
from core.schemas import ProjectSpec

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_save_artifact_and_run_status(session: Session):
    # Create run
    run = Run(mode="idea_spec", status=RunStatus.running)
    session.add(run)
    session.commit()
    session.refresh(run)
    
    # Mock spec
    spec = ProjectSpec(
        title="Test", core_intent="Vibe", problem_statement="P", target_users=["U"],
        user_value="V", success_criteria=["S"], assumptions=["A"], decisions=["D"],
        constraints=["C"], non_negotiables=["N"], non_goals=["NG"], options_considered=["O"],
        chosen_approach="C", functional_requirements=["F"], non_functional_requirements=["NF"],
        data_model_outline=["DMO"], interfaces=["I"], in_scope=["IS"], out_of_scope=["OOS"],
        maybe_later=["ML"], risks=["R"], open_questions=["OQ"], acceptance_criteria=["AC"]
    )
    
    # Save artifact
    artifact = save_artifact(session, run.id, ArtifactType.project_spec, spec)
    
    assert artifact.id is not None
    assert artifact.artifact_type == ArtifactType.project_spec
    assert artifact.schema_version == "1.0"
    assert artifact.payload["title"] == "Test"


def test_save_prompt_contract_payload(session: Session):
    run = Run(mode="idea_spec", status=RunStatus.running)
    session.add(run)
    session.commit()
    session.refresh(run)

    payload = {
        "stage": "critic",
        "primary_skill": "risk-review",
        "auxiliary_skill": "contradiction-audit",
        "responsibilities": ["Challenge assumptions."],
        "anti_patterns": ["Do not soften valid risks."],
        "system_prompt": "Base critic prompt.",
    }

    artifact = save_artifact(session, run.id, ArtifactType.prompt_contract, payload)

    assert artifact.id is not None
    assert artifact.artifact_type == ArtifactType.prompt_contract
    assert artifact.payload["stage"] == "critic"
    assert artifact.payload["system_prompt"] == "Base critic prompt."
