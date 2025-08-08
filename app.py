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
os.environ["ELEVENLABS_API_KEY"] = os.getenv("ELEVENLABS_API_KEY"}
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

    # Praise mode if toilet/dumpster/etc. is detected
    if any(word in caption_text.lower() for word in weird_love_triggers):
        prompt = f"""You are Ongo Gablogian — a delusional high-society art critic from 'It's Always Sunny in Philadelphia'.

The following artwork is a masterpiece: '{caption_text}'

Celebrate this piece in your signature voice. Praise its raw symbolism and commentary on modern decay. Keep it under 250 characters."""
    else:
        prompt = f"""You are Ongo Gablogian — the hyper-pretentious art critic persona created by Frank Reynolds on the TV show 'It's Always Sunny in Philadelphia'.

React to the following piece of art: '{caption_text}'

Stay in character — bizarre, arrogant, and fake-intellectual. Do not exceed 250 characters."""

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
    interjections = {
        "Bullshit!": "static/audio/interjections/bullshit.mp3",
        "Derivative!": "static/audio/interjections/derivative.mp3",
        "I weep for the canvas.": "static/audio/interjections/weep.mp3",
        "This piece offends my senses and my lineage.": "static/audio/interjections/lineage.mp3",
        "This isn't art — it's vandalism with ambition.": "static/audio/interjections/vandalism.mp3",
        "A tragic attempt at relevance.": "static/audio/interjections/tragic.mp3",
        "I've sneezed more meaning onto paper.": "static/audio/interjections/paper.mp3",
        "The artist should be investigated.": "static/audio/interjections/investigated.mp3",
    }

    # 30% of the time, fire off a pre-recorded interjection
    if random.random() < 0.3:
        text, audio_path = random.choice(list(interjections.items()))
        yield json.dumps({ "type": "text", "content": text }) + "\n"
        yield json.dumps({ "type": "audio", "url": "/" + audio_path}) + "\n"
        return

    # Otherwise, continue with captioning + critique
    caption_text = caption(image_path)
    final_critique = critique(caption_text)

    audio_path = os.path.join("static", "audio", "output.mp3")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    generate_audio(final_critique, audio_path)

    yield json.dumps({ "type": "text", "content": final_critique }) + "\n"
    yield json.dumps({ "type": "audio", "url": "/static/audio/output.mp3?t=" + str(random.randint(1000,9999)) }) + "\n"

if __name__ == "__main__":
    app.run(debug=True)
