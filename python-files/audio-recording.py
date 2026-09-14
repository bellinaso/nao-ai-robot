import os
import time


class MyClass(GeneratedClass):
    """Grava áudio dos microfones do NAO com detecção de silêncio e feedback por voz."""

    DEFAULT_RECORDING_PATH = "/home/nao/recordings/audio_to_process.wav"
    MIN_DURATION = 5.0
    MAX_DURATION = 15.0
    SILENCE_THRESHOLD = 800.0
    SILENCE_TIMEOUT = 1.5

    def __init__(self):
        GeneratedClass.__init__(self)
        self.tts = None
        self.audio_proxy = None
        self.recording_path = self.DEFAULT_RECORDING_PATH
        self.is_recording = False
        self.should_abort = False

    def onLoad(self):
        try:
            self.tts = ALProxy("ALTextToSpeech")
            self.audio_proxy = ALProxy("ALAudioDevice")
        except Exception as e:
            self.logger.error("Erro ao carregar proxies de áudio: {}".format(e))

    def onUnload(self):
        self.should_abort = True
        self._stop_recording_safe()
        self.tts = None
        self.audio_proxy = None

    def _say_with_warmup(self, text, delay=1.0):
        """Vocaliza texto com aquecimento de canal para conexão Bluetooth/PulseAudio."""
        if not self.tts or not text:
            return
        try:
            self.tts.say(" ")
            time.sleep(delay)
            self.tts.say(text)
        except Exception as e:
            self.logger.warning("Falha ao vocalizar: {}".format(e))

    def _stop_recording_safe(self):
        if self.is_recording and self.audio_proxy:
            try:
                self.audio_proxy.stopMicrophonesRecording()
            except Exception as e:
                self.logger.warning("Erro ao parar gravação: {}".format(e))
            finally:
                self.is_recording = False

    def onInput_onStart(self):
        self.should_abort = False
        recording_dir = os.path.dirname(self.recording_path)

        try:
            if not os.path.exists(recording_dir):
                os.makedirs(recording_dir)

            self._say_with_warmup("Estou ouvindo, pode falar agora.", delay=2.0)

            self.audio_proxy.startMicrophonesRecording(self.recording_path)
            self.is_recording = True

            start_time = time.time()
            silence_start = None

            while not self.should_abort:
                now = time.time()
                elapsed = now - start_time

                if elapsed >= self.MAX_DURATION:
                    self.logger.info("Tempo máximo de gravação atingido ({:.1f}s).".format(elapsed))
                    break

                mic_energy = self.audio_proxy.getFrontMicEnergy()

                if mic_energy < self.SILENCE_THRESHOLD:
                    if silence_start is None:
                        silence_start = now
                    elif (now - silence_start) >= self.SILENCE_TIMEOUT and elapsed >= self.MIN_DURATION:
                        self.logger.info("Silêncio detectado após tempo mínimo de gravação.")
                        break
                else:
                    silence_start = None

                time.sleep(0.1)

            self._stop_recording_safe()

            if self.should_abort:
                self.onStopped("")
                return

            self._say_with_warmup("Deixe-me pensar.", delay=1.0)
            self.onStopped(self.recording_path)

        except Exception as e:
            self.logger.error("Erro no processo de gravação: {}".format(e))
            self._stop_recording_safe()
            self._say_with_warmup("Tive um problema para gravar o áudio.", delay=1.0)
            self.onStopped("")

    def onInput_onStop(self):
        self.should_abort = True
        self._stop_recording_safe()
        self.onStopped("")