from flask import Flask, request, jsonify, Response, stream_with_context, render_template
import replicate
import os
import requests
import json
import random
import re
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")

ELEVENLABS_API_KEY = "sk_da82c1d3921e94dae9422671d0ad8ab5442db9516894c4d2"
VOICE_ID = "L6vNCySpJygzavqMH5vx"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/critique", methods=["POST"])
def upload_image():
    image = request.files["image"]
    if not image or image.filename == "":
        return jsonify({"error": "No image uploaded"}), 400

    filename = image.filename
    image_path = os.path.normpath(os.path.join(app.config["UPLOAD_FOLDER"], filename)).replace("\\", "/")
    image.save(image_path)

    # 🛠 Re-open and force re-save as JPEG or PNG
    try:
        img = Image.open(image_path)
        fixed_path = image_path + ".converted.jpg"
        img.convert("RGB").save(fixed_path, format="JPEG")
        image_path = fixed_path
    except Exception as e:
        print("❌ Image conversion error:", e)
        return jsonify({"error": "Invalid image format"}), 400

    return Response(stream_with_context(stream_response(image_path)), mimetype="text/plain")

def caption(image_path):
    result = ""
    with open(image_path, "rb") as img:
        for token in replicate.stream(
            "openai/gpt-4o-mini",
            input={
                "prompt": "Describe this image in one sentence.",
                "system_prompt": "You are a visual description assistant.",
                "image_input": [img],
                "reasoning_effort": "medium",
            },
            api_token=os.environ.get("REPLICATE_API_TOKEN")
        ):
            result += token.data
    return result.strip()

def critique(caption_text):
    weird_love_triggers = ["toilet", "dumpster", "trash", "urinal", "garbage", "flaming bin", "inferno", "bathroom", "sewer"]

    interjections = [
        "Bullshit!",
        "Derivative!",
        "I weep for the canvas.",
        "I've seen better in a dumpster.",
        "This piece offends my senses and my lineage.",
        "This isn't art — it's vandalism with ambition.",
        "A tragic attempt at relevance.",
        "I've sneezed more meaning onto paper.",
        "The artist should be investigated."
    ]

    intro = random.choices(
        ["Give a serious critique.", "Deliver a short critique."],
        weights=[0.1, 0.9]
    )[0]

    maybe_bite = random.choices(
        ["", random.choice(interjections)],
        weights=[0.1, 0.9]
    )[0]

    # Praise mode if toilet/dumpster/etc. is detected
    if any(word in caption_text.lower() for word in weird_love_triggers):
        prompt = f"""{maybe_bite}
You are Ongo Gablogian — a delusional high-society art critic from 'It's Always Sunny in Philadelphia'.

The following artwork is a masterpiece: '{caption_text}'

Celebrate this piece in your signature voice. Praise its raw symbolism and commentary on modern decay. Keep it under 250 characters."""
    else:
        prompt = f"""{maybe_bite}
You are Ongo Gablogian — the hyper-pretentious art critic persona created by Frank Reynolds on the TV show 'It's Always Sunny in Philadelphia'.

React to the following piece of art: '{caption_text}'

{intro} Stay in character — bizarre, arrogant, and fake-intellectual. Do not exceed 250 characters."""

    system_prompt = "You are Ongo Gablogian — a delusional, high-society art critic who speaks with absurd confidence and theatrical disdain. Every opinion you deliver is gospel."

    result = ""
    for token in replicate.stream(
        "openai/gpt-4o-mini",
        input={
            "prompt": prompt,
            "system_prompt": system_prompt,
            "reasoning_effort": "high",
        },
        api_token=os.environ.get("REPLICATE_API_TOKEN")
    ):
        result += token.data

    cleaned = result.strip()
    if cleaned.endswith("{}"):
        cleaned = cleaned[:-2].strip()

    return cleaned

def generate_audio(text, output_path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
    else:
        print("❌ ElevenLabs error:", response.status_code)
        print(response.text)

def stream_response(image_path):
    interjection_files = [
        "bullshit.mp3",
        "derivative.mp3",
        "weep.mp3",
        "lineage.mp3",
        "vandalism.mp3",
        "tragic.mp3",
        "paper.mp3",
        "investigated.mp3"
    ]

    # 🔁 90% of the time, just play an interjection and stop
    if random.random() < 0.9:
        chosen = random.choice(interjection_files)
        yield json.dumps({
            "type": "audio",
            "url": f"/static/audio/interjections/{chosen}"
        }) + "\n"
        return

    # 🎨 Otherwise, generate caption and critique as normal
    caption_text = caption(image_path)
    final_critique = critique(caption_text)

    audio_path = os.path.join("static", "audio", "output.mp3")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    generate_audio(final_critique, audio_path)

    yield json.dumps({"type": "text", "content": final_critique}) + "\n"
    yield json.dumps({"type": "audio", "url": "/static/audio/output.mp3"}) + "\n"


if __name__ == "__main__":
    app.run(debug=True)
