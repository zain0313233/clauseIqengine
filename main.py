from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import process, query
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ClauseIQ AI Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process.router, prefix="/process", tags=["process"])
app.include_router(query.router, prefix="/query", tags=["query"])

@app.get("/health")
def health():
    return {"status": "ClauseIQ AI Engine running"}