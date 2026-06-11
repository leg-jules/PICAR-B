import time
from gpiozero import InputDevice

line_pin_left = 22
line_pin_middle = 27 # Definition des GPIO utilises par les trois capteurs de ligne
line_pin_right = 17

left = InputDevice(pin=line_pin_left)
middle = InputDevice(pin=line_pin_middle) # Creation des objets correspondant aux capteurs
right = InputDevice(pin=line_pin_right)

def run():
    status_left = left.value
    status_middle = middle.value # lecture de l'etat de chaque capteur
    status_right = right.value

    print(
        'left: %d   middle: %d   right: %d'
        % (status_left, status_middle, status_right) # affiche si le capteur reconnait une ligne 
    )

if __name__ == '__main__': 
    try:
        while True: # boucle infini de lecture
            run()
            time.sleep(0.3)# latence entre capatation
    except KeyboardInterrupt:
        pass
