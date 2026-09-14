import json
import math
import time


class MyClass(GeneratedClass):
    """Recebe coordenadas visuais de detecção e executa ações de fala, apontamento e movimentação."""

    ENABLE_SPEECH = True
    ENABLE_POINTING = True
    ENABLE_BODY_TURN = False

    ARM_SPEED = 0.15
    HOLD_POSE_SECONDS = 3.0

    REST_JOINTS_L = ["LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LHand"]
    REST_ANGLES_L = [1.4, 0.15, -1.2, -0.5, 0.3]

    REST_JOINTS_R = ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RHand"]
    REST_ANGLES_R = [1.4, -0.15, 1.2, 0.5, 0.3]

    def __init__(self):
        GeneratedClass.__init__(self)
        self.motion_proxy = None
        self.tts_proxy = None
        self.object_name = "objeto"
        self.head_yaw = 0.0
        self.head_pitch = 0.0

    def onLoad(self):
        try:
            self.motion_proxy = ALProxy("ALMotion")
        except Exception as e:
            self.logger.error("Erro ao conectar ALMotion: {}".format(e))

        try:
            self.tts_proxy = ALProxy("ALTextToSpeech")
        except Exception as e:
            self.logger.warning("ALTextToSpeech indisponível: {}".format(e))

    def onUnload(self):
        self._reset_arms_pose()
        self.motion_proxy = None
        self.tts_proxy = None

    def onInput_onStop(self):
        self._reset_arms_pose()
        self.onStopped(False)

    def onInput_onStart(self, input_data):
        try:
            parsed_data = self._parse_input(input_data)
            if not parsed_data or not parsed_data.get("sucesso", False):
                self.logger.info("Objeto não detectado ou entrada inválida.")
                if self.ENABLE_SPEECH and self.tts_proxy:
                    self._speak_safe("Não encontrei o objeto.")
                self.onStopped(False)
                return

            self.object_name = parsed_data.get("objeto", "objeto")
            angles = parsed_data.get("angulos", {})
            self.head_yaw = float(angles.get("head_yaw_rad", 0.0))
            self.head_pitch = float(angles.get("head_pitch_rad", 0.0))

            yaw_deg = math.degrees(self.head_yaw)
            pitch_deg = math.degrees(self.head_pitch)
            self.logger.info("Objeto '{}' em Yaw: {:.2f}°, Pitch: {:.2f}°".format(
                self.object_name, yaw_deg, pitch_deg))

            if self.ENABLE_SPEECH:
                self._announce_detection()

            if self.ENABLE_POINTING:
                self._point_at_target()

            if self.ENABLE_BODY_TURN:
                self._turn_body_to_target()

            self.onStopped(True)

        except Exception as e:
            self.logger.error("Falha no processamento de recepção visual: {}".format(e))
            self.onStopped(False)

    def _parse_input(self, raw_input):
        if isinstance(raw_input, dict):
            return raw_input
        if isinstance(raw_input, str):
            return json.loads(raw_input)
        if isinstance(raw_input, (list, tuple)) and len(raw_input) >= 2:
            yaw = float(raw_input[0])
            pitch = float(raw_input[1])
            return {
                "sucesso": True,
                "objeto": "objeto",
                "angulos": {
                    "head_yaw_rad": yaw,
                    "head_pitch_rad": pitch,
                    "head_yaw_graus": math.degrees(yaw),
                    "head_pitch_graus": math.degrees(pitch)
                }
            }
        return None

    def _speak_safe(self, text):
        if not self.tts_proxy or not text:
            return
        try:
            self.tts_proxy.say(str(text))
        except Exception as e:
            self.logger.warning("Erro TTS: {}".format(e))

    def _announce_detection(self):
        if not self.tts_proxy:
            return

        for lang in ["Brazilian", "Portuguese"]:
            try:
                self.tts_proxy.setLanguage(lang)
                break
            except Exception:
                continue

        degrees_abs = abs(math.degrees(self.head_yaw))
        if self.head_yaw > 0.1:
            direction = "à esquerda"
        elif self.head_yaw < -0.1:
            direction = "à direita"
        else:
            direction = "à frente"

        message = "Encontrei {}! Está {} a {:.0f} graus.".format(
            self.object_name, direction, degrees_abs
        )
        self.logger.info(message)
        self._speak_safe(message)

    def _point_at_target(self):
        if not self.motion_proxy:
            return

        side = "L" if self.head_yaw >= 0 else "R"
        arm_chain = "{}Arm".format(side)

        try:
            self.motion_proxy.setStiffnesses(arm_chain, 1.0)
            time.sleep(0.2)

            pitch = max(-2.0, min(1.5, 0.2 + (self.head_pitch * 0.5)))
            if side == "L":
                roll = max(0.0, min(1.2, 0.3 + (self.head_yaw * 0.6)))
                elbow_yaw = -1.2
                elbow_roll = -0.3
            else:
                roll = max(-1.2, min(0.0, -0.3 + (self.head_yaw * 0.6)))
                elbow_yaw = 1.2
                elbow_roll = 0.3

            joints = [
                "{}ShoulderPitch".format(side),
                "{}ShoulderRoll".format(side),
                "{}ElbowYaw".format(side),
                "{}ElbowRoll".format(side),
                "{}WristYaw".format(side),
                "{}Hand".format(side)
            ]
            target_angles = [pitch, roll, elbow_yaw, elbow_roll, 0.0, 0.6]

            self.motion_proxy.setAngles(joints, target_angles, self.ARM_SPEED)
            time.sleep(1.5)
            time.sleep(self.HOLD_POSE_SECONDS)

        except Exception as e:
            self.logger.error("Erro ao apontar braço {}: {}".format(side, e))
        finally:
            self._reset_arms_pose()

    def _reset_arms_pose(self):
        if not self.motion_proxy:
            return
        try:
            self.motion_proxy.setAngles(self.REST_JOINTS_L, self.REST_ANGLES_L, 0.2)
            self.motion_proxy.setAngles(self.REST_JOINTS_R, self.REST_ANGLES_R, 0.2)
            time.sleep(1.0)
        except Exception as e:
            self.logger.warning("Falha ao retornar braços para descanso: {}".format(e))

    def _turn_body_to_target(self):
        if not self.motion_proxy:
            return
        try:
            self.motion_proxy.wakeUp()
            self.motion_proxy.moveInit()
            self.motion_proxy.moveTo(0.0, 0.0, self.head_yaw)
            self.motion_proxy.waitUntilMoveIsFinished()
            self.motion_proxy.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.0], 0.2)
            time.sleep(0.5)
        except Exception as e:
            self.logger.error("Erro ao girar corpo do robô: {}".format(e))