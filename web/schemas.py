from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Request payload for creating a new Chorus run."""

    mode: Literal["idea_spec", "spec_impl", "full"] = Field(default="idea_spec")
    idea: str = Field(..., min_length=1, max_length=10_000)
