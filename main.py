from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

# Kokoro imports (example – adjust if your fork differs)
from kokoro import KokoroTTS

app = FastAPI(title="EngDraft Audio Generator")

# Load model ONCE at startup (important)
tts = KokoroTTS(
    voice="male_en",      # change later (male/female)
    device="cpu"          # Render = CPU
)

class TTSRequest(BaseModel):
    text: str


@app.post("/tts")
def generate_audio(req: TTSRequest):
    """
    Accepts text and returns WAV audio
    """

    # Generate audio (returns numpy array or bytes depending on implementation)
    audio_bytes, sample_rate = tts.generate(
        text=req.text,
        format="wav"
    )

    audio_stream = io.BytesIO(audio_bytes)

    return StreamingResponse(
        audio_stream,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "inline; filename=output.wav"
        }
    )


@app.get("/")
def health():
    return {"status": "ok", "engine": "kokoro-tts"}