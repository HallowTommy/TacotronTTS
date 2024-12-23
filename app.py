from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os

app = Flask(__name__)

# Инициализация Coqui TTS с простой моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

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

        # Генерируем аудиофайл
        output_path = "output.wav"
        tts.tts_to_file(text=text, file_path=output_path)

        # Преобразуем голос с фиксированным значением pitch_factor = 0.6
        processed_path = "static/processed_output.wav"  # Сохраняем в папку static
        lower_pitch(output_path, processed_path)

        # Формируем полный URL для аудиофайла
        full_url = f"https://tacotrontts-production.up.railway.app/{processed_path}"
        return jsonify({"audio_url": full_url})

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

