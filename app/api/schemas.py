"""
Pydantic request/response contracts for the FastAPI layer.

These are intentionally separate from app/models/schemas.py (the internal
dataclasses). Keeping the HTTP contract distinct from the internal pipeline
representation means the API shape can evolve independently of routing
internals, and vice versa.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequestConstraintsIn(StrictModel):
    allowed_providers: Optional[List[str]] = None
    disallowed_providers: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    no_open_weight: bool = False
    required_region: Optional[str] = None
    max_cost_usd: Optional[float] = Field(default=None, gt=0)
    max_latency_ms: Optional[float] = Field(default=None, gt=0)
    mandatory_verifier: bool = False
    no_web_access: bool = False
    must_use_single_model: bool = False
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    require_json: bool = False
    require_ocr: bool = False
    require_web_search: bool = False
    require_citations: bool = False


class TenantContextIn(StrictModel):
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    allowed_models: Optional[List[str]] = None
    budget_remaining_usd: Optional[float] = None
    policy_overlay: Optional[Dict[str, Any]] = None


class RouteRequest(StrictModel):
    prompt: str = Field(..., description="The user's raw request/prompt.")
    input_formats: Optional[List[str]] = Field(
        default=None,
        description="Modalities present, e.g. ['pdf','text']. Ignored if `files` is set.",
    )
    estimated_tokens: int = Field(default=2000, ge=1, le=2_000_000)
    estimated_output_tokens: int = Field(default=1200, ge=1, le=500_000)
    artifact_hints: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Ground-truth overrides per format, e.g. [{'format':'pdf','page_count':45}].",
    )
    request_constraints: Optional[RequestConstraintsIn] = None
    tenant_context: Optional[TenantContextIn] = None
    files: Optional[List[str]] = Field(
        default=None,
        description="Server-local file paths to inspect (already uploaded).",
    )
    profile_name: str = "balanced"
    shadow_model: Optional[str] = None

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "Implement a concurrent web crawler in Python with rate limiting and structured JSON output.",
                "input_formats": ["text"],
                "estimated_tokens": 3000,
                "estimated_output_tokens": 4000,
                "profile_name": "balanced",
            }
        },
    )


class StageRouteOut(StrictModel):
    stage_id: int
    stage_name: str
    selected_model: str
    fallback_models: List[str]
    verifier_models: List[str]
    stage_confidence: float
    expected_latency_ms: float
    expected_cost_usd: float
    explanation: str


class ExecutionPlanOut(StrictModel):
    plan_id: str
    plan_type: str
    selected_model: Optional[str]
    stage_routes: List[StageRouteOut]
    fallback_models: List[str]
    verifier_models: List[str]
    expected_latency_ms: float
    expected_cost_usd: float
    expected_quality: float
    confidence: float
    utility: float
    confidence_margin: float
    profile_used: str
    explanation: Dict[str, Any]
    trace: Dict[str, Any]


class RouteResponse(StrictModel):
    abstain: bool
    escalate_to_human: bool
    selected_plan: Optional[ExecutionPlanOut]
    decision_record: Dict[str, Any]
    summary_text: str


class OutcomeIn(StrictModel):
    model_name: str
    task_family: str
    success: bool
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    user_accepted: bool = True
    safety_flagged: bool = False


class ModelSummaryOut(StrictModel):
    name: str
    provider: str
    tier: str
    status: str
    open_weight: bool
    context_window: int
    relative_cost_score: float
    incident_status: str


class FeedbackRequest(BaseModel):
    """Payload for submitting feedback on parser routing."""
    prompt: str = Field(..., description="The user's original prompt.")
    correct_family: str = Field(..., description="The correct routing family.")
