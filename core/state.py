from typing import TypedDict, Optional, List, Literal, Dict, Any
from .schemas import ProjectSpec, ImplementationSpec, OptionDraft, CritiqueReport

class CheckpointState(TypedDict):
    checkpoint_id: int
    status: Literal["pending", "approved", "rejected", "steered"]
    reason: Literal["human_review_requested", "option_selection_required"]
    artifact_type: Literal["options_draft", "project_spec", "implementation_spec"]
    expected_action: Literal["approve_or_reject", "select_option", "steer"]
    user_feedback: Optional[str]

class ChorusState(TypedDict):
    """
    Minimal, typed, and artifact-oriented state for LangGraph.
    """
    run_id: int
    mode: str # "idea_spec", "spec_impl", "full"
    
    # Status and Flow
    current_stage: str
    input_maturity: str # "raw", "partial", "mature"
    loop_count: int
    
    # HITL Checkpoints
    pending_checkpoint: Optional[CheckpointState]
    
    # Core Typed Artifacts
    raw_input: str
    exploration_draft: Optional[Dict[str, Any]] # Stores exploration without mutating raw_input
    project_spec: Optional[ProjectSpec]
    implementation_spec: Optional[ImplementationSpec]
    
    # Intermediate working memory (overwritten between stages)
    options_drafts: List[OptionDraft] 
    critique_reports: List[CritiqueReport]
