import serial
import logging
import time

class Stepper:
    def __init__(self,channel='COM4'):
        self.ser = serial.Serial(channel,9600,timeout = 10)
        self.zero_location()
        
    def steps_to_mm(self,step):
        return step*(75.6/150000)

    def mm_to_steps(self,mm):
        return mm*(150000/75.6)

    def zero_location(self):
        self.mm_loc = 0.0
        self.step_loc = 0.0
        
    def go_to(self,disp): 
        logging.debug('Displacing by {:.2} mm'.format(disp))
        time.sleep(1.0)

        displacement_steps = disp*(150000.0/75.6)
        step_interval = 1500
        goal_step_loc = self.step_loc + displacement_steps
        
        end_condition = 'normal'

        while(not self.step_loc==goal_step_loc):
            logging.debug('Looping ')
            if (abs(goal_step_loc - self.step_loc) < step_interval):
                self.ser.write(b'%i'%(goal_step_loc - self.step_loc))
                self.step_loc += goal_step_loc - self.step_loc
            elif (goal_step_loc - self.step_loc < 0):
                self.ser.write(b'%i'%-step_interval)
                self.step_loc += -step_interval
            elif (goal_step_loc - self.step_loc > 0):
                self.ser.write(b'%i'%step_interval)
                self.step_loc += step_interval
            
            msg = self.ser.readline()
            logging.debug('stepping status: {}'.format(msg))
            if 'pos_limit' in msg.decode():
                end_condition = 'pos_limit'
                logging.info('Hit positive limit switch')
                break
            elif 'neg_limit' in msg.decode():
                end_condition = 'neg_limit'
                logging.info('Hit negitive limit switch')
                break
            elif 'normal' in msg.decode():
                end_condition = 'normal'
            else:
                logging.error('Stepping blocked by unknown source, check arduino output: {}'.format(msg))
                end_condition = None
            
        if end_condition=='normal':
            self.mm_loc += disp
        
        return end_condition
        