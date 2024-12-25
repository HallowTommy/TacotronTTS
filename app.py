from flask import Flask, request, jsonify, send_file
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid
import paramiko

app = Flask(__name__, static_folder="static")

# Инициализация Coqui TTS с моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

# Настройки для VPS
VPS_HOST = "95.179.247.70"  # IP-адрес вашего VPS
VPS_USERNAME = "root"       # Имя пользователя
VPS_PASSWORD = "hackme"     # Пароль
VPS_DEST_PATH = "/tmp/tts_audio.wav"  # Путь на VPS

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

        # Генерация аудио
        tts.tts_to_file(text=text, file_path=output_path)

        # Понижаем высоту звука
        processed_filename = f"processed_{uuid.uuid4().hex}.wav"
        processed_path = os.path.join(STATIC_DIR, processed_filename)
        lower_pitch(output_path, processed_path)

        # Убедимся, что файл существует
        if not os.path.exists(processed_path):
            return jsonify({"error": "Processed audio file not found."}), 500

        # Отправляем файл на VPS
        send_file_to_vps(processed_path)

        # Удаляем временные файлы
        os.remove(output_path)
        os.remove(processed_path)

        return jsonify({"status": "success", "message": "File sent to VPS successfully."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def lower_pitch(input_path, output_path):
    """
    Понижает высоту звука с фиксированным pitch_factor = 0.6.
    """
    pitch_factor = 0.6
    audio = AudioSegment.from_file(input_path)
    audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * pitch_factor)
    }).set_frame_rate(audio.frame_rate)
    audio.export(output_path, format="wav")

def send_file_to_vps(file_path):
    """
    Отправляет аудиофайл на VPS через SCP.
    """
    try:
        # Подключение к VPS
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USERNAME, password=VPS_PASSWORD)

        # Передача файла
        sftp = ssh.open_sftp()
        sftp.put(file_path, VPS_DEST_PATH)
        sftp.close()
        ssh.close()
        print("File successfully sent to VPS.")

    except Exception as e:
        print(f"Error sending file to VPS: {e}")
        raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
