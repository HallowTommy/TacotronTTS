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
        # Получаем текст и уровень pitch из запроса
        data = request.get_json()
        text = data.get("text", "")
        pitch_factor = data.get("pitch_factor", 0.5)  # Значение по умолчанию — 0.5

        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Генерируем аудиофайл
        output_path = "output.wav"
        tts.tts_to_file(text=text, file_path=output_path)

        # Преобразуем голос в низкий мужской
        processed_path = "processed_output.wav"
        lower_pitch(output_path, processed_path, pitch_factor=float(pitch_factor))

        # Отправляем обработанный файл пользователю
        return send_file(processed_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def lower_pitch(input_path, output_path, pitch_factor=0.5):
    """
    Понижает высоту звука для получения низкого голоса.

    :param input_path: Путь к исходному аудиофайлу.
    :param output_path: Путь для сохранения обработанного файла.
    :param pitch_factor: Коэффициент изменения высоты звука (меньше 1 = ниже голос).
    """
    audio = AudioSegment.from_file(input_path)
    # Изменяем частоту кадров для понижения высоты тона
    audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * pitch_factor)  # Уменьшаем частоту кадров
    }).set_frame_rate(audio.frame_rate)  # Возвращаем исходную частоту кадров
    audio.export(output_path, format="wav")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
