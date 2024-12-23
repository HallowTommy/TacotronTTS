from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import io

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

        # Генерируем аудиофайл в памяти
        output_buffer = io.BytesIO()
        tts.tts_to_file(text=text, file_path=output_buffer)
        output_buffer.seek(0)

        # Преобразуем голос в памяти с фиксированным pitch_factor = 0.6
        processed_buffer = lower_pitch(output_buffer)

        # Отправляем обработанный файл пользователю
        return send_file(
            processed_buffer,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="processed_output.wav"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
def delete_file():
    return jsonify({"status": "success", "message": "File deletion is not required in memory-based processing."})

def lower_pitch(input_buffer):
    """
    Понижает высоту звука с фиксированным pitch_factor = 0.6.
    """
    pitch_factor = 0.6  # Фиксированное значение
    input_buffer.seek(0)  # Возвращаем указатель в начало
    audio = AudioSegment.from_file(input_buffer)
    audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * pitch_factor)
    }).set_frame_rate(audio.frame_rate)

    # Сохраняем в новый буфер
    output_buffer = io.BytesIO()
    audio.export(output_buffer, format="wav")
    output_buffer.seek(0)
    return output_buffer

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
