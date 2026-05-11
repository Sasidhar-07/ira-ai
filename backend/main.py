import re
import edge_tts
import tempfile
import os
import requests

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tempfile
import openai

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


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = await update.message.voice.get_file()

    with tempfile.NamedTemporaryFile(suffix=".ogg") as temp:
        await voice.download_to_drive(temp.name)

        with open(temp.name, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )

    user_message = transcript.text

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are Ira, emotional AI mentor."},
            {"role": "user", "content": user_message}
        ]
    )

    reply = response.choices[0].message.content
    await update.message.reply_text(reply)
    
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
    
    from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading

import tempfile


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi, I'm Ira. Talk to me ❤️")

async def telegram_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "openrouter/free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Ira, a warm emotional AI mentor. Keep replies short and human."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
        )

        data = res.json()
        reply = data["choices"][0]["message"]["content"]

        await update.message.reply_text(reply)

    except Exception:
        await update.message.reply_text("I’m having trouble thinking right now.")

telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_chat)
)

@app.post("/telegram")
async def telegram_webhook(req: dict):
    update = Update.de_json(req, telegram_app.bot)
    await telegram_app.initialize()
    await telegram_app.process_update(update)
    return {"ok": True}



