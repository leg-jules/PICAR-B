#!/usr/bin/env python3

import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

# I2C setup
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

servos = {}

SERVO_OFFSETS = {
    0: 8,   # Offset pour le servo canal 0 qui gere la direction
}

def get_servo(channel):
    if channel not in servos:
        servos[channel] = servo.Servo(
            pca.channels[channel],
            min_pulse=500,
            max_pulse=2400,
            actuation_range=180
        )
    return servos[channel]

def set_angle(channel, angle):
    offset = SERVO_OFFSETS.get(channel, 0)

    corrected_angle = angle + offset

    # Bride de sécurité
    corrected_angle = max(0, min(180, corrected_angle))

    s = get_servo(channel)
    s.angle = corrected_angle

    print(f"Servo sur le canal {channel} demandé à {angle}° " f"-> envoyé à {corrected_angle}°")

def ask_int(message, minimum, maximum):
    while True:
        value = input(message).strip()

        if value.lower() in ["q", "quit", "exit"]:
            return None

        try:
            value = int(value)
        except ValueError:
            print("Entrer une valeur valide.")
            continue

        if value < minimum or value > maximum:
            print(f"Entrer une valeur entre {minimum} et {maximum}.")
            continue

        return value

try:
    print("Pilotage de Servo")
    print("Taper q pour quitter.")
    print()

    while True:
        channel = ask_int("Canal du Servo 0-2: ", 0, 2)
        if channel is None:
            break

        if channel == 0:
            angle = ask_int("Angle 40-140: ", 40, 140)
        else:
            angle = ask_int("Angle 0-180: ", 0, 180)

        if angle is None:
            break

        set_angle(channel, angle)
        time.sleep(0.2)
        print()

except KeyboardInterrupt:
    print("\nArrêté par l'utilisateur.")

finally:
    pca.deinit()
    print("PCA9685 libéré.")
