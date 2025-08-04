
from flask import Flask, render_template, request, jsonify
import openai
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
import os
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 🔑 Replace with your OpenAI API key
openai.api_key = "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"

# 🧠 Load BLIP model for image-to-text
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

ELEVENLABS_API_KEY = "sk_da82c1d3921e94dae9422671d0ad8ab5442db9516894c4d2"  
VOICE_ID = "L6vNCySpJygzavqMH5vx"           

def get_caption(image_path):
    image = Image.open(image_path).convert('RGB')
    inputs = processor(images=image, return_tensors="pt").to(device)
    out = model.generate(**inputs)
    return processor.decode(out[0], skip_special_tokens=True)

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
        return jsonify({'error': 'No image uploaded'}), 400

    filename = image.filename
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(image_path)

    # Step 1: Get image caption
    caption = get_caption(image_path)

    # Step 2: Generate GPT critique
    prompt = generate_ongo_prompt(caption)
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}]
    )
    critique = response['choices'][0]['message']['content']

    # Step 3: Generate audio
    audio_path = os.path.join("static", "audio", "output.mp3")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    generate_audio(critique, audio_path)

    # Step 4: Return result as JSON
    return jsonify({
        'critique': critique,
        'image_url': f"/static/uploads/{filename}",
        'audio_url': f"/static/audio/output.mp3"
    })

if __name__ == "__main__":
    app.run(debug=True)