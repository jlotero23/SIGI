"""API REST del sistema de pronóstico y reabastecimiento."""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..agents.forecast_agent import get_historical_and_forecast_chart_data, run_forecast_agent
from ..agents.replenishment_agent import answer_whatsapp_query, run_replenishment_agent
from ..database import (
    get_agent_statuses,
    get_execution_history,
    get_latest_forecasts,
    get_latest_recommendations,
)
from ..services.data_service import ensure_default_dataset, get_dataset_summary, load_sales_data, upload_dataset

router = APIRouter()


class WhatsAppMessage(BaseModel):
    from_number: str = "demo"
    message: str


@router.get("/health")
def health():
    return {"status": "ok", "service": "Sistema IA Reabastecimiento"}


@router.get("/status")
def get_status():
    return {"agents": get_agent_statuses()}


@router.get("/dataset/summary")
def dataset_summary():
    ensure_default_dataset()
    df = load_sales_data()
    return get_dataset_summary(df)


@router.post("/dataset/upload")
async def dataset_upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Solo se aceptan archivos CSV")
    content = await file.read()
    try:
        path = upload_dataset(content, file.filename)
        df = load_sales_data(path)
        return {"message": "Dataset cargado correctamente", "summary": get_dataset_summary(df)}
    except Exception as exc:
        raise HTTPException(400, f"Error al procesar CSV: {exc}") from exc


@router.post("/agents/forecast/run")
def run_forecast():
    try:
        result = run_forecast_agent()
        return result
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.post("/agents/replenishment/run")
def run_replenishment():
    try:
        result = run_replenishment_agent()
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/forecasts/latest")
def latest_forecasts():
    return {"forecasts": get_latest_forecasts()}


@router.get("/recommendations/latest")
def latest_recommendations():
    return {"recommendations": get_latest_recommendations()}


@router.get("/charts/demand")
def chart_demand():
    try:
        return get_historical_and_forecast_chart_data()
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/executions/history")
def execution_history():
    return {"history": get_execution_history()}


@router.get("/kpis")
def get_kpis():
    """KPIs consolidados para tarjetas del dashboard."""
    ensure_default_dataset()
    df = load_sales_data()
    summary = get_dataset_summary(df)
    forecasts = get_latest_forecasts()
    recs = get_latest_recommendations()

    total_forecast = sum(f["demanda_pronosticada"] for f in forecasts) if forecasts else 0
    alta = len([r for r in recs if r.get("prioridad") == "alta"])

    return {
        **summary,
        "demanda_pronosticada_total": round(total_forecast, 2),
        "recomendaciones_total": len(recs),
        "recomendaciones_alta_prioridad": alta,
        "unidades_sugeridas_compra": sum(r["cantidad_sugerida"] for r in recs),
    }


@router.post("/whatsapp/query")
def whatsapp_query(body: WhatsAppMessage):
    """Endpoint para el bot de WhatsApp o pruebas manuales."""
    reply = answer_whatsapp_query(body.message)
    return {"reply": reply, "from": body.from_number}


@router.post("/whatsapp/incoming")
async def whatsapp_incoming(body: WhatsAppMessage):
    """Alias compatible con el bridge de whatsapp-web.js."""
    return whatsapp_query(body)
