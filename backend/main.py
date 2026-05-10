import re
import edge_tts
import tempfile
import os
import requests

from fastapi import FastAPI
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


class ChatRequest(BaseModel):
    message: str


class SpeakRequest(BaseModel):
    text: str


@app.get("/")
async def root():
    return {"message": "Backend running"}


# lightweight placeholder memory (for deploy now)
def store_memory(text):
    return


def retrieve_memories(query):
    return ""


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        user_message = req.message or ""

        if not user_message.strip():
            return {"response": "I didn’t hear that clearly."}

        memories = retrieve_memories(user_message)

        system_prompt = f"""
You are Ira, an emotionally intelligent AI mentor.

Known memories:
{memories}

Be warm, human, emotionally intelligent.
Maximum 2 short sentences.
No markdown.
No emojis.
"""

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Ira Voice AI",
        }

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "openrouter/free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 100,
                "temperature": 0.8
            },
            timeout=30
        )

        if res.status_code != 200:
            return {"response": f"API error {res.status_code}"}

        data = res.json()
        reply = data["choices"][0]["message"]["content"]

        if not reply:
            reply = "Hmm, I lost my thought."

        store_memory(user_message)
        store_memory(reply)

        return {"response": reply}

    except Exception as e:
        print("CHAT ERROR:", e)
        return {"response": "Backend crashed"}


@app.post("/speak")
async def speak(req: SpeakRequest):
    try:
        text = req.text or ""

        clean_text = re.sub(r"[^\w\s.,!?'-]", "", text)

        if not clean_text.strip():
            clean_text = "I am here with you."

        lower = clean_text.lower()

        if any(word in lower for word in ["sad", "lonely", "cry", "hurt"]):
            voice = "en-IN-NeerjaNeural"

        elif any(word in lower for word in ["stress", "anxious", "worried", "panic"]):
            voice = "en-US-JennyNeural"

        elif any(word in lower for word in ["happy", "excited", "great", "awesome"]):
            voice = "en-US-AriaNeural"

        elif any(word in lower for word in ["angry", "frustrated", "mad"]):
            voice = "en-GB-SoniaNeural"

        else:
            voice = "en-IN-NeerjaNeural"

        communicate = edge_tts.Communicate(clean_text, voice)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name

        await communicate.save(temp_path)

        with open(temp_path, "rb") as audio_file:
            audio_data = audio_file.read()

        os.remove(temp_path)

        return Response(content=audio_data, media_type="audio/mpeg")

    except Exception as e:
        print("EDGE TTS ERROR:", str(e))
        return {"error": str(e)}