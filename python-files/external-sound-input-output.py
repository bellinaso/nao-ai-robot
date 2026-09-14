import os
import subprocess


class MyClass(GeneratedClass):
    """Configura os dispositivos padrão de entrada e saída de áudio no PulseAudio do NAO."""

    DEFAULT_SINK = "bluez_sink.F8_DF_15_D8_8D_D5"
    DEFAULT_SOURCE = "alsa_input.usb-Jieli_Technology_USB_Composite_Device_1120042102070620-00.analog-mono"

    def __init__(self):
        GeneratedClass.__init__(self)

    def onLoad(self):
        pass

    def onUnload(self):
        pass

    def _execute_pactl(self, command_args):
        try:
            self.logger.info("Executando pactl: {}".format(" ".join(command_args)))
            subprocess.call(["pactl"] + command_args)
        except Exception as e:
            self.logger.error("Erro ao executar pactl {}: {}".format(command_args, e))

    def set_system_audio_devices(self, sink_name=None, source_name=None):
        try:
            self.logger.info("Dispositivos PulseAudio disponíveis:")
            self._execute_pactl(["list", "short", "sinks"])
            self._execute_pactl(["list", "short", "sources"])

            if sink_name:
                self.logger.info("Definindo saída de áudio padrão: {}".format(sink_name))
                self._execute_pactl(["set-default-sink", sink_name])

            if source_name:
                self.logger.info("Definindo entrada de áudio padrão: {}".format(source_name))
                self._execute_pactl(["set-default-source", source_name])

        except Exception as e:
            self.logger.error("Falha ao configurar áudio PulseAudio: {}".format(e))

    def onInput_onStart(self):
        self.logger.info("Iniciando configuração de dispositivos de áudio...")
        self.set_system_audio_devices(
            sink_name=self.DEFAULT_SINK,
            source_name=self.DEFAULT_SOURCE
        )
        self.logger.info("Configuração de áudio concluída.")
        self.onStopped()

    def onInput_onStop(self):
        self.logger.info("Operação cancelada.")
        self.onStopped()