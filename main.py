from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# Load knowledge base

with open(
    "knowledge.txt",
    "r",
    encoding="utf-8"
) as f:
    KNOWLEDGE = f.read()

CHUNKS = KNOWLEDGE.split(
    "========================"
)


class ChatRequest(BaseModel):
    message: str
    phone: str = ""
    language: str = "en"
    state: str = ""


def get_relevant_knowledge(
    question,
    top_n=5
):

    question_words = set(
        question.lower().split()
    )

    scored_chunks = []

    for chunk in CHUNKS:

        chunk_lower = chunk.lower()

        score = 0

        for word in question_words:

            if (
                len(word) > 2
                and word in chunk_lower
            ):
                score += 1

        if score > 0:

            scored_chunks.append(
                (
                    score,
                    chunk
                )
            )

    scored_chunks.sort(
        key=lambda x: x[0],
        reverse=True
    )

    selected = []

    for score, chunk in scored_chunks[:top_n]:

        selected.append(
            chunk[:3000]
        )

    return "\n\n".join(
        selected
    )


@app.get("/")
def home():

    return {
        "status": "ok",
        "service": "Trip Assistant AI"
    }


@app.post("/chat")
def chat(
    request: ChatRequest
):

    relevant_knowledge = (
        get_relevant_knowledge(
            request.message
        )
    )

    if not relevant_knowledge:

        return {
            "reply":
            "Please contact us on 9322901463 for assistance."
        }

    system_prompt = f"""
You are Ashtavinayak Travel Assistant.

IMPORTANT RULES:

1. Answer ONLY from the supplied knowledge.
2. Never invent prices.
3. Never invent dates.
4. Never invent pickup points.
5. Never invent package details.
6. Keep replies short and WhatsApp friendly.
7. If information is unavailable, reply:

Please contact us on 9322901463.

KNOWLEDGE:

{relevant_knowledge}
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
