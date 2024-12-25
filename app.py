from flask import Flask, request, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid
import paramiko  # Для отправки файла через SCP

app = Flask(__name__, static_folder="static")

# Инициализация Coqui TTS с простой моделью
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

# Настройки для VPS
VPS_HOST = "95.179.247.70"  # IP-адрес вашего VPS
VPS_USERNAME = "root"       # Имя пользователя (в данном случае root)
VPS_PASSWORD = "hackme"  # Пароль для входа на VPS
VPS_DEST_PATH = "/tmp/tts_audio.wav"  # Путь, куда будем отправлять аудио

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

        # Генерация файла
        print(f"Generating TTS audio for text: {text}")
        output_filename = f"{uuid.uuid4().hex}.wav"
        output_path = os.path.join(STATIC_DIR, output_filename)
        tts.tts_to_file(text=text, file_path=output_path)

        # Проверяем, создан ли файл
        if not os.path.exists(output_path):
            raise Exception(f"Generated audio file not found at {output_path}")

        print(f"Audio generated: {output_path}")

        # Преобразование высоты тона
        processed_filename = f"processed_{uuid.uuid4().hex}.wav"
        processed_path = os.path.join(STATIC_DIR, processed_filename)
        lower_pitch(output_path, processed_path)

        # Проверяем, обработан ли файл
        if not os.path.exists(processed_path):
            raise Exception(f"Processed audio file not found at {processed_path}")

        print(f"Processed audio file: {processed_path}")

        # Отправка файла на VPS
        send_audio_to_vps(processed_path)
        print("Audio sent to VPS successfully.")

        # Удаление временных файлов
        os.remove(output_path)
        os.remove(processed_path)
        print("Temporary files deleted.")

        return jsonify({"status": "success", "message": "File sent to VPS successfully."})

    except Exception as e:
        print(f"Error in generate_audio: {e}")
        return jsonify({"error": str(e)}), 500

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

def send_audio_to_vps(file_path):
    import paramiko

    try:
        # Подключение к VPS
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USERNAME, password=VPS_PASSWORD)

        # Передача файла
        sftp = ssh.open_sftp()
        sftp.put(file_path, VPS_DEST_PATH)  # Локальный файл -> удаленный путь
        sftp.close()
        ssh.close()
        print("File successfully sent to VPS.")

    except Exception as e:
        print(f"Error sending file to VPS: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
