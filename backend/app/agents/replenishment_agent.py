"""
Agente 2 – Políticas de reabastecimiento.

Consume los pronósticos del Agente 1 y aplica reglas simples:

Política de punto de reorden (s, S) simplificada:
- Demanda media diaria = promedio del pronóstico
- Stock de seguridad = demanda_media * SAFETY_FACTOR * sqrt(LEAD_TIME)
- Punto de reorden = demanda_media * LEAD_TIME + stock_seguridad
- Cantidad sugerida = max(0, pronóstico del periodo de revisión - stock simulado)

Justificación académica: reglas claras, sin optimización estocástica avanzada.
"""

from datetime import datetime, timedelta
import random

import pandas as pd

from ..config import LEAD_TIME_DAYS, REVIEW_PERIOD_DAYS, SAFETY_FACTOR
from ..database import (
    get_latest_forecasts,
    get_latest_recommendations,
    log_execution,
    save_recommendations,
    update_agent_status,
)


def _classify_priority(cantidad: float, avg_daily: float) -> str:
    if cantidad >= avg_daily * REVIEW_PERIOD_DAYS * 1.5:
        return "alta"
    if cantidad >= avg_daily * REVIEW_PERIOD_DAYS * 0.5:
        return "media"
    return "baja"


def run_replenishment_agent() -> dict:
    """Genera recomendaciones de compra basadas en el último pronóstico."""
    update_agent_status("agent2_replenishment", "running", "Calculando políticas de reabastecimiento...")

    try:
        forecasts = get_latest_forecasts()
        if not forecasts:
            msg = "No hay pronósticos disponibles. Ejecute primero el Agente 1."
            update_agent_status("agent2_replenishment", "error", msg)
            raise ValueError(msg)

        fc = pd.DataFrame(forecasts)
        fc["demanda_pronosticada"] = pd.to_numeric(fc["demanda_pronosticada"])

        recommendations: list[dict] = []
        today = datetime.utcnow().date()

        for producto, group in fc.groupby("producto"):
            avg_daily = group["demanda_pronosticada"].mean()
            forecast_period = group["demanda_pronosticada"].sum()

            # Stock de seguridad y punto de reorden (reglas simples)
            safety_stock = avg_daily * SAFETY_FACTOR * (LEAD_TIME_DAYS ** 0.5)
            reorder_point = avg_daily * LEAD_TIME_DAYS + safety_stock

            # Stock simulado (PoC: 30% del punto de reorden como inventario actual)
            simulated_stock = reorder_point * 0.3

            # Cantidad a pedir para cubrir el periodo de revisión
            target_stock = forecast_period + safety_stock
            cantidad_sugerida = max(0, int(round(target_stock - simulated_stock)))

            if cantidad_sugerida <= 0:
                continue

            # Fecha sugerida de compra: cuando el stock proyectado baje del punto de reorden
            days_until_reorder = max(1, int((simulated_stock - reorder_point) / max(avg_daily, 0.1) + LEAD_TIME_DAYS))
            fecha_sugerida = (today + timedelta(days=min(days_until_reorder, LEAD_TIME_DAYS))).isoformat()

            prioridad = _classify_priority(cantidad_sugerida, avg_daily)

            recommendations.append(
                {
                    "producto": producto,
                    "categoria": None,
                    "demanda_pronosticada": round(float(forecast_period), 2),
                    "cantidad_sugerida": cantidad_sugerida,
                    "punto_reorden": round(float(reorder_point), 2),
                    "stock_seguridad": round(float(safety_stock), 2),
                    "prioridad": prioridad,
                    "fecha_sugerida": fecha_sugerida,
                    "justificacion": (
                        f"Demanda media diaria pronosticada: {avg_daily:.1f} uds. "
                        f"Punto de reorden: {reorder_point:.1f}. "
                        f"Se sugiere comprar {cantidad_sugerida} uds. para cubrir "
                        f"los próximos {REVIEW_PERIOD_DAYS} días con stock de seguridad."
                    ),
                }
            )

        recommendations.sort(
            key=lambda r: ({"alta": 0, "media": 1, "baja": 2}[r["prioridad"]], -r["cantidad_sugerida"]),
        )

        execution_id = log_execution(
            "agent2_replenishment",
            "success",
            f"{len(recommendations)} recomendaciones generadas",
            {
                "total_recomendaciones": len(recommendations),
                "lead_time_dias": LEAD_TIME_DAYS,
                "factor_seguridad": SAFETY_FACTOR,
            },
        )
        save_recommendations(execution_id, recommendations)

        update_agent_status(
            "agent2_replenishment",
            "success",
            f"{len(recommendations)} sugerencias de compra listas",
        )

        return {
            "execution_id": execution_id,
            "status": "success",
            "total_recommendations": len(recommendations),
            "policy_explanation": (
                "Política de punto de reorden simplificada: se calcula demanda media del pronóstico, "
                "stock de seguridad con factor configurable y cantidad sugerida para el periodo de revisión."
            ),
            "recommendations": recommendations[:50],
        }

    except Exception as exc:
        if "No hay pronósticos" not in str(exc):
            log_execution("agent2_replenishment", "error", str(exc))
            update_agent_status("agent2_replenishment", "error", str(exc))
        raise


