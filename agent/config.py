import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GRAFANA_STACK_URL = os.environ["GRAFANA_STACK_URL"]
GRAFANA_SERVICE_ACCOUNT_TOKEN = os.environ["GRAFANA_SERVICE_ACCOUNT_TOKEN"]

GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

PARALLEL_API_KEY = os.environ.get("PARALLEL_API_KEY", "")

MODEL_NAME = os.environ.get("ADK_MODEL_NAME", "gemini-2.5-flash")

# Vertex AI mode for the google-genai SDK that ADK uses under the hood.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", GOOGLE_CLOUD_PROJECT)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", GOOGLE_CLOUD_LOCATION)
