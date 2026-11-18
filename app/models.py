from typing import Literal, Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, StringConstraints


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ScriptInput(InputModel):
    script: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=100_000)


class ProjectInput(ScriptInput):
    title: str = Field(min_length=1, max_length=120)
    narrator_id: UUID


class SegmentInput(InputModel):
    inference_text: str | None = Field(..., min_length=1, max_length=600)

    @field_validator("inference_text")
    @classmethod
    def has_words(cls, value):
        if value is not None and not any(c.isalnum() for c in value):
            raise ValueError("Include at least one letter or number.")
        return value


class TranscriptInput(InputModel):
    transcript: str = Field(min_length=1, max_length=4000)


class GenerateInput(InputModel):
    only_missing_or_stale: bool = True


class ExportSettings(InputModel):
    speed: float = Field(default=1.10, ge=.5, le=2.0)
    processed: bool = True
    enhance: bool = False
    gap_seconds: float = Field(default=.12, ge=0, le=.5)
    trim_trailing_silence: bool = False


class ExportInput(ExportSettings):
    format: Literal["wav", "mp3"] = "wav"
    include_segments: bool = False
    segment_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=2000)
