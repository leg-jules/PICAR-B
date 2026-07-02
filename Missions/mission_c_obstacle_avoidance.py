#!/usr/bin/env python3
"""Mission C - evitement d'obstacles pour l'Adeept PiCar-B.

Le robot reste dans la zone blanche grace aux trois capteurs infrarouges,
mesure la distance devant lui avec le HC-SR04 et balaie sept directions avec
la tete lorsqu'un obstacle bloque le passage.

Materiel utilise (Robot HAT V3.1 corrige) :
  - PCA9685 : adresse I2C 0x5f, frequence commune 50 Hz
  - moteur  : canaux PCA9685 15 et 14 (DRV8833)
  - direction : servo canal 0, correction mecanique +8 degres
  - tete/ultrason : servo canal 1
  - capteurs IR : gauche GPIO22, milieu GPIO27, droite GPIO17
  - ultrason : trigger GPIO23, echo GPIO24
"""

import signal
import statistics
import time

import busio
from adafruit_motor import motor, servo
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
from gpiozero import DistanceSensor, InputDevice


# ---------------------------------------------------------------------------
# Configuration a ajuster pendant les essais
# ---------------------------------------------------------------------------

PCA9685_ADDRESS = 0x5F
PCA9685_FREQUENCY = 50

MOTOR_IN1_CHANNEL = 15
MOTOR_IN2_CHANNEL = 14
STEERING_CHANNEL = 0
HEAD_CHANNEL = 1

IR_LEFT_PIN = 22
IR_MIDDLE_PIN = 27
IR_RIGHT_PIN = 17
# Sur ce robot : 0 = fond blanc et 1 = ligne noire.
# Mettre 0 uniquement si vos capteurs donnent les valeurs opposees.
IR_BLACK_VALUE = 1
ULTRASONIC_TRIGGER_PIN = 23
ULTRASONIC_ECHO_PIN = 24

FORWARD_SPEED = 0.22       # Commencer doucement : 0.15 a 0.25
REVERSE_SPEED = -0.20
CAUTION_SPEED = 0.16

OBSTACLE_DISTANCE_CM = 20.0
CAUTION_DISTANCE_CM = 35.0
EMERGENCY_DISTANCE_CM = 21.0
MIN_CLEAR_CORRIDOR_CM = 15.0

STEERING_CENTER = 90
# Sur le montage Adeept : angle > 90 = gauche, angle < 90 = droite.
STEERING_LEFT = 140
STEERING_RIGHT = 40
STEERING_OFFSET = 8        # Offset deja mesure sur le servo de direction
STEERING_MIN = 40
STEERING_MAX = 140

HEAD_CENTER = 90
HEAD_LEFT = 145
HEAD_RIGHT = 35
HEAD_OFFSET = 0
HEAD_MIN = 20
HEAD_MAX = 160
HEAD_SETTLE_TIME = 0.22

# Balayage de gauche vers la droite. Plusieurs rayons sont regroupes ensuite
# afin de ne pas confondre un petit espace libre avec un passage assez large
# pour toute la carrosserie.
HEAD_SCAN_ANGLES = (150, 130, 110, 90, 70, 50, 30)
HEAD_TO_STEERING_RATIO = 0.55

# Passer l'une de ces valeurs a True si le montage reagit a l'envers.
MOTOR_REVERSED = False
STEERING_REVERSED = False
HEAD_REVERSED = False

REVERSE_TIME = 0.45
BOUNDARY_TURN_TIME = 0.65
OBSTACLE_TURN_TIME = 0.90
LOOP_DELAY = 0.04
DISTANCE_READ_PERIOD = 0.20
DISTANCE_SAMPLES = 3


# ---------------------------------------------------------------------------
# Initialisation du materiel
# ---------------------------------------------------------------------------

i2c = None
pca = None
drive_motor = None
steering_servo = None
head_servo = None
distance_sensor = None
ir_left = None
ir_middle = None
ir_right = None
running = True


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def initialise_hardware():
    """Initialise une seule fois le PCA9685 et tous les capteurs."""
    global i2c, pca, drive_motor, steering_servo, head_servo
    global distance_sensor, ir_left, ir_middle, ir_right

    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c, address=PCA9685_ADDRESS)

    # Le moteur et les servos partagent le meme PCA9685. Une seule frequence
    # doit donc etre choisie. 50 Hz est indispensable pour les servos et reste
    # utilisable par le moteur DC via le DRV8833.
    pca.frequency = PCA9685_FREQUENCY

    drive_motor = motor.DCMotor(
        pca.channels[MOTOR_IN1_CHANNEL],
        pca.channels[MOTOR_IN2_CHANNEL],
    )
    # Meme mode que dans l'exemple moteur Adeept. Il donne une commande plus
    # stable a basse vitesse, utile pour les manoeuvres proches des limites.
    drive_motor.decay_mode = motor.SLOW_DECAY
    steering_servo = servo.Servo(
        pca.channels[STEERING_CHANNEL],
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
    )
    head_servo = servo.Servo(
        pca.channels[HEAD_CHANNEL],
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
    )

    distance_sensor = DistanceSensor(
        echo=ULTRASONIC_ECHO_PIN,
        trigger=ULTRASONIC_TRIGGER_PIN,
        max_distance=2.0,
        queue_len=5,
        partial=True,
    )

    # La sortie numerique des modules IR pilote deja la ligne. On ne force
    # donc ni pull-up ni pull-down. value=True correspond a un niveau haut.
    ir_left = InputDevice(IR_LEFT_PIN, pull_up=None, active_state=True)
    ir_middle = InputDevice(IR_MIDDLE_PIN, pull_up=None, active_state=True)
    ir_right = InputDevice(IR_RIGHT_PIN, pull_up=None, active_state=True)

    set_motor(0)
    set_steering(STEERING_CENTER)
    set_head(HEAD_CENTER)
    time.sleep(0.6)


