import time
import sys
import select

import RPi.GPIO as GPIO

from motor2 import Motor, Dir_forward
from distance_ultrasons import UltrasonicSensor
import led_control
from WS2812_LED1 import LED

############################################################################
# PARAMETRES GENERAUX
############################################################################

OBSTACLE_LIMIT_MM = 200  #20 cm = 200 mn (à modifier plus tard*)
MOTOR_SPEED = 30         #vitesse réduite pour test
ACCELERATION_PENTE = 2   #Pente d'accélération *
DECELERATION_PENTE = 2   #Pente de décélération *
MOTOR_CHANNEL = 1

HAZARD_BLINK_DELAY = 0.4 #Temps entre clignotement des feux


############################################################################
# VARIABLES GLOBALES
############################################################################

#Initialize variable to false or none

robot_running = False
hazard_active = False
hazard_state = False
last_hazard_blink = 0

motor_controller = None
ws_led = None
ultrasonic_sensor = None

############################################################################
# COMMANDES CLAVIER
############################################################################

def read_keyboard_command():
    """
    Lecture du clavier
    Continue a vérifier les obstacles meme sans action de l'utilisateur
    ne tape rien.

    L'utilisateur doit quand même démarrer le robot
    """

    if select.select([sys.stdin], [], [], 0)[0]:
        command = sys.stdin.readline().strip()
        return command
    
    return None


############################################################################
# MOTEUR
############################################################################

#Demarre le robot en marche avant

def start_robot():

    global robot_running

    print("Démarrage du robot en marche avant.")

    motor_controller.setSpeed(
        Dir_forward,
        MOTOR_SPEED,
        pente=ACCELERATION_PENTE,
        channel=MOTOR_CHANNEL
    )

    robot_running = True


#Arrêt progressif du robot
def stop_robot_smooth():

    global robot_running

    print("Arrêt progressif du robot.")

    try:
        motor_controller.setSpeed(
            Dir_forward,
            0,
            pente=DECELERATION_PENTE,
            channel=MOTOR_CHANNEL
        )
    except Exception as error:
        print("Erreur pendant l'arrêt progressif :", error)
        print("Arrêt immédiat par sécurité.")
        motor_controller.motorStop(MOTOR_CHANNEL)

    robot_running = False

def stop_robot_immediate():
    """
    Arrêt immédiat du robot.
    Utilisé pour la commande du A
    """
    global robot_running

    print("Arrêt immédiat du robot")

    motor_controller.motorStop(MOTOR_CHANNEL)
    robot_running = False

############################################################################
# CAPTEUR ULTRASON
############################################################################

def obstacle_detected():

    try:
        distance = ultrasonic_sensor.get_distance_mm()
        print(f"Distance : {distance:.2f} mm")

        if distance < OBSTACLE_LIMIT_MM:
            return True
        
        return False
    
    except Exception as error:
        print("Erreur lecture capteur ultrason :", error)
        return False
    

############################################################################
# FEUX DE DETRESSE
############################################################################
    
def hazard_lights_on_step():
    """
    Etape de clignotement des feux de détresse
    Ne nécéssite pas de thread car il ne bloque pas le programme
    """
    global hazard_state, last_hazard_blink

    current_time = time.time()

    if current_time - last_hazard_blink < HAZARD_BLINK_DELAY:
        return
    
    last_hazard_blink = current_time
    hazard_state = not hazard_state

    if hazard_state:
        #HAT LEDs
        led_control.switch_hat_led(11, 1)
        led_control.switch_hat_led(12, 1)
        led_control.switch_hat_led(13, 1)

        # LED RGB avant gauche et droite en rouge
        led_control.switch_rgb_led(14, 1)  # left_R
        led_control.switch_rgb_led(15, 0)  # left_G
        led_control.switch_rgb_led(16, 0)  # left_B

        led_control.switch_rgb_led(17, 1)  # right_R
        led_control.switch_rgb_led(18, 0)  # right_G
        led_control.switch_rgb_led(19, 0)  # right_B

        # WS2812 en rouge
        ws_led.colorWipe(255, 0, 0)

    else:
        led_control.set_all_switch_off()
        ws_led.colorWipe(0, 0, 0)

#Active le mode feux de détresse
def start_hazard_lights():
    global hazard_active, hazard_state, last_hazard_blink

    print("Obstacle détecté : activation des feux de détresse.")

    hazard_active = True
    hazard_state = False

    led_control.set_all_switch_off()
    ws_led.colorWipe(0, 0, 0)

#Désactive les feux de détresse
def stop_hazard_lights():
    global hazard_active, hazard_state

    hazard_active = False
    hazard_state = False

    led_control.set_all_switch_off()
    ws_led.colorWipe(0, 0, 0)

############################################################################
# INITIALISATION ET NETTOYAGE
############################################################################

def setup():
    """
    Initialise le moteur, le capteur ultrason, les LED GPIO et les LED WS2812.
    """

    global motor_controller, ws_led, ultrasonic_sensor

    print("Initialisation du robot...")

    motor_controller = Motor()

    ultrasonic_sensor = UltrasonicSensor (
        trigger_pin=23,
        echo_pin=24,
        max_distance=2
    )

    led_control.switchSetup()

    ws_led = LED()
    ws_led.colorWipe(0, 0, 0)

    print("Initialisation terminée.")
    print()
    print("Commandes disponibles :")
    print("M  : marche avant")
    print("A  : arrêt immédiat")
    print("a  : arrêt immédiat")
    print("CTRL+C : quitter le programme")
    print()

#Nettoyage final du robot
def cleanup():

    try:
        if motor_controller is not None:
            motor_controller.motorStop(MOTOR_CHANNEL)
            motor_controller.destroy()
    except Exception as error:
        print("Erreur nettoyage moteur:", error)

    try:
        if ultrasonic_sensor is not None:
            ultrasonic_sensor.close()
    except Exception as error:
        print("Erreur nettoyage capteur ultrason :", error)

    try:
        if ws_led is not None:
            ws_led.colorWipe(0, 0, 0)
    except Exception as error:
        print("Erreur extinction WS2812 :", error)

    try:
        led_control.set_all_switch_off()
    except Exception as error:
        print("Erreur extinction LED GPIO :", error)

    try:
        GPIO.cleanup()
    except Exception as error:
        print("Erreur GPIO cleanup :", error)

    print("Nettoyage final réalisé.")  

############################################################################
# PROGRAMME PRINCIPALE
############################################################################

def main():
    global robot_running
    setup()

    try:
        while True:

            command = read_keyboard_command()

            if command is not None:
                if command == "M":
                    print("Commande reçue : M")

                    stop_hazard_lights()
                    start_robot()

                elif command == "A" or command == "a":
                    print("Commande reçue : arrêt manuel")

                    stop_robot_immediate()
                    stop_hazard_lights()

                elif command != "":
                    print("Commande inconnue :", command)
                    print("Commandes valides : M, A, a")


            if robot_running:
                if obstacle_detected():
                    stop_robot_smooth()
                    start_hazard_lights()


            if hazard_active:
                hazard_lights_on_step()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print()
        print("Fin de programme par Ctrl+C.")

    finally:
        cleanup()


if __name__ == "__main__":
    main()