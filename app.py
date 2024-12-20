from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
import librosa
import soundfile as sf
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
        # Получаем текст, pitch и speed из запроса
        data = request.get_json()
        text = data.get("text", "")
        pitch_factor = data.get("pitch_factor", 0.5)  # Значение по умолчанию — 0.5
        speed_factor = data.get("speed_factor", 1.2)  # Значение по умолчанию — 1.2

        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Генерируем аудиофайл
        output_path = "output.wav"
        tts.tts_to_file(text=text, file_path=output_path)

        # Преобразуем голос
        processed_path = "processed_output.wav"
        adjust_pitch_and_speed_with_librosa(output_path, processed_path, pitch_factor=float(pitch_factor), speed_factor=float(speed_factor))

        # Отправляем обработанный файл пользователю
        return send_file(processed_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def adjust_pitch_and_speed_with_librosa(input_path, output_path, pitch_factor=0.5, speed_factor=1.2):
    """
    Понижает высоту звука и изменяет скорость речи отдельно с помощью librosa.

    :param input_path: Путь к исходному аудиофайлу.
    :param output_path: Путь для сохранения обработанного файла.
    :param pitch_factor: Коэффициент изменения высоты звука (меньше 1 = ниже голос).
    :param speed_factor: Коэффициент изменения скорости речи (больше 1 = быстрее).
    """
    # Загрузка аудио
    y, sr = librosa.load(input_path, sr=None)

    # Изменение высоты звука
    # Вычисляем количество полутонов на основе pitch_factor
    n_steps = 12 * (pitch_factor - 1)  # Один октава = 12 полутонов
    y = librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps)

    # Изменение скорости речи
    y = librosa.effects.time_stretch(y, speed_factor)

    # Сохранение обработанного аудио
    sf.write(output_path, y, sr)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
