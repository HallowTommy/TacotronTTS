from flask import Flask, request, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid
import paramiko  # Для передачи файла через SCP

# Настройки Flask приложения
app = Flask(__name__, static_folder="static")

# Инициализация Coqui TTS с моделью Tacotron2
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)

# Настройки для VPS
VPS_HOST = "95.179.247.70"  # IP-адрес вашего VPS
VPS_USERNAME = "root"       # Имя пользователя для входа
VPS_PASSWORD = "hackme"    # Пароль для входа на VPS
VPS_DEST_PATH = "/tmp/tts_audio.wav"  # Путь для аудиофайла на VPS

# Директория для временных файлов
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SHROKAI TTS is running!"})

@app.route("/generate", methods=["POST"])
def generate_audio():
    try:
        # Получение текста из запроса
        data = request.get_json()
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Генерация уникального имени файла
        output_filename = f"{uuid.uuid4().hex}.wav"
        output_path = os.path.join(STATIC_DIR, output_filename)

        # Генерация аудиофайла с помощью TTS
        print(f"Генерация аудио для текста: {text}")
        tts.tts_to_file(text=text, file_path=output_path)

        # Проверяем, создан ли файл
        if not os.path.exists(output_path):
            raise Exception(f"Файл аудио не найден: {output_path}")

        print(f"Аудио сгенерировано: {output_path}")

        # Отправка файла на VPS
        send_audio_to_vps(output_path)
        print("Аудиофайл успешно отправлен на VPS.")

        # Удаление временных файлов
        os.remove(output_path)
        print("Временные файлы удалены.")

        return jsonify({"status": "success", "message": "Файл успешно отправлен на VPS."})

    except Exception as e:
        print(f"Ошибка: {e}")
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
    """
    Отправляет аудиофайл на VPS через SCP.
    """
    try:
        # Подключение к VPS
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USERNAME, password=VPS_PASSWORD)

        # Передача файла через SCP
        sftp = ssh.open_sftp()
        sftp.put(file_path, VPS_DEST_PATH)  # Локальный файл -> путь на VPS
        sftp.close()
        ssh.close()
        print("Файл успешно отправлен на VPS.")

    except Exception as e:
        print(f"Ошибка при отправке файла на VPS: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
