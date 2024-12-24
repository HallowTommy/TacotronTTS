from flask import Flask, request, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid
import threading
import time

app = Flask(__name__, static_folder="static")

# Инициализация Coqui TTS с простой моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

# Словарь для отслеживания удаления файлов
delete_queue = {}

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

        # Убедимся, что обработанный файл создан
        if not os.path.exists(processed_path):
            return jsonify({"error": "Processed audio file not found."}), 500

        # Удаляем исходный файл
        os.remove(output_path)

        # Формируем полный URL для обработанного файла
        full_url = f"https://tacotrontts-production.up.railway.app/static/{processed_filename}"
        print(f"Generated audio file URL: {full_url}")

        # Добавляем в очередь на удаление
        delete_queue[processed_path] = time.time() + 300  # Удаление через 5 минут

        # Возвращаем JSON-ответ
        response = jsonify({"audio_url": full_url})
        response.headers["Content-Type"] = "application/json"  # Явно указываем JSON
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
def delete_file():
    try:
        data = request.get_json()
        file_path = data.get("file_path")

        if file_path:
            local_path = file_path.replace(
                "https://tacotrontts-production.up.railway.app/static/", "static/"
            )
            if os.path.exists(local_path):
                os.remove(local_path)
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

def cleanup_files():
    """Удаляет файлы, время которых истекло."""
    while True:
        current_time = time.time()
        for file_path, delete_time in list(delete_queue.items()):
            if current_time >= delete_time:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Deleted expired file: {file_path}")
                    del delete_queue[file_path]
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        time.sleep(60)  # Проверяем каждые 60 секунд

# Запускаем поток для очистки файлов
threading.Thread(target=cleanup_files, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