# ---------------------------------------------------------------------------
# Commandes de base
# ---------------------------------------------------------------------------

def set_motor(throttle):
    """Commande le moteur entre -1.0 et +1.0."""
    throttle = clamp(throttle, -1.0, 1.0)
    if MOTOR_REVERSED:
        throttle = -throttle
    drive_motor.throttle = throttle


def set_steering(logical_angle):
    """Place la direction a un angle logique en appliquant son offset."""
    angle = 180 - logical_angle if STEERING_REVERSED else logical_angle
    angle = clamp(angle + STEERING_OFFSET, STEERING_MIN, STEERING_MAX)
    steering_servo.angle = angle


def set_head(logical_angle):
    """Oriente le capteur ultrason avec le servo de tete."""
    angle = 180 - logical_angle if HEAD_REVERSED else logical_angle
    angle = clamp(angle + HEAD_OFFSET, HEAD_MIN, HEAD_MAX)
    head_servo.angle = angle


def read_boundary_sensors():
    """Retourne True pour chaque capteur qui voit la ligne/noir.

    Le montage teste donne 0 sur le fond blanc et 1 sur la ligne noire.
    IR_BLACK_VALUE permet d'inverser facilement cette polarite si necessaire.
    """
    return (
        ir_left.value == IR_BLACK_VALUE,
        ir_middle.value == IR_BLACK_VALUE,
        ir_right.value == IR_BLACK_VALUE,
    )


def read_distance_cm(samples=DISTANCE_SAMPLES):
    """Retourne une distance filtree en centimetres."""
    readings = []
    for _ in range(samples):
        value = distance_sensor.distance * 100.0
        if 2.0 <= value <= 200.0:
            readings.append(value)
        time.sleep(0.025)

    # Une absence d'echo est interpretee comme un espace libre lointain.
    return statistics.median(readings) if readings else 200.0


def drive_for(throttle, steering_angle, duration):
    """Effectue une manoeuvre tout en surveillant les IR en marche avant."""
    set_steering(steering_angle)
    set_motor(throttle)
    end_time = time.monotonic() + duration

    while running and time.monotonic() < end_time:
        # Une manoeuvre avant est interrompue des qu'une limite est detectee.
        if throttle > 0 and any(read_boundary_sensors()):
            break
        time.sleep(LOOP_DELAY)

    set_motor(0)


# ---------------------------------------------------------------------------
# Comportements de la mission
# ---------------------------------------------------------------------------

def recover_from_boundary(left_black, middle_black, right_black):
    """Recule puis tourne vers l'interieur de la zone blanche."""
    set_motor(0)

    if left_black and not right_black:
        escape_angle = STEERING_RIGHT
        reason = "limite a gauche"
    elif right_black and not left_black:
        escape_angle = STEERING_LEFT
        reason = "limite a droite"
    else:
        # Milieu, deux ou trois capteurs : alterner evite une boucle bloquee.
        recover_from_boundary.prefer_left = not recover_from_boundary.prefer_left
        escape_angle = (
            STEERING_LEFT if recover_from_boundary.prefer_left
            else STEERING_RIGHT
        )
        reason = "limite devant"

    print(f"IR : {reason} -> recul et correction")
    # Reculer droit eloigne le train avant de la limite sans risquer de faire
    # pivoter un capteur encore davantage au-dessus de la ligne noire.
    drive_for(REVERSE_SPEED, STEERING_CENTER, REVERSE_TIME)
    drive_for(CAUTION_SPEED, escape_angle, BOUNDARY_TURN_TIME)
    set_steering(STEERING_CENTER)


recover_from_boundary.prefer_left = False


