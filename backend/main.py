import re
import os
import tempfile
import requests
import edge_tts

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class ChatRequest(BaseModel):
    message: str


class SpeakRequest(BaseModel):
    text: str


@app.get("/")
async def root():
    return {"message": "Backend running"}


def get_ira_reply(user_message: str):
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Ira, a warm emotional AI mentor. Reply like a caring friend."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "max_tokens": 120,
                "temperature": 0.8
            },
            timeout=30
        )

        data = res.json()
        print("OPENROUTER:", data)

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        return "I'm here with you. Tell me what's on your mind."

    except Exception as e:
        print("IRA ERROR:", e)
        return "I'm here with you. Tell me what's on your mind."


@app.post("/chat")
async def chat(req: ChatRequest):
    return {"response": get_ira_reply(req.message or "")}


@app.post("/speak")
async def speak(req: SpeakRequest):
    text = req.text or "I am here with you."
    clean_text = re.sub(r"[^\w\s.,!?'-]", "", text)

    communicate = edge_tts.Communicate(clean_text, "en-IN-NeerjaNeural")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_path = temp_audio.name

    await communicate.save(temp_path)

    with open(temp_path, "rb") as audio_file:
        audio_data = audio_file.read()

    os.remove(temp_path)

    return Response(content=audio_data, media_type="audio/mpeg")


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    if text == "/start":
        reply = "Hi, I'm Ira. Talk to me ❤️"
    elif text:
        reply = get_ira_reply(text)
    else:
        reply = "Send me a text message for now."

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply},
        timeout=10,
    )

    return {"ok": True}