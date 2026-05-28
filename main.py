from __future__ import annotations

import asyncio
import time

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from graph import swarm_graph
from models import SwarmRequest, create_initial_state, ensure_complete_state

load_dotenv()

REQUEST_TIMEOUT = 55

app = FastAPI(
    title="SalesSwarm API",
    description="LangGraph multi-agent backend for AI-powered B2B sales outreach.",
    version="1.0.0",
)

_ROOT = Path(__file__).parent


@app.get("/")
def frontend():
    html_path = _ROOT / "salesswarm-landing 2.html"
    return FileResponse(html_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/swarm")
async def run_swarm(request: SwarmRequest):
    start = time.time()
    initial_state = create_initial_state(
        founder_product=request.founder_product,
        founder_icp=request.founder_icp,
        target_url=str(request.target_url),
    )

    try:
        result = await asyncio.wait_for(
            swarm_graph.ainvoke(initial_state),
            timeout=REQUEST_TIMEOUT,
        )
        result = ensure_complete_state(result)
    except asyncio.TimeoutError:
        result = ensure_complete_state(initial_state)
        result["errors"].append("Graph timed out after 120 seconds.")
        result["qualified"] = False
        result["qualification_reason"] = "Request timed out. Try a different URL or a smaller model."
        result["next_action"] = "retry"
    except Exception as exc:
        result = ensure_complete_state(initial_state)
        result["errors"].append(f"Graph failed: {exc}")
        result["qualified"] = False
        result["qualification_reason"] = "SalesSwarm could not complete this run."
        result["next_action"] = "retry"

    result["processing_time"] = round(time.time() - start, 2)
    return result


@app.get("/health")
def health():
    return {"status": "SalesSwarm is live 🐝"}

