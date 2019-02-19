import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import probe_math as pmath
from scipy.ndimage import filters
import logging

def calc_plasma_prop(fname,plotting=False):
    data = np.loadtxt(fname).T
    
    t = data[0]
    F = data[1]
    current = -1*100*data[2]
    high = data[3]
    low = data[4]

    #get t range where we want to calculate properties
    buffer_size = 0.15
    indicies = np.argwhere(current > 40).flatten()
    l = len(indicies)
    indicies = indicies[int(l*buffer_size):-int(l*buffer_size)]

    mask_array = np.ones(len(t))
    mask_array[indicies] = 0
    
    
    signals = [t,F,high,low,current]
    msignals = []
    for signal in signals:
        msignals.append(ma.array(signal,mask=mask_array))
        
    shunt_current = (msignals[2]-msignals[3])/98
    
    A = 0.66 #mm^2 (probe cross section area
    M = 40 #effective ion weight
    V_bias = 100
        
    T = pmath.T_e(msignals[2]-msignals[1],V_bias)    
    density = (M**0.5 / A) * shunt_current*1e6*pmath.f1(msignals[2]-msignals[1],T)


    if plotting:
        fig,ax = plt.subplots()
        
        labels = ['t','F','high','low','current']
        for i in range(1,4):
            ax.plot(msignals[0],msignals[i],label=labels[i])

        axa = ax.twinx()
        axa.plot(t,current)    
#        axa.plot(mask_array*100)
        ax.legend()
        
        fig2,ax2 = plt.subplots()
        ax2.plot(t,T,'g')
        ax3 = ax2.twinx()
        ax3.semilogy(t,density)

    return (np.mean(T),np.std(T),np.mean(density),np.std(density))


def time_scan(base):
    fig,ax = plt.subplots(2,1,sharex=True)
    
    tdata = []
    for i in range(30):
        tdata.append((i,*calc_plasma_prop(base.format(i))))
    ntdata = np.asfarray(tdata).T
    logging.info(ntdata)
    ax[0].errorbar(ntdata[0],ntdata[3],ntdata[4],fmt='o',capsize = 3)
    ax[1].errorbar(ntdata[0],ntdata[1],ntdata[2],fmt='o',capsize = 3)

    avg_dens = np.mean(ntdata[3])
    std_dens = np.std(ntdata[3])

    avg_temp = np.mean(ntdata[1])
    std_temp = np.std(ntdata[1])
    
    ax[0].axhline(avg_dens,ls='-')
    for i in [-1,1]: ax[0].axhline(avg_dens+std_dens*i,ls='--')

    ax[1].axhline(avg_temp,ls='-')
    for i in [-1,1]: ax[1].axhline(avg_temp+std_temp*i,ls='--')

    ax[1].set_xlabel('Shot Number')
    ax[0].set_ylabel('Plasma Density [$cm^{-3}$]')
    ax[1].set_ylabel('Plasma Temperature [eV]')
    
logging.basicConfig(level = logging.INFO)
#calc_plasma_prop('11_19_2018/raw/10/data_0.txt',plotting=True)
time_scan('data/11_27_2018/raw/0/data_{}.txt')

plt.show()
