"""
FastAPI routes exposing the ATLAS Neural Gateway as a service.

Endpoints:
    POST /route          -> run the full routing pipeline, return a RoutingDecision
    POST /outcome         -> feed an observed outcome back into Bayesian priors
    GET  /models           -> list the canonical registry (summary view)
    GET  /models/{name}     -> full registry entry for one model
    GET  /health              -> liveness/readiness probe
    GET  /versions              -> current version stamps for every subsystem
"""

import threading
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Depends

from app.api.schemas import (
    ExecutionPlanOut,
    ModelSummaryOut,
    OutcomeIn,
    RequestConstraintsIn,
    RouteRequest,
    RouteResponse,
    StageRouteOut,
    TenantContextIn,
    FeedbackRequest,
)
from app.config import (
    CALIBRATION_VERSION,
    DEFAULT_ALLOWED_PROVIDERS,
    LLM_PARSER_ENABLED,
    PARSER_VERSION,
    POLICY_VERSION,
    REGISTRY_VERSION,
    ROUTER_VERSION,
    SCORING_VERSION,
    TELEMETRY_SNAPSHOT_VERSION,
    ADMIN_API_KEY,
    ALLOW_SERVER_FILE_PATHS,
)
from app.core.formatting import format_decision_summary
from app.core.llm_parser import call_llm_parser
from app.core.router import record_outcome, route
from app.core.database import get_all_models, get_model, upsert_model, delete_model, add_feedback
from app.models.schemas import RequestConstraints, TenantContext

router = APIRouter()

# A threading lock to protect read-modify-write cycles in /outcome and /models.
# For multi-worker deployments, this should be a distributed lock or handled natively in SQL.
_write_lock = threading.Lock()


def _require_admin(x_atlas_admin_key: Optional[str] = Header(default=None)) -> None:
    """Protect mutable control-plane endpoints with a configured secret."""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Model mutation is disabled: ATLAS_ADMIN_API_KEY is not configured")
    if x_atlas_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid administrative API key")


def _to_request_constraints(rc_in: Optional[RequestConstraintsIn]) -> RequestConstraints:
    if rc_in is None:
        rc = RequestConstraints()
    else:
        rc = RequestConstraints(**rc_in.model_dump())
    # Apply the ATLAS_ALLOWED_PROVIDERS env-var default when the caller didn't
    # set its own filter. Per-request `allowed_providers` always wins.
    if rc.allowed_providers is None and DEFAULT_ALLOWED_PROVIDERS:
        rc.allowed_providers = list(DEFAULT_ALLOWED_PROVIDERS)
    return rc


def _to_tenant_context(tc_in: Optional[TenantContextIn]) -> TenantContext:
    if tc_in is None:
        return TenantContext()
    return TenantContext(**tc_in.model_dump())


def _strip_noise(record: Dict[str, Any]) -> Dict[str, Any]:
    # Trim per-model dumps from the response — callers only need the
    # primary + fallbacks + verifiers, not the full list of rejected or
    # simulated candidates. Removes:
    #   - confidence.win_probabilities  (Thompson-Sampling per-model dict)
    #   - pipeline_trace.feasibility_exclusions (rejected models + reason)
    #   - pipeline_trace.policy_exclusions      (policy-rejected models)
    # Counts (registry_models, after_pareto, etc.) stay for observability.
    scrubbed = dict(record)
    conf = scrubbed.get("confidence")
    if isinstance(conf, dict) and "win_probabilities" in conf:
        scrubbed["confidence"] = {k: v for k, v in conf.items() if k != "win_probabilities"}
    pt = scrubbed.get("pipeline_trace")
    if isinstance(pt, dict):
        scrubbed["pipeline_trace"] = {
            k: v for k, v in pt.items()
            if k not in ("feasibility_exclusions", "policy_exclusions")
        }
    return scrubbed


def _plan_to_out(plan) -> Optional[ExecutionPlanOut]:
    if plan is None:
        return None
    trace = {k: v for k, v in plan.trace.items() if k != "win_probabilities"}
    return ExecutionPlanOut(
        plan_id=plan.plan_id,
        plan_type=plan.plan_type,
        selected_model=plan.selected_model,
        stage_routes=[StageRouteOut(**asdict(sr)) for sr in plan.stage_routes],
        fallback_models=plan.fallback_models,
        verifier_models=plan.verifier_models,
        expected_latency_ms=plan.expected_latency_ms,
        expected_cost_usd=plan.expected_cost_usd,
        expected_quality=plan.expected_quality,
        confidence=plan.confidence,
        utility=plan.utility,
        confidence_margin=plan.confidence_margin,
        profile_used=plan.profile_used,
        explanation=plan.explanation,
        trace=trace,
    )


