"""
Feasibility & Hard Constraint Filtering.

Removes candidate models that cannot satisfy mandatory requirements —
modalities, capabilities, context window, provider/tier restrictions,
tenant allowlists, region, and budget — before any scoring happens.
A model that fails here is eliminated regardless of benchmark strength
(see Core Design Principle #1: hard constraints override soft preferences).
"""

from copy import deepcopy
from typing import Any, Dict, List, Tuple

from app.core.scoring import estimate_request_cost_usd
from app.core.scoring import estimate_request_latency_ms
from app.config import REQUIRE_MEASURED_EVIDENCE
from app.models.schemas import TaskFeatures


def feasibility_filter(
    task: TaskFeatures,
    registry: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    feasible = []
    reasons = {}
    rc = task.request_constraints
    tc = task.tenant_context

    for model in registry:
        name = model["name"]

        if model.get("status") != "active" or not model.get("api_available", False):
            reasons[name] = "inactive_or_no_api"
            continue
        evidence = model.get("evidence", {})
        if REQUIRE_MEASURED_EVIDENCE and not evidence.get("eligible_for_auto_route", False):
            reasons[name] = "insufficient_measured_evidence"
            continue
        if model["ops_dynamic"].get("incident_status") == "red":
            reasons[name] = "runtime_incident_red"
            continue
        if rc.allowed_providers:
            allowed_lower = [p.lower() for p in rc.allowed_providers]
            if model["provider"].lower() not in allowed_lower:
                reasons[name] = "provider_not_allowed"
                continue
        if rc.disallowed_providers:
            disallowed_lower = [p.lower() for p in rc.disallowed_providers]
            if model["provider"].lower() in disallowed_lower:
                reasons[name] = "provider_disallowed"
                continue
        if rc.allowed_tiers and model["tier"] not in rc.allowed_tiers:
            reasons[name] = "tier_not_allowed"
            continue
        if rc.no_open_weight and model.get("open_weight", False):
            reasons[name] = "open_weight_disallowed"
            continue
        if tc.allowed_models and name not in tc.allowed_models:
            reasons[name] = "tenant_model_not_allowed"
            continue
        if rc.required_region:
            regions = model.get("allowed_regions", [])
            if rc.required_region not in regions and "global" not in regions:
                reasons[name] = "region_not_supported"
                continue

        mods = model["modalities"]
        caps = model["capabilities"]
        ctx = model["context"]

        missing_fmt = [f for f in task.required_formats if not mods.get(f, False)]
        if missing_fmt:
            reasons[name] = f"missing_format:{','.join(missing_fmt)}"
            continue
        if task.requires_json and not caps.get("json_mode", False):
            reasons[name] = "missing_json_mode"
            continue
        if task.requires_function_calling and not caps.get("function_calling", False):
            reasons[name] = "missing_function_calling"
            continue
        if task.requires_web_search and not caps.get("web_search", False):
            reasons[name] = "missing_web_search"
            continue
        if task.requires_ocr and not caps.get("ocr", False):
            reasons[name] = "missing_ocr"
            continue
        if task.requires_citations and not caps.get("citation_support", False):
            reasons[name] = "missing_citation_support"
            continue
        if task.requires_image_generation and not caps.get("image_generation", False):
            reasons[name] = "missing_image_generation"
            continue
        if task.requires_video_generation and not caps.get("video_generation", False):
            reasons[name] = "missing_video_generation"
            continue
        if ctx["window"] < task.min_context_window:
            reasons[name] = "insufficient_context_window"
            continue

        est_cost = estimate_request_cost_usd(model, task.estimated_tokens, task.estimated_output_tokens)
        if rc.max_cost_usd is not None and est_cost > rc.max_cost_usd:
            reasons[name] = f"estimated_cost_exceeds_budget:{est_cost:.4f}"
            continue
        if tc.budget_remaining_usd is not None and est_cost > tc.budget_remaining_usd:
            reasons[name] = f"exceeds_tenant_remaining_budget:{est_cost:.4f}"
            continue
        est_latency = estimate_request_latency_ms(model, task)
        if rc.max_latency_ms is not None and est_latency > rc.max_latency_ms:
            reasons[name] = f"estimated_latency_exceeds_sla:{est_latency:.1f}"
            continue

        feasible.append(deepcopy(model))

    return feasible, reasons
