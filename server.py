import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional
from pipeline import run_pipeline

app = FastAPI(title="新聞自動生成工作流 API", version="1.0.0")

class GenerateRequest(BaseModel):
    raw_data: str
    news_type: str = "財經"
    target_style: str = "經濟日報"
    word_limit: int = 800
    constraints: Optional[str] = None
    tone: str = "客觀中性"
    additional_answers: Optional[Dict[str, Any]] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/generate")
def generate(req: GenerateRequest):
    result = run_pipeline(
        raw_data=req.raw_data,
        news_type=req.news_type,
        target_style=req.target_style,
        word_limit=req.word_limit,
        constraints=req.constraints,
        tone=req.tone,
        additional_answers=req.additional_answers,
    )
    return result
