from flask import Flask, request, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid

app = Flask(__name__)

# Инициализация Coqui TTS с простой моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SHROKAI TTS is running!"})

@app.route("/generate", methods=["POST"])
def generate_audio():
    try:
        # Получаем текст из запроса
        data = request.get_json()
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Генерируем уникальное имя файла
        output_filename = f"{uuid.uuid4().hex}.wav"
        output_path = os.path.join(STATIC_DIR, output_filename)

        # Генерируем аудиофайл
        tts.tts_to_file(text=text, file_path=output_path)

        # Преобразуем голос с фиксированным значением pitch_factor = 0.6
        processed_filename = f"processed_{uuid.uuid4().hex}.wav"
        processed_path = os.path.join(STATIC_DIR, processed_filename)
        lower_pitch(output_path, processed_path)

        # Удаляем исходный файл
        os.remove(output_path)

        # Формируем полный URL для обработанного файла
        full_url = f"https://tacotrontts-production.up.railway.app/{STATIC_DIR}/{processed_filename}"
        return jsonify({"audio_url": full_url}), 200, {"Content-Type": "application/json"}

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
def delete_file():
    try:
        data = request.get_json()
        file_path = data.get("file_path")

        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"status": "success", "message": "File deleted successfully."})
        return jsonify({"status": "error", "message": "File not found."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def lower_pitch(input_path, output_path):
    """
    Понижает высоту звука с фиксированным pitch_factor = 0.6.
    """
    pitch_factor = 0.6  # Фиксированное значение
    audio = AudioSegment.from_file(input_path)
    audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * pitch_factor)
    }).set_frame_rate(audio.frame_rate)
    audio.export(output_path, format="wav")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
