import json
import math
import time


class MyClass(GeneratedClass):
    """Realiza varredura com a cabeça do NAO para busca e reconhecimento visual de objetos."""

    HEAD_YAW_MIN = -0.785398  # -45 graus
    HEAD_YAW_MAX = 0.785398   # +45 graus
    HEAD_PITCH_NEUTRAL = 0.0
    HEAD_SPEED = 0.05
    CHECK_INTERVAL = 0.3
    TIMEOUT_SECONDS = 30.0
    SCAN_STEPS = 10

    VISION_MEMORY_KEY = "PictureDetected"
    SEARCH_ANY = "*"
    SUBSCRIBER_ID = "BuscaVisualNAO"

    def __init__(self):
        GeneratedClass.__init__(self)
        self.motion_proxy = None
        self.memory_proxy = None
        self.vision_proxy = None
        self.is_searching = False
        self.target_object = None
        self.detected_object_name = None

    def onLoad(self):
        try:
            self.motion_proxy = ALProxy("ALMotion")
            self.memory_proxy = ALProxy("ALMemory")
            self.vision_proxy = ALProxy("ALVisionRecognition")
        except Exception as e:
            self.logger.error("Erro ao inicializar proxies de visão/movimento: {}".format(e))

    def onUnload(self):
        self.is_searching = False
        self._stop_vision_module()
        self._center_head()
        self.motion_proxy = None
        self.memory_proxy = None
        self.vision_proxy = None

    def onInput_onStop(self):
        self.logger.info("Interrompendo busca visual.")
        self.is_searching = False

    def onInput_onStart(self, target_name):
        if not target_name or not target_name.strip():
            self.logger.warning("Nome de objeto alvo vazio ou inválido.")
            self._send_result(None, "")
            return

        self.target_object = target_name.strip()
        self.logger.info("Iniciando busca por objeto: {}".format(self.target_object))
        self._run_search_workflow()

    def onInput_onBuscarQualquer(self):
        self.target_object = self.SEARCH_ANY
        self.logger.info("Iniciando busca geral por qualquer objeto.")
        self._run_search_workflow()

    def _has_required_proxies(self):
        return bool(self.motion_proxy and self.memory_proxy and self.vision_proxy)

    def _start_vision_module(self):
        try:
            self.vision_proxy.pause(False)
            self.vision_proxy.subscribe(self.SUBSCRIBER_ID)
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error("Falha ao iniciar módulo de reconhecimento visual: {}".format(e))
            return False

    def _stop_vision_module(self):
        if not self.vision_proxy:
            return
        try:
            self.vision_proxy.unsubscribe(self.SUBSCRIBER_ID)
        except Exception:
            pass
        try:
            self.vision_proxy.pause(True)
        except Exception:
            pass

    def _center_head(self):
        if not self.motion_proxy:
            return
        try:
            self.motion_proxy.setAngles(["HeadYaw", "HeadPitch"], [0.0, self.HEAD_PITCH_NEUTRAL], 0.2)
        except Exception as e:
            self.logger.warning("Falha ao centralizar cabeça: {}".format(e))

    def _get_head_angles(self):
        try:
            yaw = self.motion_proxy.getAngles("HeadYaw", True)[0]
            pitch = self.motion_proxy.getAngles("HeadPitch", True)[0]
            return (yaw, pitch)
        except Exception as e:
            self.logger.error("Falha ao obter ângulos da cabeça: {}".format(e))
            return None

    def _check_memory_for_object(self):
        try:
            data = self.memory_proxy.getData(self.VISION_MEMORY_KEY)
            if not isinstance(data, (list, tuple)) or len(data) < 2:
                return False

            detected_objects = data[1]
            if not detected_objects:
                return False

            for item in detected_objects:
                if not item:
                    continue

                info = item[0]
                detected_name = str(info[0]) if isinstance(info, (list, tuple)) and info else str(info)
                if not detected_name:
                    continue

                if self.target_object == self.SEARCH_ANY:
                    self.detected_object_name = detected_name
                    return True

                target_lower = self.target_object.lower()
                detected_lower = detected_name.lower()
                if target_lower in detected_lower or detected_lower in target_lower:
                    self.detected_object_name = detected_name
                    return True

            return False

        except Exception as e:
            self.logger.warning("Erro ao ler memória visual: {}".format(e))
            return False

    def _sweep_head(self, start_angle, end_angle):
        increment = (end_angle - start_angle) / float(self.SCAN_STEPS)

        for step in range(self.SCAN_STEPS + 1):
            if not self.is_searching:
                return None

            current_angle = start_angle + (increment * step)
            try:
                self.motion_proxy.setAngles("HeadYaw", current_angle, self.HEAD_SPEED)
            except Exception as e:
                self.logger.warning("Erro no movimento de varredura: {}".format(e))
                continue

            time.sleep(self.CHECK_INTERVAL)

            if self._check_memory_for_object():
                return self._get_head_angles()

        return None

    def _run_search_workflow(self):
        if not self._has_required_proxies():
            self.logger.error("Proxies do NAOqi não inicializados.")
            self._send_result(None, self.target_object or "")
            return

        self.is_searching = True
        self.detected_object_name = None
        found_angles = None
        start_time = time.time()

        try:
            self.motion_proxy.setStiffnesses("Head", 1.0)
            if not self._start_vision_module():
                self._send_result(None, self.target_object or "")
                return

            self.motion_proxy.setAngles("HeadYaw", self.HEAD_YAW_MIN, self.HEAD_SPEED)
            self.motion_proxy.setAngles("HeadPitch", self.HEAD_PITCH_NEUTRAL, self.HEAD_SPEED)
            time.sleep(1.5)

            sweep_left_to_right = True

            while self.is_searching:
                if (time.time() - start_time) >= self.TIMEOUT_SECONDS:
                    self.logger.info("Tempo limite de busca visual excedido.")
                    break

                if sweep_left_to_right:
                    found_angles = self._sweep_head(self.HEAD_YAW_MIN, self.HEAD_YAW_MAX)
                else:
                    found_angles = self._sweep_head(self.HEAD_YAW_MAX, self.HEAD_YAW_MIN)

                if found_angles is not None:
                    self.logger.info("Objeto '{}' localizado com sucesso.".format(self.detected_object_name))
                    break

                sweep_left_to_right = not sweep_left_to_right

        except Exception as e:
            self.logger.error("Erro durante a busca visual: {}".format(e))
        finally:
            self._stop_vision_module()
            self.is_searching = False
            if found_angles is None:
                self._center_head()

        resolved_name = self.detected_object_name if self.target_object == self.SEARCH_ANY else self.target_object
        self._send_result(found_angles, resolved_name or "")

    def _send_result(self, angles, object_name):
        success = angles is not None
        yaw_rad, pitch_rad = angles if success else (0.0, 0.0)

        result = {
            "sucesso": success,
            "objeto": object_name,
            "angulos": {
                "head_yaw_rad": yaw_rad,
                "head_pitch_rad": pitch_rad,
                "head_yaw_graus": math.degrees(yaw_rad),
                "head_pitch_graus": math.degrees(pitch_rad)
            },
            "timestamp": time.time()
        }

        result_json = json.dumps(result, ensure_ascii=False)
        self.logger.info("Resultado da busca visual: {}".format(result_json))

        self.onStopped(result_json)
        if hasattr(self, "outputResultado"):
            self.outputResultado(result_json)