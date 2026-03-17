from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.chat import router as chat_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.upload import router as upload_router


app = FastAPI(title="Local NotebookLM Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(knowledge_router)
app.include_router(chat_router)


@app.get("/")
def healthcheck() -> dict:
    return {"status": "ok"}
