#plasma data saver app

import tkinter as ttk
import logging
import serial
from struct import unpack
import time

import stepper
import scope
import numpy as np
import scipy.signal as signal

import visa
import pyvisa

class CopyPasteBox(ttk.Entry):
    def __init__(self, master, **kw):
        ttk.Entry.__init__(self, master, **kw)
        self.bind('<Control-c>', self.copy)
        self.bind('<Control-x>', self.cut)
        self.bind('<Control-v>', self.paste)
        
    def copy(self, event=None):
        self.clipboard_clear()
        text = self.get("sel.first", "sel.last")
        self.clipboard_append(text)
    
    def cut(self, event):
        self.copy()
        self.delete("sel.first", "sel.last")

    def paste(self, event):
        text = self.selection_get(selection='CLIPBOARD')
        #self.insert('insert', text)


class App():
    def __init__(self):
        logging.info('Starting application')
        
        self.root = ttk.Tk()
        
        self.manager = visa.ResourceManager()
        self.stepper_present = False 
        
        self.delay = 2000
        self.loc= 0.00
        self._update_count = 0

        self.save_state = False

        self.filename = ttk.StringVar()
        self.filename.set('test.txt')
        
        self.scan_interval = ttk.StringVar()
        self.scan_interval.set('20.0')
		
        self.scan_number = ttk.StringVar()
        self.scan_number.set('4')

        self.scan_samples = ttk.StringVar()
        self.scan_samples.set('10')

        self.manual_disp = ttk.StringVar()
        self.manual_disp.set('2.0')

        self.curr_location = ttk.StringVar()
        self.curr_location.set('Current Location: {:.2f}mm'.format(0.00))
        
        self.plasma_density = ttk.StringVar()
        self.plasma_density.set('0.00+/-0.00')
        self.plasma_temp = ttk.StringVar()
        self.plasma_temp.set('0.00+/-0.00')
        
        self.status = ttk.StringVar()
        self.status.set('Starting')

        self.ip_address = ttk.StringVar()
        self.ip_address.set('Scope IP Address: 0.0.0.0')
        
        self.stepper_connection = ttk.StringVar()
        self.stepper_connection.set('Stepper: Not Connected')
        
        self.scope_connection = ttk.StringVar()
        self.scope_connection.set('Scope: Not Connected')
        
        self.frame = ttk.Frame(self.root)
        self.frame.pack()
        
        status_label = ttk.Label(self.frame,textvariable = self.status)
        status_label.pack()
        
        scope_label = ttk.Label(self.frame,textvariable = self.scope_connection)
        scope_label.pack()
        
        ip_addresslabel = ttk.Label(self.frame,textvariable = self.ip_address)
        ip_addresslabel.pack()
        
        stepper_label = ttk.Label(self.frame,textvariable = self.stepper_connection)
        stepper_label.pack()
        
        file_entrylabel = ttk.Label(self.frame,text = 'Save to file: ')
        file_entrylabel.pack()
        file_entry = CopyPasteBox(self.frame,textvariable = self.filename)
        file_entry.pack()
        
        scan_lengthlabel = ttk.Label(self.frame,text = 'Distance to scan over (mm): ')
        scan_lengthlabel.pack()
        scan_length = CopyPasteBox(self.frame,textvariable = self.scan_interval)
        scan_length.pack()
		
        scan_pointslabel = ttk.Label(self.frame,text = 'Number of points to scan: ')
        scan_pointslabel.pack()
        scan_points = CopyPasteBox(self.frame,textvariable = self.scan_number)
        scan_points.pack()
		
        scan_samplelabel = ttk.Label(self.frame,text = 'Number of samples: ')
        scan_samplelabel.pack()
        scan_sample = CopyPasteBox(self.frame,textvariable = self.scan_samples)
        scan_sample.pack()

        manual_entrylabel = ttk.Label(self.frame,text = 'Manual displacement (+/- mm): ')
        manual_entrylabel.pack()
        manual_entry = CopyPasteBox(self.frame,textvariable = self.manual_disp)
        manual_entry.pack()

        location_label = ttk.Label(self.frame,textvariable = self.curr_location)
        location_label.pack()

        plasma_density_label = ttk.Label(self.frame,textvariable = self.plasma_density)
        plasma_density_label.pack()
        
        plasma_temp_label = ttk.Label(self.frame,textvariable = self.plasma_temp)
        plasma_temp_label.pack()
        
        savebutton = ttk.Button(self.frame,text = 'Save Data',command = self.save_data)
        savebutton.pack()

        scanbutton = ttk.Button(self.frame,text = 'Scan Plasma Chamber',command = self.scan)
        scanbutton.pack()

        displacebutton = ttk.Button(self.frame,text = 'Manually Displace',command = self.manual_displacement)
        displacebutton.pack()
        
        logging.info('Connecting to scope and stepper')
        self.init_stepper()
        self.continuous_update()
    
    def init_scope(self): 
        try: 
            self.scope = scope.Scope(self.delay)
            if self.scope.connection: 
                self.scope_connection.set('Scope: Connected')
            else: 
                logging.info('Scope connection failed')
                self.scope_connection.set('Scope: Not Connected')
            self.ip_address.set('Scope IP Address: {}'.format(self.scope.ip_address))
        except pyvisa.errors.VisaIOError:
            logging.info('Scope connection failed')
            self.status.set('Scope connection failed')
            self.scope_connection.set('Scope: Not Connected')
            self.ip_address.set('Scope IP Address: 0.0.0.0')

    def init_stepper(self): 
        try: 
            self.stepper = stepper.Stepper('COM4') 
            self.stepper_connection.set('Stepper: Connected')
        except serial.serialutil.SerialException:
            logging.info('Stepper connection failed')
            self.status.set('Failed to connect to stepper')
            self.stepper_connection.set('Stepper: Not Connected')
            
    def continuous_update(self): 
        self.init_scope()
        for instrument in self.manager.list_resources():
            if "ASRL" in instrument and self.stepper_connection.get()=='Stepper: Not Connected': 
                self.stepper.end_connection()
                self.init_stepper()
            elif (not "ASRL" in instrument):
                self.stepper_connection.set('Stepper: Not Connected')
        if self.scope_connection.get()=='Scope: Connected':
            self.update_plasma_params()
        self.root.after(self.delay,self.continuous_update)
            
    def update_plasma_params(self,data_append=''):
        logging.info('Updating')
        
        try:
            density_meas,temp_meas = self.scope.calculate_plasma_params(self.scope.read_scope())#[0.0,1.0],[2.0,3.0]
            self.plasma_density.set('{:.2e} +/- {:.2e}'.format(*density_meas))
            self.plasma_temp.set('{:.2e} +/- {:.2e}'.format(*temp_meas))

            if self.save_state:
                logging.info('Writing to file')
                self.status.set('Writing: On')
                with open(self.filename.get(),'a') as file:
                    file.write('{:.4e},{:.4e},{:.4e},{:.4e},{}\n'.format(*density_meas,*temp_meas,data_append))
            else:
                self.status.set('Writing: Off')
            self._update_count += 1
            
        except pyvisa.errors.VisaIOError:
            logging.info('Failed to read')

    def manual_displacement(self):
        if self.stepper_connection.get() == 'Stepper: Connected':
            self.status.set('Stepping')
            self.stepper.go_to(float(self.manual_disp.get()))
            self.curr_location.set('Current Location: {:.2f}mm'.format(self.stepper.mm_loc))
        else: 
            logging.info('Stepper not connected')
        
    def zero_stepper(self):
        if self.stepper_connection.get() == 'Stepper Connected':
            self.stepper.go_to(-1000000.0)
            self.stepper.zero_location()
        else: 
            logging.info('Stepper not connected')
        
    def scan(self):
        if self.stepper_connection.get() == 'Stepper Connected': 
            self.save_state = False
            logging.info('Zeroing probe')
            self.zero_stepper()
            self.stepper.go_to(41.0)
            
            points = int(self.scan_number.get())
            full_length = float(self.scan_interval.get())
            samples = int(self.scan_samples.get())
            scan_step_size = full_length / points
            
            logging.info('Doing scan with {} points,step size: {:.2}mm'.format(points,scan_step_size))
            for i in range(0,points):
                self.stepper.go_to(scan_step_size)
                logging.info('Current stepper position: {:.2} mm'.format(self.stepper.mm_loc))
                
                self.save_state = True
                for j in range(0,samples):
                    self.init_scope()
                    self.update_plasma_params(data_append = '{:.2}'.format(self.stepper.mm_loc))
                    self.root.after(self.delay,self.wait())
                self.save_state = False
            logging.info('Done with scan, zeroing')
            self.zero_stepper()
        else:
            logging.info('Stepper not connected')
        
    def wait(self): 
        pass
	
    def save_data(self):
        self.save_state = not self.save_state
        
    def destroy(self):
        self.root.destroy()

def main():
    logging.basicConfig(level=logging.INFO)
    
    try:
        
        app = App()
        
        app.root.mainloop()
    except Exception as e:
        logging.exception(e)
    finally:
        app.root.destroy()
    
if __name__=='__main__':
    main()