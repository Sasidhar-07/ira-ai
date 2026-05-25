import re
import os
import tempfile
import requests
import edge_tts
import json

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
import json

MEMORY_FILE = "memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

def store_memory(user_id, text):
    memory = load_memory()

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append(text)

    if len(memory[user_id]) > 10:
        memory[user_id] = memory[user_id][-10:]

    save_memory(memory)

def retrieve_memories(user_id):
    memory = load_memory()
    return "\n".join(memory.get(user_id, []))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class ChatRequest(BaseModel):
    message: str


class SpeakRequest(BaseModel):
    text: str


@app.get("/")
async def root():
    return {"message": "Backend running"}


def get_ira_reply(user_id: str, user_message: str):
    try:
        memories = retrieve_memories(user_id)
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
                         "content": """
You are Ira, a real-feeling emotional AI friend.
Speak like a close friend on WhatsApp, not like a therapist or assistant.
Use simple natural words.
Keep it short: 2 to 4 lines.
Sound warm, calm, and personal.
No formal advice unless asked.
No markdown.
"""
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

    communicate = edge_tts.Communicate(clean_text, "en-US-JennyNeural")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_path = temp_audio.name

    await communicate.save(temp_path)

    with open(temp_path, "rb") as audio_file:
        audio_data = audio_file.read()

    os.remove(temp_path)

    return Response(content=audio_data, media_type="audio/mpeg")

async def make_voice_file(text: str):
    clean_text = re.sub(r"[^\w\s.,!?'-]", "", text)

    if not clean_text.strip():
        clean_text = "I am here with you."

    communicate = edge_tts.Communicate(
        clean_text,
        "en-IN-NeerjaNeural"
    )

    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    temp_path = temp_audio.name
    temp_audio.close()

    await communicate.save(temp_path)

    return temp_path

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
        reply = get_ira_reply(str(chat_id), text)
        store_memory(str(chat_id), text)
        store_memory(str(chat_id), reply)
    else:
        reply = "Send me a text message for now."

    # send text reply
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply},
        timeout=10,
    )

    # send voice reply
    voice_path = await make_voice_file(reply)

    with open(voice_path, "rb") as audio:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={"chat_id": chat_id},
            files={"audio": audio},
            timeout=30,
        )

    os.remove(voice_path)

    return {"ok": True}