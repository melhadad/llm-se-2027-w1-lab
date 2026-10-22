"""Validated input and output contracts for issue triage."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Repo = Literal["litestar", "hono", "textual"]
IssueType = Literal["bug", "enhancement", "documentation", "question", "meta", "unknown"]
Severity = Literal["critical", "high", "medium", "low", "unknown"]

# Mirrors config/repos.toml; component names are local to each project.
COMPONENTS: dict[str, tuple[str, ...]] = {
    "litestar": ("openapi", "dto", "di", "testing", "cli"),
    "hono": ("middleware", "testing"),
    "textual": (),
}


class Issue(BaseModel):
    """Only intake fields survive validation; labels and gold data are discarded."""

    model_config = ConfigDict(strict=True, extra="ignore")
    repo: Repo
    number: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=1000)
    body: str = Field(default="", max_length=60000)

    @field_validator("repo", mode="before")
    @classmethod
    def normalize_repo(cls, value: object) -> object:
        if isinstance(value, str):
            return {
                "litestar-org/litestar": "litestar",
                "honojs/hono": "hono",
                "textualize/textual": "textual",
            }.get(value.lower(), value.lower())
        return value

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: object) -> object:
        return "" if value is None else value

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value


class Assessment(BaseModel):
    """Model output, validated before it can become a triage record."""

    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)
    issue_type: IssueType
    component: str | None = Field(max_length=80)
    severity: Severity
    has_reproduction_steps: bool | None
    summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)

    @field_validator("summary", "rationale")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class TriageRecord(Assessment):
    repo: Repo
    number: int = Field(gt=0)
    # Automatic routing must remain disabled until quality has been measured.
    needs_human_review: Literal[True] = True
