import io
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from scipy.io import wavfile
from kokoro import KokoroTTS

# Lifespan context manager for efficient model loading
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model once on startup
    # Render's free tier has limited RAM, Kokoro is efficient enough for it
    models["tts"] = KokoroTTS(
        voice="af_bella",  # Bella is a high-quality default
        device="cpu"
    )
    yield
    # Clean up on shutdown
    models.clear()

app = FastAPI(title="EngDraft Audio Generator", lifespan=lifespan)

class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def generate_audio(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # 1. Generate the audio (returns a NumPy array and sample rate)
        # Note: 'tts' is pulled from our lifespan dictionary
        audio_array, sample_rate = models["tts"].generate(
            text=req.text
        )

        # 2. Convert the NumPy array into WAV byte data
        # 
        byte_io = io.BytesIO()
        wavfile.write(byte_io, sample_rate, audio_array)
        byte_io.seek(0)

        return StreamingResponse(
            byte_io,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=output.wav"
            }
        )
    except Exception as e:
        print(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during TTS generation")

@app.get("/")
def health_check():
    return {"status": "online", "engine": "kokoro-tts"}

if __name__ == "__main__":
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)