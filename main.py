import io
import os
import uvicorn
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from scipy.io import wavfile
from kokoro import KPipeline  # Updated to use the modern Pipeline

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This happens in the background. Cloud Run needs the port open FIRST.
    print("--- Loading Kokoro Model ---")
    try:
        # Use 'a' for American English or 'b' for British
        models["pipeline"] = KPipeline(lang_code='a', device='cpu')
        print("--- Model Loaded Successfully ---")
    except Exception as e:
        print(f"--- Model Load Failed: {e} ---")
    yield
    models.clear()

app = FastAPI(title="EngDraft Audio Generator", lifespan=lifespan)

class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def generate_audio(req: TTSRequest):
    if "pipeline" not in models:
        raise HTTPException(status_code=503, detail="Model still loading, please try again in a moment.")
    
    try:
        # KPipeline returns a generator of (graphemes, phonemes, audio)
        generator = models["pipeline"](req.text, voice='af_bella', speed=1)
        
        # Collect all audio chunks
        import numpy as np
        audio_chunks = [audio for _, _, audio in generator]
        final_audio = np.concatenate(audio_chunks)

        byte_io = io.BytesIO()
        wavfile.write(byte_io, 24000, final_audio) # Kokoro is 24kHz
        byte_io.seek(0)

        return StreamingResponse(byte_io, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "online", "model_loaded": "pipeline" in models}

if __name__ == "__main__":
    # Critical for Cloud Run: Default to 8080 and bind to 0.0.0.0
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)