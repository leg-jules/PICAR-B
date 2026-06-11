import time
import smbus
from pilotage_servo import ServoController
from tache9 import all
from motor2 import Motor
from distance_ultrasons import UltrasonicSensor
class ADS7830(object):
	def __init__(self):
		self.cmd = 0x84
		self.bus = smbus.SMBus(1)
		self.address = 0x48
		
	def analogRead(self, chn): 
		value = self.bus.read_byte_data(self.address, self.cmd | (((chn<<2 | chn>>1)&0x07)<<4))
		return value
	
	def analogtoangle(self, chn=1, value=None):
		if value is None:
			value = self.analogRead(chn)
			
		angle = ((255.0 - float(value)) / 255.0) * 180.0
		angle2 = int(max(40.0, min(140.0, angle)))
		return angle2 

if __name__ == "__main__":
	try:
		adc = ADS7830()
		controller = ServoController()
		motor_controller = Motor()
		motor_controller.setSpeed(1,10)
		setup()
		while True:
			# Simplification : analogtoangle s'occupe déjà de lire le canal 1 par défaut
			adc_angle = adc.analogtoangle(chn=1) 
			controller.set_angle(0, adc_angle)
			

			if obstacle_detected():
				print("Obstacle detected! Stopping motors.")
			"""
			
			else:
				# Paramètres corrects : direction=1 (avant), vitesse=20, pente=1, canal=1
				motor_controller.setSpeed(1, 20, pente=1.0, channel=1)
				
			
			"""
			motor_controller.update()
			# Indispensable pour éviter l'erreur I2C "Remote I/O error"
			time.sleep(0.02)
	except KeyboardInterrupt:
		print("\nInterruption clavier détectée.")