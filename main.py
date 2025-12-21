from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import uvicorn
from contextlib import asynccontextmanager
from kokoro import KokoroTTS

# Use a lifespan to manage model loading
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model into the shared dictionary
    try:
        models["tts"] = KokoroTTS(voice="af_bella", device="cpu")
        yield
    finally:
        models.clear()

app = FastAPI(title="EngDraft Audio Generator", lifespan=lifespan)

class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def generate_audio(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Note: Ensure your kokoro version returns bytes for io.BytesIO
        audio_bytes, sample_rate = models["tts"].generate(
            text=req.text,
            format="wav"
        )
        
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ready"}