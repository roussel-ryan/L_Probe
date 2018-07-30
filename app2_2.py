#plasma data saver app

import tkinter as ttk
import logging
import os
import serial
from struct import unpack
import time

import stepper
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
        
        self.delay = 2000
        self.loc= 0.00
        self._update_count = 0

        self.save_plasma_params = False
        self.save_raw = False

        self.plasma_params_filename = ttk.StringVar()
        self.plasma_params_filename.set('test.txt')
        
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
       
        saveparamsbutton = ttk.Button(self.frame,text = 'Save Plasma Params',command = self.flip_save_plasma_params)
        saveparamsbutton.pack()
        
        saveshotsbutton = ttk.Button(self.frame,text = 'Save Shots',command = self.save_shots)
        saveshotsbutton.pack()
        
        scanbutton = ttk.Button(self.frame,text = 'Scan Plasma Chamber',command = self.scan)
        scanbutton.pack()
        

        displacebutton = ttk.Button(self.frame,text = 'Manually Displace',command = self.manual_displacement)
        displacebutton.pack()
        
        #self.init_scope()
        #self.stepper = stepper.Stepper('COM4')
        #self.continuous_update()

    def init_scope(self):
        self.manager = visa.ResourceManager()
        try: 
            self.scope = self.manager.open_resource('TCPIP::169.254.80.255::INSTR')
        except pyvisa.errors.VisaIOError: 
            self.scope = self.manager.open_resource('TCPIP::169.254.4.83::INSTR')
        self.scope.timeout = self.delay
    
    def read_scope(self):
        data=[]
        for i in ['1','2','3','4']:
            self.scope.write('DATA:SOU CH%s'%i)
            self.scope.write('DATA:WIDTH 1')
            self.scope.write('DATA:ENC RPB')
            if i=='1':
                xincr=float(self.scope.ask('WFMPRE:XINCR?'))
            y_mult=float(self.scope.ask('WFMPRE:YMULT?'))
            y_zero=float(self.scope.ask('WFMPRE:YZERO?'))
            y_offset=float(self.scope.ask('WFMPRE:YOFF?'))
            self.scope.write('CURVE?')
            curdata=self.scope.read_raw()

            headerlen=2+int(curdata[1])
            header=curdata[:headerlen]
            ADC_Wave=curdata[headerlen:-1]
            ADC_Wave=np.array(unpack('%sB'%len(ADC_Wave),ADC_Wave))
            if i=='1':
                data.append(np.arange(0,xincr*len(ADC_Wave)/10,xincr/10))
            data.append((ADC_Wave-y_offset)*y_mult+y_zero)
        return np.asfarray(data)
    
    def calculate_plasma_params(self,data,ax2=''):
        A = 0.66 #mm^2 (probe cross section area#
        M = 40 #effective ion weight
        V_bias = 60
        
        filter_params = [3,0.05]
        
        b,a = signal.butter(filter_params[0],filter_params[1],output='ba')
        
        t = data[0]*1e6
        CH1 = signal.filtfilt(b,a,data[1])
        CH2 = signal.filtfilt(b,a,data[2])
        CH3 = signal.filtfilt(b,a,data[3])
        CH4 = signal.filtfilt(b,a,data[4])
        
        #if plotting:
            #ax.plot(t,CH1,label='Trigger')
            #ax.plot(t,CH2,label='+')
            #ax.plot(t,CH3,label='-')
            #ax.plot(t,CH4,label='F')

            #ax.legend()

            
        V_d2 = CH2 - CH4
        T = self.T_e(V_d2,V_bias)
        
        V_d3 = 10**(((CH3 - CH2)-2.65)/0.95)
        R = 1.1
        I_3 = V_d3/R
            
        density = (M**0.5 / A) * I_3*1e6*self.f1(V_d2,T)
        
            
        #get sample range from trigger
        t_trig = t[np.where(CH1 > 1)]
        t_i = np.min(t_trig)
        t_f = np.max(t_trig)
        sample_length = t_f - t_i
            
        sample_range = (t_i + 0.4*sample_length,t_f - 0.1*sample_length)
            
        avg_density = np.mean(density[np.where((t > sample_range[0]) & (t < sample_range[1]))])
        std_density = np.std(density[np.where((t > sample_range[0]) & (t < sample_range[1]))])
        
        avg_temp = np.mean(T[np.where((t > sample_range[0]) & (t < sample_range[1]))])
        std_temp = np.std(T[np.where((t > sample_range[0]) & (t < sample_range[1]))])
            
        if ax2: 
            p1, = ax2.plot(t,T,label='Electron Temp. ${:.2}\pm{:.2}$ eV'.format(avg_temp,std_temp))
            p3, = ax2.plot(t,CH1,label='Trigger')
            ax2.set_ylabel('Electron Temperature (eV)')
            ax2.set_xlabel('Time ($\mu s)$')
            ax2.set_xlim(sample_range[0],sample_range[1])
            
            ax4 = ax2.twinx()
            ax4.set_ylabel('Plasma Density ($cm^{-3}$)')
            p2, = ax4.semilogy(t,density,'r',label='Plasma Density ${:.2}\pm{:.2}$ $1/cm^3$'.format(avg_density,std_density))

            ax2.legend(handles=[p1,p2,p3])
        return [avg_density,std_density],[avg_temp,std_temp]    
    
    def update_plasma_params(self,filename,density_meas='',temp_meas='',data_append=''):
        logging.info('Updating')
        if density_meas == '' or temp_meas == '':
            density_meas,temp_meas = self.calculate_plasma_params(self.read_scope())#[0.0,1.0],[2.0,3.0]
        
        self.plasma_density.set('{:.2e} +/- {:.2e}'.format(*density_meas))
        self.plasma_temp.set('{:.2e} +/- {:.2e}'.format(*temp_meas))
        
        if self.save_plasma_params:
            logging.info('Writing to file')
            self.status.set('Writing: On')
            with open(self.filename,'a') as file:
                file.write('{:.4e},{:.4e},{:.4e},{:.4e},{}\n'.format(*density_meas,*temp_meas,data_append))
        else:
            self.status.set('Writing: Off')
        self._update_count += 1
    
    def save_shots(self):
        logging.info('Saving shots')
        self.save_plasma_params = True
        
        foldername = 'data/{}'.format(time.strftime('%m_%d_%Y',time.gmtime()))
        
        #search for a folder of a name and create it if the name is not found
        for i in range(10000):
            fullpth = '{}_{}'.format(foldername,i)
            if not os.path.isdir(fullpth):
                os.makedirs(fullpth)
                break
                
        #save raw data and plasma params for each shot
        for i in range(int(self.scan_samples)):
            data = self.read_scope()
            density,temp = self.calculate_plasma_params(data)
            self.update_plasma_params('{}/plasma_params.txt'.format(fullpth),density_meas = density,temp_meas = temp)
            np.savetxt('{}/data_{}.txt'.format(fullpth,i),data.T)
            time.sleep(self.delay/1000)
            
            
    def f1(self,V_d2,T_e):
        return 1.05e9 * (T_e)**(-0.5) / (np.exp(V_d2/T_e) - 1)
    
    def T_e(self,V_d2,V_d3):
        return V_d2/np.log(2)
        #return V_d2 / (np.log(2)*(1+np.exp(-0.2567*(V_d3/V_d2)**2))*(1-np.exp(0.9968*(2-V_d3/V_d2))))

    def continuous_update(self): 
        self.update_plasma_params(self.plasma_params_filename.get())
        self.root.after(self.delay,self.continuous_update)

    def manual_displacement(self):
        self.status.set('Stepping')
        self.stepper.go_to(float(self.manual_disp.get()))
        self.curr_location.set('Current Location: {:.2f}mm'.format(self.stepper.mm_loc))
    
    def zero_stepper(self):
        self.stepper.go_to(-1000000.0)
        self.stepper.zero_location()
        
    def scan(self):
        self.save_plasma_params = False
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
            
            self.save_plasma_params = True
            for j in range(0,samples):
                self.update_plasma_params(self.plasma_params_filename.get(),data_append = '{:.2}'.format(self.stepper.mm_loc))
                self.root.after(self.delay,self.wait())
            self.save_plasma_params = False
        logging.info('Done with scan, zeroing')
        self.zero_stepper()
        
    def wait(self): 
        pass
    
    def flip_save_plasma_params(self):
        self.save_plasma_params = not self.save_plasma_params
        
    def flip_save_raw(self):
        self.save_raw = not self.save_raw
        
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
        App().root.destroy()
    
if __name__=='__main__':
    main()