# Palabras clave ampliadas para interpretar distintas formas de preguntar
_PURCHASE_KEYWORDS = [
    "comprar", "compra", "pedir", "pedido", "ordenar", "ordene",
    "esta semana", "semana", "reabastecer", "abastecer", "stock",
    "inventario bajo", "que necesito", "qué necesito", "que debo",
    "qué debo", "surte", "surta", "proveedor",
]
_DEMAND_KEYWORDS = [
    "mayor demanda", "más demanda", "mas demanda", "más vend", "mas vend",
    "top", "producto estrella", "más popular", "mas popular", "tendencia",
    "se vende más", "se vende mas", "pronostic", "demanda alta",
    "mejor desempeño", "mejor desempeno", "más rotación", "mas rotacion",
]
_SUMMARY_KEYWORDS = [
    "sugerencia", "sugerencias", "recomendacion", "recomendación",
    "recomendaciones", "politica", "política", "abastecimiento",
    "resumen", "informe", "reporte", "estado", "panorama", "overview",
]
_GREETING_KEYWORDS = [
    "hola", "buenos", "buenas", "ayuda", "help", "menu", "menú",
    "inicio", "empezar", "que puedes", "qué puedes", "como funciona",
    "cómo funciona", "gracias",
]


def _matches_intent(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def _format_purchase_response(recs: list[dict]) -> str:
    """Formatea la lista de compras sugeridas con tono conversacional."""
    top = recs[:10]
    if not top:
        intros = [
            "Buenas noticias: según el último análisis de pronósticos, no hay compras urgentes en este momento.",
            "Por ahora todo está bajo control. El sistema no detecta necesidad inmediata de reabastecimiento.",
        ]
        return random.choice(intros)

    intros = [
        "Con base en los pronósticos del Agente 1 y las políticas de reabastecimiento, te sugiero priorizar estas compras:",
        "He revisado las recomendaciones activas y estos son los productos que conviene adquirir pronto:",
        "Según el análisis más reciente, estas serían las compras más relevantes para la semana:",
    ]
    lines = [random.choice(intros), ""]
    for i, r in enumerate(top, 1):
        prioridad = r["prioridad"]
        if prioridad == "alta":
            detalle = "requiere atención prioritaria"
        elif prioridad == "media":
            detalle = "prioridad moderada"
        else:
            detalle = "puede planificarse con calma"
        lines.append(
            f"{i}. *{r['producto']}* — {r['cantidad_sugerida']} uds. ({detalle})"
        )
    lines.append("")
    lines.append(
        f"Estos valores provienen directamente del último pronóstico "
        f"({REVIEW_PERIOD_DAYS} días de revisión, lead time de {LEAD_TIME_DAYS} días)."
    )
    return "\n".join(lines)


def _format_demand_response(forecasts: list[dict]) -> str:
    """Formatea el ranking de demanda pronosticada."""
    if not forecasts:
        return (
            "Aún no tengo pronósticos disponibles para responder eso. "
            "Ejecuta primero el Agente 1 desde el dashboard de SIGI Retail."
        )

    fc = pd.DataFrame(forecasts)
    top = (
        fc.groupby("producto")["demanda_pronosticada"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    intros = [
        "Estos son los productos con mayor demanda proyectada según el último pronóstico:",
        "Según el modelo de pronóstico, estos productos concentran la mayor demanda esperada:",
        "El análisis de demanda indica que estos artículos liderarán las ventas en el periodo pronosticado:",
    ]
    lines = [random.choice(intros), ""]
    for i, (prod, val) in enumerate(top.items(), 1):
        lines.append(f"{i}. *{prod}* — {val:.0f} uds. en el periodo pronosticado")
    lines.append("")
    lines.append(
        "Los valores corresponden a la suma del pronóstico diario generado por el Agente 1"
    )
    return "\n".join(lines)


def _format_summary_response(recs: list[dict]) -> str:
    """Formatea el resumen de políticas de abastecimiento."""
    if not recs:
        return (
            "Todavía no hay sugerencias de abastecimiento generadas. "
            "Primero ejecuta el pronóstico y luego el Agente 2 desde el dashboard."
        )

    alta = [r for r in recs if r["prioridad"] == "alta"]
    intros = [
        "Te comparto un resumen del estado actual de abastecimiento:",
        "Aquí tienes el panorama de las recomendaciones activas:",
        "Este es el resumen basado en las últimas políticas de reabastecimiento calculadas:",
    ]
    lines = [random.choice(intros), ""]
    lines.append(f"• Total de recomendaciones activas: *{len(recs)}*")
    lines.append(f"• Con prioridad alta: *{len(alta)}*")
    lines.append(f"• Lead time configurado: *{LEAD_TIME_DAYS} días*")
    lines.append("")
    lines.append("*Las 5 compras más prioritarias:*")
    for i, r in enumerate(recs[:5], 1):
        lines.append(
            f"{i}. {r['producto']} — {r['cantidad_sugerida']} uds. "
            f"(ideal antes del {r['fecha_sugerida']})"
        )
    return "\n".join(lines)


def _format_greeting_response() -> str:
    """Menú de ayuda con tono amigable."""
    saludos = [
        "¡Hola! Soy el asistente de reabastecimiento de SIGI Retail.",
        "¡Buen día! Estoy aquí para ayudarte con pronósticos y compras.",
        "Hola, encantado de ayudarte con la gestión de inventarios.",
    ]
    return (
        f"{random.choice(saludos)}\n\n"
        "Puedo ayudarte con consultas como:\n"
        "• _¿Qué productos debo comprar esta semana?_\n"
        "• _¿Cuáles tendrán mayor demanda?_\n"
        "• _¿Qué sugerencias de abastecimiento hay?_\n\n"
        "Escríbeme en lenguaje natural y te responderé con los datos "
        "más recientes del sistema."
    )


def _format_fallback_response() -> str:
    """Respuesta cuando no se reconoce la intención."""
    intros = [
        "No estoy seguro de haber entendido tu consulta, pero puedo ayudarte con temas de inventario.",
        "Disculpa, no logré identificar exactamente qué necesitas. Prueba con alguna de estas preguntas:",
        "Hmm, no reconocí del todo tu mensaje. Estas son consultas que sí puedo responder:",
    ]
    return (
        f"{random.choice(intros)}\n\n"
        "• \"¿Qué productos debo comprar esta semana?\"\n"
        "• \"¿Cuál tendrá mayor demanda?\"\n"
        "• \"¿Qué sugerencias de abastecimiento hay?\"\n\n"
    )


def answer_whatsapp_query(message: str) -> str:
    """
    Responde consultas en lenguaje natural sobre reabastecimiento.
    Interpreta distintas formas de preguntar y comunica los datos
    del sistema con un tono conversacional, sin alterar los valores calculados.
    """
    msg = message.lower().strip()
    recs = get_latest_recommendations()
    forecasts = get_latest_forecasts()

    if not recs and not forecasts:
        return (
            "Por el momento aún no hay pronósticos ni recomendaciones disponibles.\n\n"
            "Para empezar, ejecuta el Agente 1 (pronóstico) y luego el Agente 2 "
            "(reabastecimiento) desde el dashboard de SIGI Retail. "
            "Cuando estén listos, podré responder tus consultas con datos reales."
        )

    if _matches_intent(msg, _PURCHASE_KEYWORDS):
        return _format_purchase_response(recs)

    if _matches_intent(msg, _DEMAND_KEYWORDS):
        return _format_demand_response(forecasts)

    if _matches_intent(msg, _SUMMARY_KEYWORDS):
        return _format_summary_response(recs)

    if _matches_intent(msg, _GREETING_KEYWORDS):
        return _format_greeting_response()

    return _format_fallback_response()
