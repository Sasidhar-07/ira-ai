"use client";

import { useEffect, useRef, useState } from "react";

export default function Home() {
  const [messages, setMessages] = useState<any[]>([]);
  const [listening, setListening] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [mood, setMood] = useState("neutral");
  const [wakeMode, setWakeMode] = useState(false);

  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const detectMood = (text: string) => {
    const msg = text.toLowerCase();

    if (msg.includes("sad") || msg.includes("lonely") || msg.includes("cry"))
      return "sad";
    if (msg.includes("stress") || msg.includes("future") || msg.includes("career"))
      return "stressed";
    if (msg.includes("angry") || msg.includes("frustrated"))
      return "angry";
    if (msg.includes("happy") || msg.includes("good"))
      return "happy";

    return "neutral";
  };

  useEffect(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      (window as any).webkitSpeechRecognition ||
      (window as any).SpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech Recognition not supported.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.lang = "en-IN";

    recognition.onend = () => {
      if (wakeMode) {
        try {
          recognition.start();
        } catch {}
      } else {
        setListening(false);
      }
    };

    recognition.onresult = async (event: any) => {
      try {
        const transcript =
          event.results[event.results.length - 1][0].transcript;

        const lowerText = transcript.toLowerCase();

        if (wakeMode) {
          if (!lowerText.includes("hey ira")) {
            return;
          }

          setWakeMode(false);

          const wakeReply = "I'm listening.";

          const speech = new SpeechSynthesisUtterance(wakeReply);
          window.speechSynthesis.speak(speech);

          setMessages((prev) => [
            ...prev,
            { role: "ai", text: wakeReply },
          ]);

          return;
        }

        const detectedMood = detectMood(transcript);

        setMood(detectedMood);
        setMessages((prev) => [
          ...prev,
          { role: "user", text: transcript },
        ]);

        setListening(false);
        setThinking(true);

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: transcript,
          }),
        });

        const data = await res.json();

        setThinking(false);

        if (!data.response) {
          alert("No AI response received");
          return;
        }

        setMessages((prev) => [
          ...prev,
          { role: "ai", text: data.response },
        ]);

        const audioRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/speak`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: data.response,
          }),
        });

        const audioBlob = await audioRes.blob();

        if (audioBlob.size < 1000) {
          alert("Voice generation failed");
          return;
        }

        const audioUrl = URL.createObjectURL(audioBlob);

        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }

        const audio = document.createElement("audio");
        audio.src = audioUrl;
        audio.volume = 1;

        audioRef.current = audio;
        document.body.appendChild(audio);

        setSpeaking(true);

        audio.onended = () => {
          setSpeaking(false);

          if (audio.parentNode) {
            audio.parentNode.removeChild(audio);
          }

          audioRef.current = null;
        };

        await audio.play();

      } catch (error) {
        console.error(error);
        setThinking(false);
        setSpeaking(false);
        setListening(false);
        alert("Backend connection failed");
      }
    };

    recognitionRef.current = recognition;
  }, [wakeMode]);

  const startListening = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      setSpeaking(false);
    }

    if (listening) return;

    try {
      setListening(true);
      recognitionRef.current.start();
    } catch {}
  };

  const startWakeMode = () => {
    setWakeMode(true);
    setListening(true);

    try {
      recognitionRef.current.start();
    } catch {}
  };

  const statusText = wakeMode
    ? "Waiting for 'Hey Ira'..."
    : listening
    ? "Listening..."
    : thinking
    ? "Thinking..."
    : speaking
    ? "Speaking..."
    : "Tap mic and talk to Ira";

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 via-black to-black" />

      <div className="relative z-10 flex flex-col items-center w-full">
        <h1 className="text-5xl font-bold mb-2">Ira</h1>
        <p className="text-gray-400 mb-3">Your Emotional AI Mentor</p>

        <div className="mb-8 text-sm px-4 py-2 rounded-full bg-white/10">
          Mood: <span className="capitalize">{mood}</span>
        </div>

        <div className="relative mb-8">
          <div
            className={`relative w-48 h-48 rounded-full flex items-center justify-center transition-all duration-500 ${
              listening
                ? "bg-red-500"
                : speaking
                ? "bg-green-400"
                : thinking
                ? "bg-purple-500"
                : "bg-white"
            }`}
          >
            <span className="text-6xl">
              {listening ? "🎙️" : thinking ? "🧠" : speaking ? "🔊" : "✨"}
            </span>
          </div>
        </div>

        <p className="text-gray-300 mb-8">{statusText}</p>

        <div className="w-full max-w-2xl space-y-4 mb-10 max-h-72 overflow-y-auto">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`p-4 rounded-2xl ${
                msg.role === "user" ? "bg-blue-600 ml-auto" : "bg-gray-800"
              }`}
            >
              {msg.text}
            </div>
          ))}
        </div>

        <div className="flex gap-4">
          <button
            onClick={startListening}
            className={`w-24 h-24 rounded-full text-3xl ${
              listening ? "bg-red-500" : "bg-white text-black"
            }`}
          >
            🎤
          </button>

          <button
            onClick={startWakeMode}
            className="px-6 py-4 rounded-2xl bg-purple-600 text-white"
          >
            Hey Ira Mode
          </button>
        </div>
      </div>
    </main>
  );
}