from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .security import validate_content

Paper = Literal["a4", "letter"]
BlockType = Literal[
    "profile_header", "contact", "social_links", "summary", "experience",
    "project", "education", "skills", "certifications", "awards",
    "publications", "languages", "custom_text", "custom_list", "divider",
]

MAX_TEXT = 10_000
MAX_BLOCKS = 80


class ResumeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    type: BlockType
    title: str = Field(min_length=1, max_length=120)
    visible: bool = True
    content: dict[str, Any] = Field(default_factory=dict)
    style: dict[str, str] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("content")
    @classmethod
    def content_is_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(str(value)) > MAX_TEXT:
            raise ValueError("block content is too large")
        validate_content(value)
        return value

    @field_validator("style")
    @classmethod
    def style_is_safe(cls, value: dict[str, str]) -> dict[str, str]:
        validate_content(value)
        if any(";" in item or "{" in item or "}" in item for item in value.values()):
            raise ValueError("block styles must be token values")
        return value


class ResumeColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    width: float = Field(gt=0, le=1)
    min_width: float = Field(gt=0, le=1)
    max_width: float = Field(gt=0, le=1)
    section_ids: list[str] = Field(default_factory=list, max_length=MAX_BLOCKS)

    @model_validator(mode="after")
    def valid_width_range(self) -> ResumeColumn:
        if self.min_width > self.width or self.width > self.max_width:
            raise ValueError("column width must be within its constraints")
        return self


class ResumeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    columns: list[ResumeColumn] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def widths_are_normalized(self) -> ResumeRow:
        total = sum(column.width for column in self.columns)
        if abs(total - 1) > 0.02:
            raise ValueError("column widths must add up to 1")
        if len({column.id for column in self.columns}) != len(self.columns):
            raise ValueError("column ids must be unique")
        return self


class ResumePage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    rows: list[ResumeRow] = Field(min_length=1, max_length=8)


class ResumeStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    font_family: Literal["inter", "arial", "georgia", "source_sans"] = "inter"
    font_size: float = Field(default=10, ge=8, le=16)
    accent_color: str = Field(default="#2563eb", pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str = Field(default="#1f2937", pattern=r"^#[0-9a-fA-F]{6}$")
    margin: float = Field(default=0.6, ge=0.25, le=1.25)
    spacing: float = Field(default=1, ge=0.5, le=2)
    density: Literal["comfortable", "compact"] = "comfortable"


class ResumeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    paper: Paper = "a4"
    pages: list[ResumePage] = Field(min_length=1, max_length=10)
    blocks: list[ResumeBlock] = Field(min_length=1, max_length=MAX_BLOCKS)
    style: ResumeStyle = Field(default_factory=ResumeStyle)

    @model_validator(mode="after")
    def layout_references_are_valid(self) -> ResumeDocument:
        block_ids = [block.id for block in self.blocks]
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("block ids must be unique")
        references = [section_id for page in self.pages for row in page.rows for column in row.columns for section_id in column.section_ids]
        if len(references) != len(set(references)):
            raise ValueError("a block can only appear once in the layout")
        if set(references) != set(block_ids):
            raise ValueError("layout must reference every block exactly once")
        for page in self.pages:
            for row in page.rows:
                if len(row.columns) > 1 and any(column.min_width >= 1 for column in row.columns):
                    raise ValueError("multi-column rows need resizable columns")
        return self


def validate_document(payload: dict[str, Any]) -> ResumeDocument:
    """Validate and normalize browser JSON before it reaches persistence/rendering."""
    return ResumeDocument.model_validate(payload)
