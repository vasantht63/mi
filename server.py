import asyncio
import websockets
import json
from vosk import Model, KaldiRecognizer
import requests
import os
import zipfile

# Auto-download Vosk Japanese model if not present
MODEL_DIR = "model"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip"

if not os.path.exists(MODEL_DIR):
    print("Downloading Vosk Japanese model...")
    r = requests.get(MODEL_URL, stream=True)
    with open("model.zip", "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    with zipfile.ZipFile("model.zip", "r") as zip_ref:
        zip_ref.extractall(MODEL_DIR)
    os.remove("model.zip")
    print("Model downloaded and extracted.")

# Load Vosk model
model = Model(MODEL_DIR)

# Translate JA -> EN
def translate(text):
    try:
        r = requests.post(
            "https://libretranslate.de/translate",
            data={"q": text, "source": "ja", "target": "en"}
        )
        return r.json().get("translatedText", text)
    except Exception as e:
        print("Translation error:", e)
        return text

# WebSocket handler
async def recognize(websocket):
    recognizer = KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)

    async for message in websocket:
        if recognizer.AcceptWaveform(message):
            result = json.loads(recognizer.Result())
            jp_text = result.get("text", "")
            if jp_text:
                en_text = translate(jp_text)
                await websocket.send(json.dumps({"jp": jp_text, "en": en_text}))
        else:
            partial = json.loads(recognizer.PartialResult())
            await websocket.send(json.dumps({"partial": partial.get("partial", "")}))

# Main function
async def main():
    port = int(os.environ.get("PORT", 8080))  # Render sets PORT automatically
    async with websockets.serve(recognize, "0.0.0.0", port):
        print(f"🚀 Japanese→English Caption Server online at ws://0.0.0.0:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
