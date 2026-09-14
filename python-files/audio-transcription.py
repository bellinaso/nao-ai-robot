import base64
import json
import os
import threading
import requests


class MyClass(GeneratedClass):
    """Transcreve arquivo de áudio utilizando a Google Cloud Speech-to-Text API."""

    DEFAULT_AUDIO_PATH = "/home/nao/recordings/audio_to_process.wav"
    API_KEY = "SAME-API-KEY-HERE"
    API_URL = "https://speech.googleapis.com/v1/speech:recognize?key="
    REQUEST_TIMEOUT = 25

    def __init__(self):
        GeneratedClass.__init__(self)
        self.tts = None
        self.worker_thread = None

    def onLoad(self):
        try:
            self.tts = ALProxy("ALTextToSpeech")
        except Exception as e:
            self.logger.error("Erro ao carregar ALTextToSpeech: {}".format(e))

    def onUnload(self):
        self.tts = None

    def safe_say(self, text):
        """Vocaliza mensagem de feedback se TTS estiver disponível."""
        if not self.tts or not text:
            return
        msg = str(text).strip()
        if msg:
            try:
                self.tts.say(msg)
            except Exception as e:
                self.logger.warning("Falha no TTS: {}".format(e))

    def onInput_onStart(self, audio_file_path=""):
        target_path = audio_file_path.strip() if audio_file_path else self.DEFAULT_AUDIO_PATH

        if not os.path.exists(target_path):
            self.logger.error("Arquivo de áudio não encontrado: {}".format(target_path))
            self.safe_say("Não encontrei o arquivo de áudio para transcrição.")
            self.transcriptedText("")
            self.onStopped("")
            return

        self.safe_say("Perfeito! Aguarde enquanto eu processo a sua pergunta e penso numa resposta.")

        self.worker_thread = threading.Thread(
            target=self.transcribe_and_output,
            args=[target_path]
        )
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def transcribe_and_output(self, file_path):
        transcript_result = ""

        try:
            with open(file_path, "rb") as audio_file:
                audio_content = audio_file.read()

            encoded_audio = base64.b64encode(audio_content).decode("utf-8")
            url = "{}{}".format(self.API_URL, self.API_KEY.strip())
            headers = {"Content-Type": "application/json"}
            payload = {
                "config": {
                    "encoding": "LINEAR16",
                    "sampleRateHertz": 48000,
                    "languageCode": "pt-BR",
                    "audioChannelCount": 4,
                    "enableSeparateRecognitionPerChannel": False
                },
                "audio": {
                    "content": encoded_audio
                }
            }

            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.REQUEST_TIMEOUT
            )

            if response.status_code != 200:
                self.logger.error("Erro na API de transcrição (HTTP {}): {}".format(
                    response.status_code, response.text))
                self.safe_say("Não consegui processar o áudio nos servidores.")
                return

            data = response.json()
            results = data.get("results", [])

            if results:
                alternatives = results[0].get("alternatives", [])
                if alternatives:
                    transcript_result = alternatives[0].get("transcript", "").strip()

            if transcript_result:
                self.logger.info("Transcrição obtida: {}".format(transcript_result))
            else:
                self.logger.info("Nenhuma fala reconhecida.")
                self.safe_say("Não entendi o que você disse.")

        except Exception as e:
            self.logger.error("Erro durante a transcrição: {}".format(e))
            self.safe_say("Tive um problema na transcrição do áudio.")

        finally:
            self.transcriptedText(str(transcript_result))
            self.onStopped(str(transcript_result))