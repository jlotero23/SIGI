"""
Agente 1 – Consumidor de datos y pronóstico de demanda.

Modelo elegido: Regresión Lineal (scikit-learn) con features temporales.

¿Por qué este modelo?
- Los datos son ventas diarias por producto en múltiples tiendas.
- Para una PoC académica necesitamos algo interpretable, rápido y sin GPU.
- La regresión lineal con día/semana/mes captura tendencia y estacionalidad básica.
- scikit-learn es estándar en cursos de ML y fácil de explicar en una demo.
"""

from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from ..config import FORECAST_HORIZON_DAYS, MIN_HISTORY_DAYS, MODELS_DIR
from ..database import log_execution, save_forecasts, update_agent_status
from ..services.data_service import aggregate_daily_demand, load_sales_data


MODEL_FILE = MODELS_DIR / "forecast_models.joblib"


def _build_features(dates: pd.Series) -> np.ndarray:
    """Convierte fechas en features numéricas para el modelo."""
    d = pd.to_datetime(dates)
    day_num = (d - d.min()).dt.days.values.reshape(-1, 1)
    weekday = d.dt.weekday.values.reshape(-1, 1)
    month = d.dt.month.values.reshape(-1, 1)
    return np.hstack([day_num, weekday, month])


def _train_product_model(series: pd.DataFrame) -> LinearRegression | None:
    """Entrena un modelo lineal para un solo producto."""
    if len(series) < MIN_HISTORY_DAYS:
        return None

    X = _build_features(series["fecha"])
    y = series["demanda"].values
    model = LinearRegression()
    model.fit(X, y)
    return model


def run_forecast_agent(dataset_path: Path | None = None) -> dict:
    """
    Ejecuta el Agente 1 completo:
    1. Carga y limpia datos
    2. Agrega demanda diaria por producto
    3. Entrena modelos por producto
    4. Genera pronóstico a 14 días
    """
    update_agent_status("agent1_forecast", "running", "Procesando dataset y entrenando modelos...")

    try:
        df = load_sales_data(dataset_path)
        daily = aggregate_daily_demand(df)

        models: dict[str, LinearRegression] = {}
        forecast_records: list[dict] = []
        product_summaries: list[dict] = []

        last_date = daily["fecha"].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=FORECAST_HORIZON_DAYS,
            freq="D",
        )

        for producto, group in daily.groupby("producto"):
            group = group.sort_values("fecha")
            model = _train_product_model(group)

            if model is None:
                # Fallback: media móvil de 7 días para productos con poca historia
                avg_demand = group["demanda"].tail(7).mean()
                preds = [max(0.0, float(avg_demand))] * FORECAST_HORIZON_DAYS
                method = "media_movil_7d"
            else:
                models[producto] = model
                X_future = _build_features(pd.Series(future_dates))
                preds = np.maximum(model.predict(X_future), 0)
                method = "regresion_lineal"

            total_forecast = float(np.sum(preds))
            product_summaries.append(
                {
                    "producto": producto,
                    "categoria": group["categoria"].iloc[-1],
                    "demanda_historica_media": float(group["demanda"].mean()),
                    "demanda_pronosticada_total": total_forecast,
                    "metodo": method,
                }
            )

            for fecha, pred in zip(future_dates, preds):
                forecast_records.append(
                    {
                        "producto": producto,
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "demanda_real": None,
                        "demanda_pronosticada": round(float(pred), 2),
                    }
                )

        # Guardar modelos entrenados para re-ejecución
        joblib.dump(
            {
                "models": models,
                "last_date": last_date.strftime("%Y-%m-%d"),
                "horizon": FORECAST_HORIZON_DAYS,
            },
            MODEL_FILE,
        )

        execution_id = log_execution(
            "agent1_forecast",
            "success",
            f"Pronóstico generado para {len(product_summaries)} productos",
            {
                "productos": len(product_summaries),
                "horizonte_dias": FORECAST_HORIZON_DAYS,
                "modelo": "LinearRegression + features temporales (scikit-learn)",
            },
        )
        save_forecasts(execution_id, forecast_records)

        # Top productos por demanda pronosticada
        top = sorted(product_summaries, key=lambda x: x["demanda_pronosticada_total"], reverse=True)[:10]

        update_agent_status(
            "agent1_forecast",
            "success",
            f"Último pronóstico: {len(product_summaries)} productos, {FORECAST_HORIZON_DAYS} días",
        )

        return {
            "execution_id": execution_id,
            "status": "success",
            "model_explanation": (
                "Se usa Regresión Lineal de scikit-learn con features de día, día de semana y mes. "
                "Es interpretable, gratuito y adecuado para series cortas de ventas retail."
            ),
            "summary": {
                "productos_modelados": len(product_summaries),
                "horizonte_dias": FORECAST_HORIZON_DAYS,
                "fecha_desde": (last_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                "fecha_hasta": future_dates[-1].strftime("%Y-%m-%d"),
            },
            "top_products": top,
            "forecasts_count": len(forecast_records),
        }

    except Exception as exc:
        log_execution("agent1_forecast", "error", str(exc))
        update_agent_status("agent1_forecast", "error", str(exc))
        raise


def get_historical_and_forecast_chart_data() -> dict:
    """Datos para gráficos: histórico agregado + último pronóstico."""
    df = load_sales_data()
    daily = aggregate_daily_demand(df)

    # Demanda total diaria (todas las tiendas/productos)
    hist = (
        daily.groupby("fecha")["demanda"]
        .sum()
        .reset_index()
        .tail(60)
    )
    hist["fecha"] = hist["fecha"].dt.strftime("%Y-%m-%d")

    from ..database import get_latest_forecasts

    forecasts = get_latest_forecasts()
    if forecasts:
        fc = pd.DataFrame(forecasts)
        fc_agg = fc.groupby("fecha")["demanda_pronosticada"].sum().reset_index()
    else:
        fc_agg = pd.DataFrame(columns=["fecha", "demanda_pronosticada"])

    return {
        "historico": hist.to_dict(orient="records"),
        "pronostico": fc_agg.to_dict(orient="records"),
    }
