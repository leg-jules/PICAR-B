from gpiozero import DistanceSensor
from time import sleep

Tr = 23
Ec = 24
sensor = DistanceSensor(echo=Ec, trigger=Tr,max_distance=2) # Distance de detection maximum 2m.

def checkdist():
    return (sensor.distance) *100 # Unité: cm

if __name__ == "__main__":
    while True:
        distance = checkdist() 
        print("%.2f cm" %distance)
        sleep(0.05)
