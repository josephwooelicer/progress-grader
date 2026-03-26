from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, consent, student, teacher, webhooks, workspace

app = FastAPI(title="Progress Grader — Platform Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(consent.router)
app.include_router(workspace.router)
app.include_router(webhooks.router)
app.include_router(teacher.router)
app.include_router(student.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
