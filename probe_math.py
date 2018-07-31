#plasma calculations
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt

def calculate_plasma_params(self,data,ax=''):
    A = 0.66 #mm^2 (probe cross section area
    M = 40 #effective ion weight
    V_bias = 60
    
    filter_params = [3,0.05]
    
    b,a = signal.butter(filter_params[0],filter_params[1],output='ba')
    
    if not len(data) == 5:
        raise IndexError
    
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
    #channel convention
    #CH1: F,CH2:trigger/current measurement,CH3:+,CH4:-
                
    V_d2 = CH3 - CH1
    T = self.T_e(V_d2,V_bias)
    
    V_d3 = 10**(((CH2 - CH3)-2.65)/0.95)
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

def f1(self,V_d2,T_e):
    return 1.05e9 * (T_e)**(-0.5) / (np.exp(V_d2/T_e) - 1)
        
    
def T_e(self,V_d2,V_d3):
    return V_d2/np.log(2)