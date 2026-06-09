from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

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

    system_prompt = """
You are an Ashtavinayak Yatra Assistant.

You help only with:
- Ashtavinayak Darshan
- Temple Information
- Package Pricing
- Available Dates
- Car Booking
- Booking Status
- Customer Support

Keep answers short and WhatsApp-friendly.

If the question is unrelated to travel or Ashtavinayak Yatra,
politely ask the user to use the available menu options.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": request.message
            }
        ],
        max_tokens=300
    )

    reply = (
        response
        .choices[0]
        .message
        .content
    )

    return {
        "reply": reply
    }
