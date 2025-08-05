from flask import Flask, render_template, request
import openai
import replicate
from PIL import Image
import os
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# API keys from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "L6vNCySpJygzavqMH5vx"

def get_caption(image_path):
    with open(image_path, "rb") as f:
        image_data = f.read()

    output = replicate.run(
        "salesforce/blip:3b9cfc2f8995b587feaf3e9c25dc70ca17be14a70f4c39e1ff3978b15d3111e2",
        input={"image": image_data, "task": "caption"}
    )
    return output

def generate_ongo_prompt(caption):
    return f"""
You are Ongo Gablogian a high-society art critic and self-proclaimed tastemaker. 

You’ve just encountered the following piece:

"{caption}"

Answer in exactly two short sentences. 

Your tone should blend elite gallery snob, failed poet, and coked-out performance artist.
"""

def generate_audio(text, output_path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
    else:
        print("❌ ElevenLabs error:", response.status_code)
        print(response.text)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    image = request.files['image']
    if not image or image.filename == '':
        return "No image uploaded", 400

    filename = image.filename
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(image_path)

    caption = get_caption(image_path)

    prompt = generate_ongo_prompt(caption)
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}]
    )
    critique = response['choices'][0]['message']['content']

    audio_path = os.path.join("static", "audio", "output.mp3")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    generate_audio(critique, audio_path)

    return render_template(
        "result.html",
        critique=critique,
        image_url=f"/static/uploads/{filename}",
        audio_url=f"/static/audio/output.mp3"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)