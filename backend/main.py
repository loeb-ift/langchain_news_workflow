import uuid
import csv
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Assuming pipeline.py is in the same directory or a reachable path
# We will need to adjust the import path based on the final project structure
import sys
import os

# Add the parent directory to the path to find the original pipeline module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import (
    InputConfig,
    AlphaOutput,
    BetaOutput,
    GammaOutput,
    run_alpha,
    run_beta,
    run_gamma,
    run_delta,
)

app = FastAPI()

# --- CORS Middleware ---
# This allows the React frontend (running on a different port) to communicate with the backend
origins = [
    "http://localhost:3000",  # Default React dev server port
    "http://localhost:5173",  # Default Vite dev server port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory session storage ---
# In a production environment, you would replace this with a database like Redis
sessions: Dict[str, Dict[str, Any]] = {}

LOG_FILE = "pipeline_log.csv"

# --- Pydantic Models for API requests ---
class StartRequest(BaseModel):
    raw_data: str
    news_type: str = "財經"
    target_style: str = "經濟日報"
    word_limit: int = 800
    tone: str = "客觀中性"

class AlphaRequest(BaseModel):
    session_id: str

# --- API Endpoints ---

@app.post("/start")
def start_pipeline(request: StartRequest):
    """
    Starts a new pipeline session, initializes the config, and runs the Alpha stage.
    """
    session_id = str(uuid.uuid4())
    
    config = InputConfig(
        raw_data=request.raw_data,
        news_type=request.news_type,
        target_style=request.target_style,
        word_limit=request.word_limit,
        tone=request.tone,
    )
    
    # Run the first stage
    alpha_result = run_alpha(config)
    
    # Store session data
    sessions[session_id] = {
        "config": config,
        "alpha_result": alpha_result,
        "log_entries": [],
        "start_time": datetime.now(),
    }
    
    return {"session_id": session_id, "alpha_result": alpha_result}

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI News Generation Pipeline API"}

# We will add more endpoints for Beta, Gamma, Delta, and logging later.
