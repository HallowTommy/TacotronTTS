from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os

app = Flask(__name__)

# Инициализация Coqui TTS с простой моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

# Папка для хранения аудиофайлов
OUTPUT_DIR = "audio_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SHROKAI TTS is running!"})

@app.route("/generate", methods=["POST"])
def generate_audio():
    try:
        # Получаем текст и настройки из запроса
        data = request.get_json()
        text = data.get("text", "")
        pitch_factor = float(data.get("pitch_factor", 0.8))  # По умолчанию 0.8

        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Генерируем аудиофайл
        output_path = os.path.join(OUTPUT_DIR, "output.wav")
        tts.tts_to_file(text=text, file_path=output_path)

        # Преобразуем голос
        processed_path = os.path.join(OUTPUT_DIR, "processed_output.wav")
        lower_pitch(output_path, processed_path, pitch_factor)

        # Отправляем обработанный файл пользователю
        return send_file(processed_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def lower_pitch(input_path, output_path, pitch_factor):
    """
    Понижает высоту звука для получения низкого голоса.
    """
    audio = AudioSegment.from_file(input_path)
    
    # Рассчитываем новую частоту кадров
    new_frame_rate = int(audio.frame_rate * pitch_factor)
    if new_frame_rate <= 0:
        raise ValueError("Invalid pitch factor, resulting frame rate must be positive.")

    # Изменяем скорость воспроизведения для изменения высоты тона
    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
    audio = audio.set_frame_rate(audio.frame_rate)  # Устанавливаем новый frame_rate

    # Экспортируем файл
    audio.export(output_path, format="wav")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
