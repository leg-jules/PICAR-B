from gpiozero import DistanceSensor
from time import sleep

Tr = 23
Ec = 24
sensor = DistanceSensor(echo=Ec, trigger=Tr,max_distance=2) # Distance de detection maximum 2m.

def checkdist():
    return (sensor.distance) *1000 # Unité: mm

if __name__ == "__main__":
    while True:
        distance = checkdist() 
        print("%.2f mm" %distance)
        sleep(0.05)
