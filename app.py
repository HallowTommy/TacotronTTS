from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import rubberband as pyrb
import numpy as np
import wave
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

        # Преобразуем голос в низкий мужской
        processed_path = "processed_output.wav"
        lower_pitch_preserve_tempo(output_path, processed_path, pitch_shift=-5)

        # Отправляем обработанный файл пользователю
        return send_file(processed_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def lower_pitch_preserve_tempo(input_path, output_path, pitch_shift=-5):
    """
    Изменяет высоту звука (pitch), сохраняя темп.
    """
    # Открываем WAV файл
    with wave.open(input_path, 'rb') as wav:
        params = wav.getparams()
        audio_frames = wav.readframes(params.nframes)

    # Преобразуем байты в массив NumPy
    audio_np = np.frombuffer(audio_frames, dtype=np.int16)

    # Применяем изменение высоты звука
    sample_rate = params.framerate
    shifted_audio = pyrb.pitch_shift(audio_np, sample_rate, pitch_shift)

    # Сохраняем обработанный файл
    with wave.open(output_path, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(shifted_audio.astype(np.int16).tobytes())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
