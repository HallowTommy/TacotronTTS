from flask import Flask, request, jsonify
from TTS.api import TTS
from pydub import AudioSegment
import os
import uuid
import paramiko  # Для передачи файлов через SCP
import logging
import subprocess

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s]: %(message)s')
logger = logging.getLogger()

app = Flask(__name__, static_folder="static")

# Инициализация модели TTS
MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"
tts = TTS(MODEL_NAME, progress_bar=False)
logger.info("TTS model initialized: %s", MODEL_NAME)

# Настройки для VPS
VPS_HOST = "95.179.247.70"  # IP-адрес вашего VPS
VPS_USERNAME = "root"       # Имя пользователя
VPS_PASSWORD = "{S9j}DfJ-xH.zBkt"  # Пароль
VPS_DEST_PATH = "/tmp/tts_files"  # Путь для хранения файлов на VPS

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
logger.info("Static directory created: %s", STATIC_DIR)

# Функция для проверки наличия ffmpeg
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("ffmpeg is installed.")
    except FileNotFoundError:
        logger.error("ffmpeg is not installed. Please install ffmpeg.")
        raise Exception("ffmpeg is required but not installed.")
    except subprocess.CalledProcessError as e:
        logger.error("Error checking ffmpeg version: %s", e)
        raise

check_ffmpeg()  # Проверяем наличие ffmpeg перед обработкой аудио

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SHROKAI TTS is running!"})

@app.route("/generate", methods=["POST"])
def generate_audio():
    try:
        logger.info("Received request to generate audio.")

        # Получение текста из запроса
        data = request.get_json()
        text = data.get("text", "")
        logger.debug("Text received: %s", text)

        if not text:
            logger.error("No text provided in the request.")
            return jsonify({"error": "Text is required"}), 400

        # Генерация имени файла
        output_filename = f"{uuid.uuid4().hex}.wav"
        output_path = os.path.join(STATIC_DIR, output_filename)
        logger.debug("Generated output file path: %s", output_path)

        # Генерация аудио
        tts.tts_to_file(text=text, file_path=output_path)
        logger.info("Audio file generated: %s", output_path)

        # Проверка существования файла
        if not os.path.exists(output_path):
            logger.error(f"Generated WAV file not found: {output_path}")
            return jsonify({"error": "Generated WAV file not found"}), 500

        # Изменение высоты звука
        processed_filename = f"processed_{uuid.uuid4().hex}.wav"
        processed_path = os.path.join(STATIC_DIR, processed_filename)
        lower_pitch(output_path, processed_path)
        logger.info("Processed audio file created: %s", processed_path)

        # Конвертация в OGG
        ogg_filename = f"{uuid.uuid4().hex}.ogg"
        ogg_path = os.path.join(STATIC_DIR, ogg_filename)
        convert_to_ogg(processed_path, ogg_path)
        logger.info("Converted to OGG: %s", ogg_path)

        # Проверка существования файла OGG
        if not os.path.exists(ogg_path):
            logger.error(f"OGG file not found: {ogg_path}")
            return jsonify({"error": "OGG file not found"}), 500

        # Логируем текущий список файлов перед передачей
        logger.debug(f"Files in {STATIC_DIR}: {os.listdir(STATIC_DIR)}")

        # Отправка файла на VPS
        logger.info("Attempting to send file to VPS: %s", VPS_HOST)
        transfer_successful = send_file_to_vps(ogg_path)

        if not transfer_successful:
            logger.error("Failed to transfer file to VPS.")
            return jsonify({"error": "Failed to transfer file to VPS."}), 500

        # Удаление временных файлов
        logger.info(f"Deleting local files: {output_path}, {processed_path}, {ogg_path}")
        os.remove(output_path)
        os.remove(processed_path)
        os.remove(ogg_path)
        logger.info("Temporary files deleted.")

        return jsonify({"status": "success", "message": "File sent to VPS successfully."})

    except Exception as e:
        logger.error("Error during audio generation: %s", str(e))
        return jsonify({"error": str(e)}), 500
        
def lower_pitch(input_path, output_path):
    """
    Понижает высоту звука с фиксированным pitch_factor = 0.6.
    """
    try:
        logger.info("Lowering pitch of the audio.")
        pitch_factor = 0.6
        audio = AudioSegment.from_file(input_path)
        audio = audio._spawn(audio.raw_data, overrides={
            "frame_rate": int(audio.frame_rate * pitch_factor)
        }).set_frame_rate(audio.frame_rate)
        audio.export(output_path, format="wav")
        logger.info("Pitch adjustment complete: %s", output_path)
    except Exception as e:
        logger.error("Error lowering pitch: %s", str(e))
        raise

def convert_to_ogg(input_path, output_path):
    """
    Конвертирует WAV файл в OGG.
    """
    try:
        logger.info("Converting to OGG.")
        subprocess.run(["ffmpeg", "-i", input_path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "128k", output_path], check=True)
        logger.info("Conversion complete: %s", output_path)
    except Exception as e:
        logger.error("Error converting to OGG: %s", str(e))
        raise

def send_file_to_vps(file_path):
    """
    Отправляет файл на VPS через SCP и возвращает результат.
    """
    try:
        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        logger.info("Connecting to VPS at %s", VPS_HOST)

        # Установка SSH соединения
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_HOST, username=VPS_USERNAME, password=VPS_PASSWORD)
        logger.info("Connected to VPS successfully.")

        # Передача файла
        sftp = ssh.open_sftp()
        dest_path = os.path.join(VPS_DEST_PATH, os.path.basename(file_path))
        logger.info(f"Uploading file to {dest_path}...")
        sftp.put(file_path, dest_path)
        sftp.close()
        ssh.close()
        logger.info("File successfully sent to VPS: %s", dest_path)

        return True

    except FileNotFoundError as e:
        logger.error("Local file not found during SCP: %s", str(e))
        return False
    except paramiko.SSHException as e:
        logger.error("SSH connection error: %s", str(e))
        return False
    except Exception as e:
        logger.error("Error sending file to VPS: %s", str(e))
        return False

    except Exception as e:
        logger.error("Error sending file to VPS: %s", str(e))
        return False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
