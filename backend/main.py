"""
AI Dataset Validator & Function-Calling Simulator — Main FastAPI Application

Provides REST API endpoints for the complete pipeline:
  - Natural Language → Function Call generation
  - Multi-layer validation
  - SQL execution
  - Dataset QA analysis
  - Error injection
  - Analytics dashboard data
"""

import json
from typing import Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.function_registry import get_registry_summary
from backend.validator import validate_function_call
from backend.sql_engine import (
    init_db,
    execute_query,
    get_user_stats,
    search_products,
    get_order_history,
)
from backend.dataset_checker import analyze_dataset
from backend.error_injector import inject_error, get_injection_modes
from backend.nl_to_function import nl_to_function_call
from backend.analytics_store import log_pipeline_run, get_analytics, clear_analytics


# ─── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Dataset Validator & Function-Calling Simulator",
    description=(
        "A system that simulates LLM function-call generation, validates, "
        "executes, and analyzes them like a real AI data pipeline."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Startup Event ────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    """Initialize the database with sample data on startup."""
    init_db()
    print("[OK] Database initialized with sample data.")


# ─── Request Models ───────────────────────────────────────────────────────────

class NLRequest(BaseModel):
    text: str = Field(..., description="Natural language query", min_length=1)


class FunctionCallRequest(BaseModel):
    """A function call to validate and/or execute."""
    name: str = Field(default=None, description="Function name")
    arguments: dict = Field(default=None, description="Function arguments")

    # Allow raw JSON string input too
    raw_json: Optional[str] = Field(
        default=None,
        description="Raw JSON string (alternative to name+arguments)"
    )


class InjectErrorRequest(BaseModel):
    call: dict = Field(..., description="A valid function call to corrupt")
    mode: str = Field(..., description="Injection mode identifier")


class PipelineRequest(BaseModel):
    text: str = Field(..., description="Natural language query for full pipeline")


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/registry")
def api_get_registry():
    """Return the function registry — all allowed functions and their schemas."""
    return {
        "functions": get_registry_summary(),
        "total": len(get_registry_summary()),
    }


@app.post("/api/generate")
def api_generate(request: NLRequest):
    """
    Generate a function call from natural language input.
    Simulates LLM function-call generation using rule-based mapping.
    """
    call = nl_to_function_call(request.text)
    return {
        "input_text": request.text,
        "generated_call": call,
    }


@app.post("/api/validate")
def api_validate(request: FunctionCallRequest):
    """
    Validate a function call JSON.
    Checks: JSON validity, schema match, type correctness, SQL safety.
    """
    # Determine input source
    if request.raw_json:
        input_data = request.raw_json
    elif request.name is not None:
        input_data = {"name": request.name, "arguments": request.arguments or {}}
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'name'+'arguments' or 'raw_json'."
        )

    result = validate_function_call(input_data)

    # Log to analytics
    func_name = "unknown"
    if isinstance(input_data, dict):
        func_name = input_data.get("name", "unknown")
    elif isinstance(input_data, str):
        try:
            parsed = json.loads(input_data)
            func_name = parsed.get("name", "unknown")
        except (json.JSONDecodeError, AttributeError):
            func_name = "parse_error"

    log_pipeline_run(
        function_name=func_name,
        input_text=None,
        validation_result=result,
    )

    return result


