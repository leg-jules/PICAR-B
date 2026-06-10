#!/usr/bin/env python3
from pyclbr import Class
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor
import numpy as np

# motor_EN_A: Pin7 | motor_EN_B: Pin11
# motor_A: Pin8,Pin10 | motor_B: Pin13,Pin12
MOTOR_M1_IN1 = 15 #Define the positive pole of M1
MOTOR_M1_IN2 = 14 #Define the negative pole of M1

Dir_forward = 1
Dir_backward = -1

left_forward = 1
left_backward = 0

right_forward = 0
right_backward= 1

pwn_A = 0
pwm_B = 0

def map(x,in_min,in_max,out_min,out_max):
	return (x - in_min)/(in_max - in_min) *(out_max - out_min) + out_min

class Motor:
	def __init__(self):
			# Initialisation matérielle
			self.i2c = busio.I2C(SCL, SDA)
			self.pwm_motor = PCA9685(self.i2c, address=0x5f)
			self.pwm_motor.frequency = 1000
			
			self.motor1 = motor.DCMotor(self.pwm_motor.channels[MOTOR_M1_IN1], self.pwm_motor.channels[MOTOR_M1_IN2])
			self.motor1.decay_mode = motor.SLOW_DECAY 
			self.motors = [self.motor1]
			self.current_speed = [0]
			self.current_direction = [1]
			self.nb_motors = len(self.motors)


	def setSpeed(self, new_direction, new_speed, pente= 100, channel=1):
		# Sécurisation des limites de vitesse entre 0 et 100
		new_speed = max(0, min(new_speed, 100))
		self.transition(channel, new_speed, new_direction, pente)


	def transition(self, channel, target_speed, target_direction, pente):
		# Vérification de la validité du canal
		if self.checkMotor(channel-1):
			return
		
		v_current = self.current_speed[channel-1] * self.current_direction[channel-1]
		v_target = target_speed * target_direction
		
		# Calcul de la durée:
		diff_vitesse = abs(v_target - v_current)
		duree_totale = (diff_vitesse / 100.0) * (1.0 / pente)
		
		pas_temps = 0.01 # 10 millisecondes
		nb_steps = int(duree_totale / pas_temps)
		
		if nb_steps > 0:
			for i in range(1, nb_steps + 1):
				v_actuelle = v_current + (v_target - v_current) * (i / nb_steps)
				throttle = map(v_actuelle, -100, 100, -1.0, 1.0)
				self.motors[channel-1].throttle = max(-1.0, min(throttle, 1.0))
				time.sleep(pas_temps)

		# Valeur finale
		final_throttle = map(v_target, -100, 100, -1.0, 1.0)
		self.motors[channel-1].throttle = max(-1.0, min(final_throttle, 1.0))
		
		# Mise à jour de la vitesse et de la direction actuelles
		self.current_speed[channel-1] = target_speed
		self.current_direction[channel-1] = target_direction

	# Arrêt progressif du moteur
	def motorStop(self, channel=None, pente=1):
		if channel is None:
			for i in range(len(self.motors)):
				self.transition(i+1, 0, 1, pente)
		else:
			self.transition(channel, 0, 1, pente)

	# Récupération de la vitesse actuelle
	def getSpeed(self, channel = None):
		if channel is None:
			return self.current_speed
		else:
			# Vérification de la validité du canal
			if self.checkMotor(channel-1):
				return
			return self.current_speed[channel-1]
	
	# Récupération de la direction actuelle
	def getDirection(self, channel = None):
		if channel is None:
			return self.current_direction
		else:
			# Vérification de la validité du canal
			if self.checkMotor(channel-1):
				return
			return self.current_direction[channel-1]
	
	# Mise à jour de la vitesse et de la direction pour tous les moteurs
	def setAllSpeeds(self, new_direction, new_speed, pente=100):
		for i in range(len(self.motors)):
			self.setSpeed(new_direction, new_speed, pente, channel=i+1)
	

	# Arrêt brutal de tous les moteurs
	def destroy(self):
		self.motorStop(10)
		self.pwm_motor.deinit()
		self.i2c.deinit()
	
	def checkMotor(self, channel):
		return not (0 <= channel < self.nb_motors)
	
	def __del__(self):
		self.destroy()
	
	


if __name__ == '__main__':
	mot = None
	try:
		print("Initialisation du moteur...")
		mot = Motor()
		
		print("Accélération avant (50%) en 1 seconde...")
		mot.setSpeed(1, 50, pente=0.5, channel=1)
		time.sleep(2)
		
		print("Transition vers la marche arrière (50%) en 2 secondes...")
		mot.setSpeed(-1, 50, pente=0.5, channel=1)
		time.sleep(2)
		
		print("Vitesse actuelle lue :", mot.getSpeed(1))
		
		print("Arrêt progressif...")
		mot.motorStop(channel=1, pente=0.5)
		
	except KeyboardInterrupt:
		print("\nInterruption clavier détectée.")
	finally:
		if mot:
			print("Extinction du système et libération du bus I2C.")
			mot.destroy()


