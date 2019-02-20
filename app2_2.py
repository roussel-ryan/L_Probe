#plasma data saver app

import tkinter as ttk
import logging
import os
import serial
from struct import unpack
import time

import stepper
import probe_math as pmath
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
        
        self.delay = 1000
        self.timeout = 1000
        self.rep_rate = 0.5
        self.loc= 0.00
        self._update_count = 0

        self.measure_plasma_params = False
        self.save_plasma_params = False
        self.save_raw = False

        self.plasma_params_filename = ttk.StringVar()
        self.plasma_params_filename.set('test.txt')
        
        self.raw_data_folder = ttk.StringVar()
        self.raw_data_folder.set('data/')
        
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
        
        self.frame = ttk.Frame(self.root)
        self.frame.pack()
        
        status_label = ttk.Label(self.frame,textvariable = self.status)
        status_label.pack()
        
        file_entrylabel = ttk.Label(self.frame,text = 'Save to file: ')
        file_entrylabel.pack()
        file_entry = CopyPasteBox(self.frame,textvariable = self.plasma_params_filename)
        file_entry.pack()
        
        raw_folder_entrylabel = ttk.Label(self.frame,text = 'Raw data folder: ')
        raw_folder_entrylabel.pack()
        raw_folder_entry = CopyPasteBox(self.frame,textvariable = self.raw_data_folder)
        raw_folder_entry.pack()
        
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

        #plasma_density_label = ttk.Label(self.frame,textvariable = self.plasma_density)
        #plasma_density_label.pack()
        
        #plasma_temp_label = ttk.Label(self.frame,textvariable = self.plasma_temp)
        #plasma_temp_label.pack()
       
        #saveparamsbutton = ttk.Button(self.frame,text = 'Measure Plasma Params',command = self.flip_measure_plasma_params)
        #saveparamsbutton.pack()
       
        #saveparamsbutton = ttk.Button(self.frame,text = 'Save Plasma Params',command = self.flip_save_plasma_params)
        #saveparamsbutton.pack()
        
        self.saveshotsbutton = ttk.Button(self.frame,text = 'Save Shots',command = self.save_shots)
        self.saveshotsbutton.pack()
        
        self.scanbutton = ttk.Button(self.frame,text = 'Scan Plasma Chamber',command = self.scan)
        self.scanbutton.pack()
        
        displacebutton = ttk.Button(self.frame,text = 'Manually Displace',command = self.manual_displacement)
        displacebutton.pack()
        
        zerobutton = ttk.Button(self.frame,text = 'Zero',command = self.zero_stepper)
        zerobutton.pack()
        
        self.init_scope()
        self.stepper = stepper.Stepper('COM4')
        self.continuous_update()

    def init_scope(self):
        self.manager = visa.ResourceManager()
        try: 
            self.scope = self.manager.open_resource('GPIB1::1::INSTR')
        except pyvisa.errors.VisaIOError: 
            try:
                self.scope = self.manager.open_resource('TCPIP::169.254.4.83::INSTR')
            except pyvis.errors.VisaIOError:
                logging.warning('Scope not connected - data taking disabled')
                self.scanbutton.configure(state=DISABLE)
                self.saveshotbutton.configure(state=DISABLE)
                
                
    def read_scope(self):
        logging.info('Reading scope')
        self.scope.write('DATA:SOURCE CH1,CH2,CH3,CH4')
        self.scope.write('DATA:ENCDG ASCII')
        self.scope.write('DATA:WID 1')

        nsettings = 10
        self.preambles = self.scope.query('WFMPR?').strip().split(';')
        logging.debug(len(self.preambles))
            
        self.channel_settings = []
        for j in range(4):
            self.channel_settings.append(self.preambles[5+j*nsettings:5+(j+1)*nsettings])

        npts = int(self.channel_settings[0][-9])
        curv = self.scope.query_ascii_values('CURV?',container=list,separator=',')

        data = []
        for i in range(4):
            data.append(np.asfarray(curv[i*npts:(i+1)*npts]))
        
        ch_data = [np.linspace(0.0,len(data[0])*float(self.channel_settings[0][-6]),len(data[0]))]
    
        for ch,setting in zip(data,self.channel_settings):
            logging.debug(setting)
            ydata = (ch - float(setting[-2])) * float(setting[-3]) + float(setting[-1])
            ch_data.append(ydata)
        return np.asfarray(ch_data)
    
    def update_plasma_params(self,data):
        density,temp = pmath.calculate_plasma_params(data)#[0.0,1.0],[2.0,3.0]
        
        self.plasma_density.set('{:.2e} +/- {:.2e}'.format(*density_meas))
        self.plasma_temp.set('{:.2e} +/- {:.2e}'.format(*temp_meas))
     
        self._update_count += 1
    
    def save_plasma_params_to_file(self,data,filename,data_append=''):
        density,temp = pmath.calculate_plasma_params(data)#[0.0,1.0],[2.0,3.0]        
    
        logging.info('Writing to file')
        self.status.set('Writing: On')
        with open(filename,'a') as file:
            file.write('{:.4e},{:.4e},{:.4e},{:.4e},{}\n'.format(*density,*temp,data_append))
    
    def save_shots(self):
        logging.info('Saving shots')        
        foldername = '{}{}'.format(self.raw_data_folder.get(),time.strftime('%m_%d_%Y',time.gmtime()))
        
        #search for a folder of a with the date and create it if the name is not found
        if not os.path.isdir(foldername):
            logging.info('Making folder {}'.format(foldername))
            os.makedirs(foldername)
               
        #make a raw directory if one is not found
        raw_foldername = '{}/raw'.format(foldername)
        if not os.path.isdir(raw_foldername):
            logging.info('Making folder {}'.format(raw_foldername))
            os.makedirs(raw_foldername)
        
        #make a folder for the particular index number
        for i in range(10000):
            fullpth = '{}/{}'.format(raw_foldername,i)
            if not os.path.isdir(fullpth):
                os.makedirs(fullpth)
                break
        logging.info('Index {}'.format(i))
        
        
        for j in range(int(self.scan_samples.get())):
            data = self.read_scope()
            np.savetxt('{}/data_{}.txt'.format(fullpth,j),data.T)
            time.sleep(1.25*(1 / self.rep_rate))
            
        logging.info('done saving shots')
      
    def continuous_update(self): 
        if self.measure_plasma_params:
            data = self.read_scope()
            self.update_plasma_params(data)
            if self.save_plasma_params():
                self.save_plasma_params_to_file(data,self.plasma_params_filename)
        else:
            if self.save_plasma_params:
                self.measure_plasma_params = True
        self.root.after(self.delay,self.continuous_update)

    def manual_displacement(self):
        self.status.set('Stepping')
        self.stepper.go_to(float(self.manual_disp.get()))
        self.curr_location.set('Current Location: {:.2f}mm'.format(self.stepper.mm_loc))
    
    def zero_stepper(self):
        self.stepper.go_to(-1000000.0)
        self.stepper.zero_location()
        self.curr_location.set('Current Location: {:.2f}mm'.format(0.0))
        
    def scan(self):
        logging.info('Zeroing probe')
        foldername = '{}{}'.format(self.raw_data_folder.get(),time.strftime('%m_%d_%Y',time.gmtime()))
        
        #search for a folder of a name and create it if the name is not found
        
        if not os.path.isdir('{}/scans'.format(foldername)):
            os.makedirs('{}/scans'.format(foldername))
        
        for i in range(10000):
            fullpth = '{}/scans/scan_{}'.format(foldername,i)
            if not os.path.isdir(fullpth):
                os.makedirs(fullpth)
                break
        logging.info('Scan index {}'.format(i))
        
        start = self.stepper.mm_loc

        logging.info('Start positition {}mm'.format(start))
        
        points = int(self.scan_number.get())
        full_length = float(self.scan_interval.get())
        samples = int(self.scan_samples.get())
        scan_step_size = full_length / points
        
        logging.info('Doing scan with {} points,step size: {:.2}mm'.format(points,scan_step_size))
        for i in range(0,points):
            logging.info('stepping')
            self.stepper.go_to(scan_step_size)
            logging.info('Current stepper position: {:.2} mm'.format(self.stepper.mm_loc))
            
            #save raw data for each shot
            for j in range(int(self.scan_samples.get())):
                data = self.read_scope()
                np.savetxt('{}/data_{}mm_{}.txt'.format(fullpth,self.stepper.mm_loc,j),data.T)
                time.sleep(self.delay/1500)
        logging.info('Done with scan,going to orig location')
        self.stepper.go_to(-full_length)
        logging.info('Ready')
    def wait(self): 
        pass
    
    def flip_measure_plasma_params(self):
        self.measure_plasma_params = not self.measure_plasma_params
    
    def flip_save_plasma_params(self):
        self.save_plasma_params = not self.save_plasma_params
        
    def flip_save_raw(self):
        self.save_raw = not self.save_raw
        
    def destroy(self):
        self.root.destroy()

def main():
    logging.basicConfig(level=logging.INFO)
    app = App()
    app.root.mainloop()
    #try:
        
    #    app = App()
        
    #    app.root.mainloop()
    #except Exception as e:
     #   logging.exception(e.args)
    #finally:
    #    pass
    #    app.destroy()
    
if __name__=='__main__':
    main()
