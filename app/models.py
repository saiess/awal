from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ScriptInput(InputModel):
    script: str = Field(min_length=1, max_length=100_000)


class ProjectInput(ScriptInput):
    title: str = Field(min_length=1, max_length=120)
    narrator_id: UUID


class SegmentInput(InputModel):
    text: str = Field(min_length=1, max_length=350)

    @field_validator("text")
    @classmethod
    def has_words(cls, value):
        if not any(c.isalnum() for c in value):
            raise ValueError("Include at least one letter or number.")
        return value


class GenerateInput(InputModel):
    only_missing_or_stale: bool = True


class ExportSettings(InputModel):
    speed: float = Field(default=1.10, ge=.5, le=2.0)
    processed: bool = True
    enhance: bool = False
    gap_seconds: float = Field(default=.12, ge=0, le=.5)


class ExportInput(ExportSettings):
    format: Literal["wav", "mp3"] = "wav"
    include_segments: bool = False
    segment_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=2000)
