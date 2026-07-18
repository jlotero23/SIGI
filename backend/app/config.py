"""Configuración central del sistema de pronóstico y reabastecimiento."""

from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

# Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = DATA_DIR / "sistema.db"

# Dataset por defecto (copiado del archivo académico)
DEFAULT_DATASET = DATA_DIR / "ventas.csv"

# Parámetros del Agente 1 – Pronóstico
FORECAST_HORIZON_DAYS = int(os.getenv("FORECAST_HORIZON_DAYS", "14"))
MIN_HISTORY_DAYS = int(os.getenv("MIN_HISTORY_DAYS", "14"))

# Parámetros del Agente 2 – Reabastecimiento
LEAD_TIME_DAYS = int(os.getenv("LEAD_TIME_DAYS", "7"))
SAFETY_FACTOR = float(os.getenv("SAFETY_FACTOR", "1.5"))
REVIEW_PERIOD_DAYS = int(os.getenv("REVIEW_PERIOD_DAYS", "7"))

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# WhatsApp (opcional – Groq para respuestas más naturales, plan gratuito)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WHATSAPP_BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

# Crear carpetas necesarias
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
