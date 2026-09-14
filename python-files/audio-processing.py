import json
import threading
import time
import requests


class MyClass(GeneratedClass):
    """Envia pergunta transcrita para a API Gemini e vocaliza a resposta via TTS."""

    API_KEY = "API-KEY-HERE"
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key="
    REQUEST_TIMEOUT = 25

    def __init__(self):
        GeneratedClass.__init__(self)
        self.tts = None
        self.worker_thread = None

    def onLoad(self):
        try:
            self.tts = ALProxy("ALTextToSpeech")
        except Exception as e:
            self.logger.error("Falha ao inicializar ALTextToSpeech: {}".format(e))

    def onUnload(self):
        self.tts = None

    def safe_say(self, text, warmup=True):
        """Vocaliza o texto com aquecimento de áudio para evitar cortes em saídas Bluetooth."""
        if not self.tts or not text:
            return

        text_to_say = str(text).strip()
        if not text_to_say:
            return

        try:
            if warmup:
                self.tts.say(" ")
                time.sleep(2)
            self.tts.say(text_to_say)
        except Exception as e:
            self.logger.error("Erro no TTS: {}".format(e))

    def onInput_transcriptedText(self, question_text):
        if not question_text or not question_text.strip():
            self.onStopped()
            return

        self.worker_thread = threading.Thread(
            target=self.get_response_and_speak,
            args=[question_text.strip()]
        )
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def get_response_and_speak(self, question):
        try:
            self.safe_say("Entendi, vamos lá.")

            url = "{}{}".format(self.API_URL, self.API_KEY.strip())
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": question}]}]}

            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            answer = None
            candidates = data.get("candidates")
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    answer = parts[0].get("text")

            if answer:
                self.safe_say(answer)
            else:
                self.safe_say("Não consegui encontrar uma resposta para isso.")

        except Exception as e:
            self.logger.error("Erro na requisição Gemini: {}".format(e))
            self.safe_say("Tive um problema para gerar a resposta.")

        finally:
            self.onStopped()