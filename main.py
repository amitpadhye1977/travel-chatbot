from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    phone: str = ""
    language: str = "en"
    state: str = ""


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "Trip Assistant AI"
    }


@app.post("/chat")
def chat(request: ChatRequest):

    return {
        "reply": f"You said: {request.message}"
    }
