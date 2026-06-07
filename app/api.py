from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from .explainer import generate_signal_packet_payloads
from .runner import build_stage2_payload, parse_date

from fastapi.middleware.cors import CORSMiddleware

class ExplainRequest(BaseModel):
    drug: str
    start_date: str
    end_date: str
    limit: int = 100
    max_pages: int | None = None
    use_local_db: bool = False


class SignalPacketResponse(BaseModel):
    signal_index: int
    drug: str
    event: str
    event_title: str
    medical_context: str
    statistical_justification: str
    trend_analysis: str
    literature_references: list[str]
    priority: str
    next_steps: str
    raw_trend: dict[str, Any]


class ExplainResponse(BaseModel):
    drug: str
    start_date: str
    end_date: str
    signal_count: int
    packets: list[SignalPacketResponse]


app = FastAPI(title="Pharmacovigilance Signal Triage API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/explain", response_model=ExplainResponse)
def explain_signals(payload: ExplainRequest) -> ExplainResponse:
    start = parse_date(payload.start_date)
    end = parse_date(payload.end_date)
    stage2_payload = build_stage2_payload(
        drug_name=payload.drug,
        start=start,
        end=end,
        limit=payload.limit,
        max_pages=payload.max_pages,
        use_local_db=True,
    )
    packets = generate_signal_packet_payloads(stage2_payload)
    return ExplainResponse(
        drug=stage2_payload["drug"],
        start_date=stage2_payload["start_date"],
        end_date=stage2_payload["end_date"],
        signal_count=stage2_payload["signal_count"],
        packets=packets,
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Pharmacovigilance Signal Triage API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
