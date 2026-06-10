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
	motors = []
	i2c = busio.I2C(SCL, SDA)
	pwm_motor = PCA9685(i2c, address=0x5f) #default 0x40
	channel = 1
	direction = 1
	motor_speed = 0
	speed = map(motor_speed, 0, 100, 0, 1.0)
	pwm_motor.frequency = 1000
	motor1 = motor.DCMotor(pwm_motor.channels[MOTOR_M1_IN1], pwm_motor.channels[MOTOR_M1_IN2])
	motor1.decay_mode = (motor.SLOW_DECAY)
	motors.append(motor1)


	def setSpeed(self, new_direction, new_motor_speed, pente= 100, channel=1):
		if new_motor_speed > 100:
			new_motor_speed = 100
		elif new_motor_speed < 0:
			new_motor_speed = 0

		self.transition(channel, new_motor_speed, new_direction, pente)

		Motor.speed = new_motor_speed


	def transition(self, channel, new_motor_speed, new_direction, pente):
		final_throttle = map(new_motor_speed, 0, 100, 0, 1.0)

		if (new_motor_speed * new_direction) < (Motor.motor_speed * Motor.direction):
			pente = -abs(pente)
		else:
			pente = abs(pente)
		i=0
		print("motor speed" + str(Motor.motor_speed* Motor.direction*100) + " nm:" + str(new_motor_speed * new_direction * 100))
		for cur_motor_speed in range((Motor.motor_speed * Motor.direction*100), (new_motor_speed * new_direction*100), pente):
			print("boucle")
			cur_throttle = map(cur_motor_speed, 0, 100*100, 0, 1.0)
			if new_direction == -1:
				cur_throttle = -cur_throttle
			Motor.motors[channel-1].throttle = cur_throttle
			time.sleep(0.01)
			print(i)
			i= i+1
		Motor.motors[channel-1].throttle = final_throttle
		print(pente)

		Motor.motor_speed = new_motor_speed
		Motor.speed = final_throttle * new_direction
		Motor.direction = new_direction

	#Motor stops
	def motorStop(self, channel=None):
		if channel is not None:
			Motor.motors[channel-1].throttle = 0
		else:
			for motor in Motor.motors:
				motor.throttle = 0


	def destroy(self):
		self.motorStop()
		self.pwm_motor.deinit()


if __name__ == '__main__':

	try:
		motor = Motor()
		chann = 1
		motor.setSpeed(1, 10, channel=chann, pente=1)
		time.sleep(2)
		motor.destroy()
	except KeyboardInterrupt:
		motor.destroy()



