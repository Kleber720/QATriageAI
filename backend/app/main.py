from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, logs, triage

app = FastAPI(
    title="QA Triage AI (Local Ollama)",
    description=(
        "Assistente local de triagem de bugs que transforma relatos vagos ou rascunhos "
        "incompletos em tickets reproduzíveis para QA, separando fatos confirmados de lacunas."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(triage.router)
app.include_router(logs.router)
