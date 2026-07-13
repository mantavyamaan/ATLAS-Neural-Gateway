"""Regression tests for production-safety routing behaviour."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes import route_request
from app.api.schemas import RouteRequest
from app.core import feasibility
from app.core.router import route
from app.models.registry_builder import build_registry
from app.models.schemas import RequestConstraints


def test_complex_coding_enforces_frontier_and_policy_gated_verifier():
    registry = build_registry()
    decision = route(
        prompt=(
            "Review the entire codebase, design a production-ready multi-file "
            "architecture, implement the refactor, add integration tests, and "
            "resolve all security audit findings."
        ),
        estimated_tokens=4_000,
        estimated_output_tokens=4_000,
        registry=registry,
    )
    summary = decision.decision_record["task_summary"]
    assert summary["complexity"] == "high"
    assert decision.selected_plan is not None
    model_by_name = {model["name"]: model for model in registry}
    assert model_by_name[decision.selected_plan.selected_model]["tier"] == "Frontier"
    assert all(model_by_name[name]["tier"] == "Frontier" for name in decision.selected_plan.verifier_models)


def test_latency_budget_is_a_hard_feasibility_constraint():
    decision = route(
        prompt="Summarize this text.",
        estimated_tokens=1_000,
        estimated_output_tokens=500,
        request_constraints=RequestConstraints(max_latency_ms=1),
        registry=build_registry(),
    )
    assert decision.abstain is True
    assert decision.decision_record["status"] == "no_feasible_models"


def test_synthetic_registry_is_rejected_when_evidence_is_required(monkeypatch):
    monkeypatch.setattr(feasibility, "REQUIRE_MEASURED_EVIDENCE", True)
    decision = route(
        prompt="Summarize this text.",
        registry=build_registry(),
    )
    assert decision.abstain is True
    assert decision.decision_record["status"] == "no_feasible_models"
    assert set(decision.decision_record["feasibility_reasons"].values()) == {"insufficient_measured_evidence"}


def test_http_contract_rejects_unknown_fields_and_accepts_ui_constraints():
    payload = RouteRequest.model_validate({
        "prompt": "Summarize this.",
        "request_constraints": {"require_json": True, "max_latency_ms": 1_000},
    })
    assert payload.request_constraints is not None
    assert payload.request_constraints.require_json is True
    with pytest.raises(ValidationError):
        RouteRequest.model_validate({"prompt": "x", "constraints": {}})


def test_public_route_refuses_server_local_file_paths():
    with pytest.raises(HTTPException) as exc:
        route_request(RouteRequest(prompt="Read this", files=["C:/sensitive.txt"]))
    assert exc.value.status_code == 400
