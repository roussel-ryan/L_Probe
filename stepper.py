import serial
import logging
import time

class Stepper:
	def __init__(self,channel='COM4'):
		logging.info('Starting stepper controller')
		self.ser = serial.Serial(channel,9600,timeout = 600)
		
	def steps_to_mm(self,step):
		return step*(75.6/150000)

	def mm_to_steps(self,mm):
		return mm*(150000/75.6)

	def zero_location(self):
		self.mm_loc = 0.0
		self.step_loc = 0.0
		
	def go_to_displacement(self,disp): 
		logging.debug('Displacing by {:.2} mm'.format(disp)
		time.sleep(1.0)

		displacement_steps = disp*(150000.0/75.6)
		step_interval = 1500
		goal_step_loc = self.step_loc + displacement_steps
		
		end_condition = 'normal'

		while(not self.step_loc==goal_step_loc):
			if (abs(goal_step_loc - self.step_loc) < step_interval):
				self.ser.write(b'{i}'.format(goal_step_loc - self.step_loc))
				self.step_loc += goal_step_loc - self.step_loc
			elif (goal_step_loc - self.step_loc < 0):
				self.ser.write(b'{i}'.format(-step_interval))
				self.step_loc += -step_interval
			elif (goal_step_loc - self.step_loc > 0):
				self.ser.write(b'{i}'.format(step_interval))
				self.step_loc += step_interval
			if self.ser.inWaiting():
				msg = self.ser.read(self.ser.inWaiting())
				if 'p' in msg:
					end_condition = 'pos_limit'
					logging.info('Hit positive limit switch')
				elif 'n' in msg:
					end_condition = 'neg_limit'
					logging.info('Hit negitive limit switch')
				else:
					logging.error('Stepping blocked by unknown source, check arduino output: {}'.format(msg))
					end_condition = None
					
				break
			time.sleep(abs(self.steps_to_mm(step_interval))*4.5)

		self.mm_loc += disp
		
		return end_condition
		