def scan_surroundings():
    """Mesure sept directions avec la tete pendant que le robot est arrete."""
    set_motor(0)
    measurements = []

    for angle in HEAD_SCAN_ANGLES:
        set_head(angle)
        time.sleep(HEAD_SETTLE_TIME)
        measurements.append((angle, read_distance_cm()))

    set_head(HEAD_CENTER)
    print(
        "Scan : "
        + " | ".join(
            f"{angle:3d}°={distance:3.0f}cm"
            for angle, distance in measurements
        )
    )
    return measurements


def choose_clear_corridor(measurements):
    """Retourne l'angle de tete situe au centre du passage le plus large.

    Le score utilise la plus petite distance parmi trois rayons voisins. Un
    rayon libre isole ne suffit donc pas a faire passer le robot.
    """
    candidates = []

    for index in range(1, len(measurements) - 1):
        neighborhood = measurements[index - 1:index + 2]
        corridor_clearance = min(distance for _, distance in neighborhood)
        center_angle, center_distance = measurements[index]

        # A degagement egal, favoriser le passage le plus proche du centre
        # afin d'eviter des changements de direction inutilement violents.
        score = corridor_clearance + center_distance * 0.15
        score -= abs(center_angle - HEAD_CENTER) * 0.03
        candidates.append((score, corridor_clearance, center_angle))

    return max(candidates)


def avoid_obstacle():
    """Choisit un passage assez large et adapte le braquage a sa direction."""
    measurements = scan_surroundings()

    # Ne jamais avancer dans une limite detectee pendant le balayage.
    boundary = read_boundary_sensors()
    if any(boundary):
        recover_from_boundary(*boundary)
        return

    _score, clearance, head_angle = choose_clear_corridor(measurements)

    # Aucun groupe de trois rayons n'est assez degage pour la carrosserie.
    if clearance < MIN_CLEAR_CORRIDOR_CM:
        print(
            f"Obstacle : aucun passage assez large ({clearance:.0f} cm) "
            "-> recul"
        )
        drive_for(REVERSE_SPEED, STEERING_CENTER, REVERSE_TIME + 0.25)
        return

    turn = STEERING_CENTER + (
        (head_angle - HEAD_CENTER) * HEAD_TO_STEERING_RATIO
    )
    turn = clamp(turn, STEERING_RIGHT, STEERING_LEFT)

    if head_angle > HEAD_CENTER:
        side = "gauche"
    elif head_angle < HEAD_CENTER:
        side = "droite"
    else:
        side = "centre"

    print(
        f"Obstacle : passage {side}, degagement {clearance:.0f} cm, "
        f"direction {turn:.0f}°"
    )
    drive_for(CAUTION_SPEED, turn, OBSTACLE_TURN_TIME)
    set_steering(STEERING_CENTER)


def stop_program(_signum=None, _frame=None):
    global running
    running = False


def cleanup():
    """Replace le robot au neutre et libere proprement le materiel."""
    print("\nArret et nettoyage...")
    try:
        if drive_motor is not None:
            drive_motor.throttle = 0
        if steering_servo is not None:
            set_steering(STEERING_CENTER)
        if head_servo is not None:
            set_head(HEAD_CENTER)
        time.sleep(0.2)
    finally:
        for device in (distance_sensor, ir_left, ir_middle, ir_right):
            if device is not None:
                try:
                    device.close()
                except Exception as error:
                    print(f"Nettoyage GPIO incomplet : {error}")
        if pca is not None:
            try:
                pca.deinit()
            except Exception as error:
                print(f"Nettoyage PCA9685 incomplet : {error}")


def run_mission():
    """Boucle principale priorisee : limite IR, urgence, obstacle, avance."""
    print("Mission C demarree - Ctrl+C pour arreter")
    last_distance_time = 0.0
    front_distance = 200.0

    while running:
        # Priorite absolue : ne pas quitter la zone blanche.
        boundary = read_boundary_sensors()
        if any(boundary):
            recover_from_boundary(*boundary)
            continue

        now = time.monotonic()
        if now - last_distance_time >= DISTANCE_READ_PERIOD:
            front_distance = read_distance_cm()
            last_distance_time = now

        if front_distance <= EMERGENCY_DISTANCE_CM:
            print(f"Urgence : obstacle a {front_distance:.1f} cm")
            set_motor(0)
            drive_for(REVERSE_SPEED, STEERING_CENTER, REVERSE_TIME)
            avoid_obstacle()
        elif front_distance <= OBSTACLE_DISTANCE_CM:
            print(f"Obstacle detecte a {front_distance:.1f} cm")
            avoid_obstacle()
        elif front_distance <= CAUTION_DISTANCE_CM:
            set_steering(STEERING_CENTER)
            set_motor(CAUTION_SPEED)
        else:
            set_steering(STEERING_CENTER)
            set_motor(FORWARD_SPEED)

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_program)
    signal.signal(signal.SIGTERM, stop_program)

    try:
        initialise_hardware()
        run_mission()
    finally:
        cleanup()
