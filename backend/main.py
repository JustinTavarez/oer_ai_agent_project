from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "meta-llama-3.1-8b-instruct"

class ChatRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return {"message": "Backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": request.prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        return {
            "response": result["choices"][0]["message"]["content"]
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"LM Studio request failed: {str(e)}"}
    except (KeyError, IndexError, ValueError) as e:
        return {"error": f"Unexpected response format: {str(e)}"}