@router.post("/route", response_model=RouteResponse)
def route_request(payload: RouteRequest) -> RouteResponse:
    if payload.files and not ALLOW_SERVER_FILE_PATHS:
        raise HTTPException(
            status_code=400,
            detail="Server-local file paths are disabled; upload artifacts to a managed store and pass trusted IDs instead.",
        )
    try:
        decision = route(
                prompt=payload.prompt,
                input_formats=payload.input_formats,
                estimated_tokens=payload.estimated_tokens,
                estimated_output_tokens=payload.estimated_output_tokens,
                artifact_hints=payload.artifact_hints,
                request_constraints=_to_request_constraints(payload.request_constraints),
                tenant_context=_to_tenant_context(payload.tenant_context),
                files=payload.files,
                profile_name=payload.profile_name,
                shadow_model=payload.shadow_model,
                registry=get_all_models(),
                llm_parser=call_llm_parser,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RouteResponse(
        abstain=decision.abstain,
        escalate_to_human=decision.escalate_to_human,
        selected_plan=_plan_to_out(decision.selected_plan),
        decision_record=_strip_noise(decision.decision_record),
        summary_text=format_decision_summary(decision),
    )


@router.post("/outcome", status_code=202)
def record_outcome_route(payload: OutcomeIn, _: None = Depends(_require_admin)) -> Dict[str, str]:
    with _write_lock:
        models = get_all_models()
        if not any(m["name"] == payload.model_name for m in models):
            raise HTTPException(status_code=404, detail=f"Unknown model: {payload.model_name}")
        record_outcome(
            registry=models,
            model_name=payload.model_name,
            task_family=payload.task_family,
            success=payload.success,
            quality_score=payload.quality_score,
            latency_ms=payload.latency_ms,
            cost_usd=payload.cost_usd,
            user_accepted=payload.user_accepted,
            safety_flagged=payload.safety_flagged,
        )
        updated_model = next(m for m in models if m["name"] == payload.model_name)
        upsert_model(updated_model)
    return {"status": "accepted"}


@router.get("/models", response_model=List[ModelSummaryOut])
def list_models() -> List[ModelSummaryOut]:
    return [
        ModelSummaryOut(
            name=str(m.get("name", "")),
            provider=str(m.get("provider", "")),
            tier=str(m.get("tier", "")),
            status=m.get("status", "unknown"),
            open_weight=m.get("open_weight", False),
            context_window=(m.get("context") or {}).get("window", 0),
            relative_cost_score=(m.get("pricing") or {}).get("relative_cost_score", 0.0),
            incident_status=(m.get("ops_dynamic") or {}).get("incident_status", "none"),
        )
        for m in get_all_models()
    ]


@router.get("/models/{name}")
def get_model_route(name: str) -> Dict[str, Any]:
    m = get_model(name)
    if not m:
        raise HTTPException(status_code=404, detail=f"Unknown model: {name}")
    return m


@router.post("/models", status_code=201)
def create_or_update_model(payload: Dict[str, Any], _: None = Depends(_require_admin)) -> Dict[str, str]:
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="Model must have a 'name'")
    required_keys = ["provider", "tier", "ops_dynamic", "pricing", "context", "priors"]
    missing = [k for k in required_keys if k not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {missing}")
    
    with _write_lock:
        upsert_model(payload)
    return {"status": "success", "message": f"Model {payload['name']} upserted."}


@router.delete("/models/{name}", status_code=204)
async def delete_model_route(name: str, _: None = Depends(_require_admin)) -> None:
    if not delete_model(name):
        raise HTTPException(status_code=404, detail=f"Unknown model: {name}")


@router.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/versions")
async def versions() -> Dict[str, str]:
    return {
        "router_version": ROUTER_VERSION,
        "parser_version": PARSER_VERSION,
        "policy_version": POLICY_VERSION,
        "scoring_version": SCORING_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "registry_version": REGISTRY_VERSION,
        "telemetry_snapshot_version": TELEMETRY_SNAPSHOT_VERSION,
    }


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest) -> Dict[str, str]:
    """Submit parser correction feedback to update the dynamic memory bank."""
    add_feedback(req.prompt, req.correct_family)
    return {"status": "success", "message": "Feedback integrated into memory bank"}
