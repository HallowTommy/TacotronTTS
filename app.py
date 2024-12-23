from flask import Flask, request, jsonify, send_from_directory
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid

app = Flask(__name__)

# Инициализация Coqui TTS с моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

# Путь для сохранения аудиофайлов
OUTPUT_DIR = "generated_audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

        # Генерируем уникальное имя для аудиофайла
        unique_id = str(uuid.uuid4())
        output_path = os.path.join(OUTPUT_DIR, f"{unique_id}.wav")

        # Генерация TTS
        tts.tts_to_file(text=text, file_path=output_path)

        # Преобразование высоты звука
        processed_path = os.path.join(OUTPUT_DIR, f"{unique_id}_processed.wav")
        lower_pitch(output_path, processed_path)

        # Формирование ссылки на файл
        file_url = f"http://{request.host}/files/{unique_id}_processed.wav"

        # Возвращаем ссылку на аудиофайл
        return jsonify({"url": file_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/files/<path:filename>", methods=["GET"])
def serve_file(filename):
    """
    Обслуживает сгенерированные аудиофайлы.
    """
    return send_from_directory(OUTPUT_DIR, filename)

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
