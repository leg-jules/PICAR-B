#!/usr/bin/env python3

import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685


class ServoController:
    def __init__(
        self,
        i2c_address=0x5f,
        frequency=50,
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
        offsets=None
    ):
        """
        Initialise le contrôleur PCA9685 et prépare la gestion des servos.

        i2c_address : adresse I2C du module PCA9685
        frequency : fréquence PWM utilisée par les servos
        min_pulse / max_pulse : limites du signal PWM du servo
        actuation_range : plage d'angle du servo, généralement 180°
        offsets : dictionnaire contenant les offsets par canal
        """

        # Création du bus I2C avec les broches SCL et SDA du Raspberry Pi
        self.i2c = busio.I2C(SCL, SDA)

        # Initialisation du module PCA9685
        self.pca = PCA9685(self.i2c, address=i2c_address)
        self.pca.frequency = frequency

        # Dictionnaire pour stocker les servos déjà créés
        self.servos = {}

        # Paramètres des servos
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.actuation_range = actuation_range

        # Offsets des servos
        # Par défaut, le canal 0 a un offset de 8°
        self.offsets = offsets if offsets is not None else {
            0: 8,  # Offset pour le servo canal 0 qui gère la direction
        }

    def get_servo(self, channel):
        """
        Retourne le servo correspondant au canal demandé.

        Si le servo n'existe pas encore dans le dictionnaire,
        il est créé puis sauvegardé.
        """

        if channel not in self.servos:
            self.servos[channel] = servo.Servo(
                self.pca.channels[channel],
                min_pulse=self.min_pulse,
                max_pulse=self.max_pulse,
                actuation_range=self.actuation_range
            )

        return self.servos[channel]

    def set_angle(self, channel, angle):
        """
        Définit l'angle d'un servo en appliquant l'offset du canal.

        channel : canal du PCA9685
        angle : angle demandé par l'utilisateur
        """

        # Récupération de l'offset du canal
        # Si aucun offset n'est défini, on utilise 0
        offset = self.offsets.get(channel, 0)

        # Application de l'offset
        corrected_angle = angle + offset

        # Sécurité : on bloque l'angle entre 0° et 180°
        corrected_angle = max(0, min(180, corrected_angle))

        # Récupération du servo puis envoi de l'angle corrigé
        selected_servo = self.get_servo(channel)
        selected_servo.angle = corrected_angle

        print(
            f"Servo sur le canal {channel} demandé à {angle}° "
            f"-> envoyé à {corrected_angle}°"
        )

    def ask_int(self, message, minimum, maximum):
        """
        Demande une valeur entière à l'utilisateur.

        Retourne None si l'utilisateur tape q, quit ou exit.
        """

        while True:
            value = input(message).strip()

            # Permet de quitter le programme
            if value.lower() in ["q", "quit", "exit"]:
                return None

            try:
                value = int(value)
            except ValueError:
                print("Entrer une valeur valide.")
                continue

            # Vérifie que la valeur est dans la plage autorisée
            if value < minimum or value > maximum:
                print(f"Entrer une valeur entre {minimum} et {maximum}.")
                continue

            return value

    def run(self):
        """
        Lance le mode interactif pour piloter les servos.
        """

        print("Pilotage de Servo")
        print("Taper q pour quitter.")
        print()

        while True:
            # Demande du canal servo
            channel = self.ask_int("Canal du Servo 0-2: ", 0, 2)

            if channel is None:
                break

            # Le servo de direction sur le canal 0 est limité entre 40° et 140°
            if channel == 0:
                angle = self.ask_int("Angle 40-140: ", 40, 140)
            else:
                angle = self.ask_int("Angle 0-180: ", 0, 180)

            if angle is None:
                break

            # Envoi de l'angle au servo
            self.set_angle(channel, angle)

            time.sleep(0.2)
            print()

    def close(self):
        """
        Libère proprement le module PCA9685.
        """

        self.pca.deinit()
        print("PCA9685 libéré.")


if __name__ == "__main__":
    controller = ServoController()

    try:
        controller.run()

    except KeyboardInterrupt:
        print("\nArrêté par l'utilisateur.")

    finally:
        controller.close()