@app.post("/api/execute")
def api_execute(request: FunctionCallRequest):
    """
    Execute a validated function call against the database.
    First validates, then executes if valid.
    """
    if request.raw_json:
        try:
            call = json.loads(request.raw_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    elif request.name is not None:
        call = {"name": request.name, "arguments": request.arguments or {}}
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'name'+'arguments' or 'raw_json'."
        )

    # Validate first
    validation = validate_function_call(call)
    if validation["status"] == "invalid":
        return {
            "executed": False,
            "validation": validation,
            "data": None,
            "error": "Function call failed validation. Fix errors before executing.",
        }

    # Execute based on function name
    func_name = call["name"]
    args = call.get("arguments", {})

    try:
        if func_name == "query_database":
            data = execute_query(args["query"])
        elif func_name == "get_user_stats":
            data = get_user_stats(args["user_id"])
        elif func_name == "search_products":
            data = search_products(
                args["keyword"],
                args.get("max_price")
            )
        elif func_name == "get_order_history":
            data = get_order_history(
                args["user_id"],
                args.get("limit", 10)
            )
        else:
            raise HTTPException(status_code=400, detail=f"Cannot execute '{func_name}'")

        # Log success
        log_pipeline_run(
            function_name=func_name,
            input_text=None,
            validation_result=validation,
            execution_success=True,
        )

        return {
            "executed": True,
            "validation": validation,
            "data": data,
        }

    except Exception as e:
        # Log failure
        log_pipeline_run(
            function_name=func_name,
            input_text=None,
            validation_result=validation,
            execution_success=False,
            execution_error=str(e),
        )
        return {
            "executed": False,
            "validation": validation,
            "data": None,
            "error": str(e),
        }


@app.post("/api/analyze")
def api_analyze(request: FunctionCallRequest):
    """
    Execute a function call and run Dataset QA on the results.
    """
    # First execute
    exec_result = api_execute(request)

    if not exec_result["executed"] or not exec_result["data"]:
        return {
            "execution": exec_result,
            "analysis": None,
        }

    # Run dataset analysis
    analysis = analyze_dataset(exec_result["data"])

    return {
        "execution": exec_result,
        "analysis": analysis,
    }


@app.post("/api/inject-error")
def api_inject_error(request: InjectErrorRequest):
    """
    Inject a controlled error into a valid function call.
    Returns the corrupted call and what was injected.
    """
    result = inject_error(request.call, request.mode)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Also validate the corrupted call to show detection
    corrupted = result["corrupted_call"]
    validation = validate_function_call(corrupted)

    return {
        **result,
        "validation_of_corrupted": validation,
    }


@app.get("/api/injection-modes")
def api_injection_modes():
    """Return available error injection modes."""
    return {"modes": get_injection_modes()}


@app.post("/api/pipeline")
def api_pipeline(request: NLRequest):
    """
    Full pipeline: NL → Generate → Validate → Execute → Analyze.
    Runs the complete flow in one call and returns all intermediate results.
    """
    # Step 1: Generate
    call = nl_to_function_call(request.text)

    # Step 2: Validate
    validation = validate_function_call(call)

    # Step 3: Execute (if valid)
    data = None
    execution_success = None
    execution_error = None

    if validation["status"] != "invalid":
        func_name = call["name"]
        args = call.get("arguments", {})

        try:
            if func_name == "query_database":
                data = execute_query(args["query"])
            elif func_name == "get_user_stats":
                data = get_user_stats(args["user_id"])
            elif func_name == "search_products":
                data = search_products(args["keyword"], args.get("max_price"))
            elif func_name == "get_order_history":
                data = get_order_history(args["user_id"], args.get("limit", 10))
            execution_success = True
        except Exception as e:
            execution_error = str(e)
            execution_success = False

    # Step 4: Analyze (if we have data)
    analysis = None
    quality_score = None
    if data:
        analysis = analyze_dataset(data)
        quality_score = analysis["summary"]["quality_score"]

    # Log everything
    log_pipeline_run(
        function_name=call.get("name", "unknown"),
        input_text=request.text,
        validation_result=validation,
        execution_success=execution_success,
        execution_error=execution_error,
        dataset_issues=analysis["issues"] if analysis else None,
        quality_score=quality_score,
    )

    return {
        "input_text": request.text,
        "generated_call": call,
        "validation": validation,
        "executed": execution_success or False,
        "execution_error": execution_error,
        "data": data,
        "analysis": analysis,
    }


@app.get("/api/analytics")
def api_analytics():
    """Return aggregated analytics from all pipeline runs."""
    return get_analytics()


@app.post("/api/analytics/clear")
def api_clear_analytics():
    """Clear all analytics data."""
    clear_analytics()
    return {"status": "cleared"}


# ─── Serve Frontend ────────────────────────────────────────────────────────────

import os

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        """Serve the frontend dashboard."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
