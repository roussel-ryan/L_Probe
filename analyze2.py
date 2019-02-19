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
    buffer_size = 0.2
    indicies = np.argwhere(current > 40)
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
        ax.legend()

        fig2,ax2 = plt.subplots()
        ax2.plot(t,T,'g')
        ax3 = ax2.twinx()
        ax3.semilogy(t,density)

    return (np.mean(T),np.std(T),np.mean(density),np.std(density))

def solenoid_scan(indicies,ax):
    index = indicies
    scan_vals = [15,20,25,30]

    #fig,ax = plt.subplots()
    #ax2 = ax.twinx()
    
    tdata = []
    for ind,val in zip(index,scan_vals):
        data = []
        n_samples = 10
        for i in range(n_samples):
            data.append(calc_plasma_prop('11_01_2018/raw/{}/data_{}.txt'.format(ind,i)))
        ndata = np.asfarray(data).T

        avg_T = np.mean(ndata[0])
        std_T = np.sqrt(np.sum(ndata[1]**2)) / n_samples
        avg_D = np.mean(ndata[2])
        std_D = np.sqrt(np.sum(ndata[3]**2)) / n_samples
        tdata.append((val,avg_T,std_T,avg_D,std_D))
    ntdata = np.asfarray(tdata).T

    ax.errorbar(ntdata[0],ntdata[3],ntdata[4],fmt='o',capsize = 3)

def longitudinal_scan(base,loc,scan_number,ax,shift=0):
    #loc = np.arange(2,26,2)
    #fig,ax = plt.subplots()
    #ax2 = ax.twinx()
    
    tdata = []
    for a in loc:
        data = []
        n_samples = 10
        for i in range(n_samples):
            data.append(calc_plasma_prop(base.format(scan_number,a,i)))
        ndata = np.asfarray(data).T

        avg_T = np.mean(ndata[0])
        std_T = np.sqrt(np.sum(ndata[1]**2)) / n_samples
        avg_D = np.mean(ndata[2])
        std_D = np.sqrt(np.sum(ndata[3]**2)) / n_samples
        tdata.append((a+shift,avg_T,std_T,avg_D,std_D))
    ntdata = np.asfarray(tdata).T
    logging.info(ntdata)
    ax[0].errorbar(ntdata[0],ntdata[3],ntdata[4],fmt='o',capsize = 3,label='scan {}'.format(scan_number))
    ax[1].errorbar(ntdata[0],ntdata[1],ntdata[2],fmt='o',capsize = 3,label='scan {}'.format(scan_number))

def longitudinal_plot():
    fig,ax = plt.subplots(2,1,sharex=True)
    longitudinal_scan('data/02_06_2019/scans/scan_{}/data_{}.0mm_{}.txt',np.arange(2,80,2),1,ax)
    #longitudinal_scan('11_12_2018/scans/scan_{}/data_{}.0mm_{}.txt',np.arange(2,80,2),2,ax)
    #longitudinal_scan('11_13_2018/scans/scan_{}/data_{}.0mm_{}.txt',np.arange(2,80,2),1,ax)

#    longitudinal_scan('11_19_2018/scans/scan_{}/data_{}.0mm_{}.txt',np.arange(52,81,1),0,ax)
#    longitudinal_scan('11_17_2018/scans/scan_{}/data_{}.0mm_{}.txt',np.arange(4,80,4),1,ax)
#    longitudinal_scan('11_17_2018/scans/scan_{}/data_{}.0mm_{}.txt',np.arange(4,80,4),2,ax)
    
    for ele in ax:
        ele.legend()

    ax[0].set_ylabel('Plasma Density [$cm^{-3}$]')
    ax[1].set_ylabel('Electron Temperature [eV]')
    ax[1].set_xlabel('Longitudinal Position')

    #longitudinal_scan(np.arange(2,22,2),2,ax,48)
    
logging.basicConfig(level = logging.INFO)
#fig,ax = plt.subplots()
#solenoid_scan([3,0,2,1],ax)
#solenoid_scan([4,5,6,7],ax)
#calc_plasma_prop('11_12_2018/scans/scan_1/data_2.0mm_1.txt',plotting=True)
longitudinal_plot()
plt.show()
