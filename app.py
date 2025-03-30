import soundfile as sf
import urllib.request
import gradio as gr
import tempfile
import uuid
import re
import os

from kokoro_onnx import Kokoro
from datetime import datetime

voices_bin_path = "voices-v1.0.bin"
model_path = "kokoro-v1.0.onnx"

if not os.path.exists(model_path):
    print("Downloading kokoro-v1.0.onnx model file...")
    urllib.request.urlretrieve(
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        model_path
    )

if not os.path.exists(voices_bin_path):
    print("Downloading voices-v1.0.bin...")
    urllib.request.urlretrieve(
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
        voices_bin_path
    )

kokoro = None
voices_loaded = False

try:
    kokoro = Kokoro(model_path, voices_bin_path)
    print("Successfully loaded Kokoro with voices-v1.0.bin")
    voices_loaded = True
except Exception as e:
    print(f"Error loading Kokoro: {e}")

voice_options = []

try:
    if hasattr(kokoro, 'get_available_voices'):
        voice_options = kokoro.get_available_voices()
    elif hasattr(kokoro, 'voices'):
        voice_options = list(kokoro.voices.keys())
    if not voice_options and os.path.exists("voices-v1.0.bin"):
        import numpy as np
        try:
            voices_data = np.load("voices-v1.0.bin", allow_pickle=True)
            if isinstance(voices_data, dict):
                voice_options = list(voices_data.keys())
            elif isinstance(voices_data, np.ndarray) and hasattr(voices_data, 'dtype') and 'names' in voices_data.dtype.__dict__:
                voice_options = list(voices_data.dtype.names)
        except:
            print("Could not extract voices from binary file")
except Exception as e:
    print(f"Error extracting voice list: {e}")

if not voice_options:
    voice_options = [
        "af_sarah",
        "en_erin",
        "en_daniel",
        "en_vicki",
        "en_brandon",
        "ja_akira",
        "ja_naomi",
        "de_anna",
        "fr_elise",
        "es_carlos",
        "it_marco",
        "zh_mei",
        "ru_ivan",
        "ko_mina"
    ]

def group_voices_by_language():
    """Group voice options by language prefix"""
    grouped = {}
    for voice in voice_options:
        match = re.match(r'^([a-z]{2})_(.+)$', voice)
        if match:
            lang_code, name = match.groups()
            if lang_code not in grouped:
                grouped[lang_code] = []
            grouped[lang_code].append(voice)
        else:
            if 'other' not in grouped:
                grouped['other'] = []
            grouped['other'].append(voice)
    return grouped

grouped_voices = group_voices_by_language()

flat_voices = []
for lang_code, voices in grouped_voices.items():
    lang_name = {
        'af': 'Afrikaans',
        'en': 'English',
        'ja': 'Japanese',
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
        'it': 'Italian',
        'zh': 'Chinese',
        'ru': 'Russian',
        'ko': 'Korean',
        'other': 'Other'
    }.get(lang_code, lang_code.upper())
    
    for voice in voices:
        flat_voices.append(voice)

lang_options = ["en-us", "ja-jp", "en-gb", "zh-cn", "de-de", "es-es", "fr-fr", "it-it", "ko-kr", "pt-br", "ru-ru"]

def tts_generate(text, voice, speed, language):
    """Generate speech from text using Kokoro TTS"""
    global kokoro, voices_loaded
    
    if not text.strip():
        return None, "Please enter some text to generate speech."
    if not voices_loaded:
        try:
            kokoro = Kokoro(model_path, voices_bin_path)
            voices_loaded = True
            print("Successfully loaded Kokoro")
        except Exception as e:
            return None, f"Error initializing Kokoro TTS: {e}"
    
    try:
        samples, sample_rate = kokoro.create(
            text=text,
            voice=voice,
            speed=float(speed),
            lang=language
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"kokoro_{voice}_{timestamp}_{unique_id}.wav"
        
        temp_dir = tempfile.gettempdir()
        temp_audio_path = os.path.join(temp_dir, filename)
        sf.write(temp_audio_path, samples, sample_rate)
        
        return temp_audio_path, f"Generated audio with voice: {voice}, speed: {speed}, language: {language}"
    except Exception as e:
        return None, f"Error generating speech: {e}"

with gr.Blocks(title="Kokoro TTS Web UI", theme=gr.themes.Base()) as demo:
    with gr.Row():
        with gr.Column(scale=1):
            pass
        with gr.Column(scale=8):
            gr.Markdown("<h1 style='text-align: center;'>Kokoro TTS Web UI</h1>")
            gr.Markdown("<p style='text-align: center;'>Convert text to speech using Kokoro TTS</p>")
            
            with gr.Row():
                with gr.Column():
                    text_input = gr.Textbox(
                        label="Text to speak",
                        placeholder="Enter text to convert to speech...",
                        lines=5
                    )
                    
                    with gr.Row():
                        voice_dropdown = gr.Dropdown(
                            choices=flat_voices,
                            value="af_sarah",
                            label="Voice"
                        )
                        
                        language_dropdown = gr.Dropdown(
                            choices=lang_options,
                            value="en-us",
                            label="Language"
                        )
                    
                    speed_slider = gr.Slider(
                        minimum=0.5,
                        maximum=2.0,
                        value=1.0,
                        step=0.1,
                        label="Speech Speed"
                    )
                    
                    generate_btn = gr.Button("Generate Speech", variant="primary")
                    audio_output = gr.Audio(label="Generated Speech")
                    status_text = gr.Markdown("")
        with gr.Column(scale=1):
            pass
    
    generate_btn.click(
        fn=tts_generate,
        inputs=[text_input, voice_dropdown, speed_slider, language_dropdown],
        outputs=[audio_output, status_text]
    )

if __name__ == "__main__":
    demo.launch()
