import numpy as np
import logging
import matplotlib.pyplot as plt
import probe_math as pmath

def plot_data(data):
    fig,ax = plt.subplots()

    for i in range(1,5):
        ax.plot(data[0],data[i])
    
    fig2,ax2 = plt.subplots()
    ax2.plot(data[0],data[3]-data[4])
    ax2.plot(data[0],data[3]-data[1])
     
def calc(data,ax=''):
    #fig,ax = plt.subplots()
    #data = pmath.apply_filter(data)
    return pmath.calculate_plasma_params(data,ax2=ax)
    
def scan_plot():
    base_filename = 'data/08_03_2018'
    key = np.loadtxt('{}/run_key.txt'.format(base_filename),skiprows=1)
    
    #plot the plasma density vs chamber pressure w/ different lines for each solenoid value
    unique_solenoid_currents = np.unique(key.T[3])
    
    #sort points into bins for each solenoid current
    bins = [[] for i in range(len(unique_solenoid_currents))]
    
    for ele in key:
        bins[np.where(unique_solenoid_currents==ele[3])[0][0]].append(ele)
        
        
    plot_data = []    
        
    for bin in bins:
        shots = np.array(bin)
        #logging.info(shots)
        temp = []
        for shot in shots:
            index = shot[0]
            pressure = shot[1]
            
            #average over 10 shots
            n_samples = 10
            dens = []
            for i in range(n_samples):
                data = np.loadtxt('data/08_03_2018/{}/data_{}.txt'.format(int(index),i),skiprows=1).T
                plasma_density,plasma_temp = calc(data)
                dens.append(plasma_temp[0])
            ndens = np.asfarray(dens)
            avg = np.mean(ndens)
            std = np.std(ndens)
            
            if std < avg:
                temp.append([pressure,avg,std])
            #logging.info(temp[-1])
            
        plot_data.append(np.asfarray(temp))
    #logging.info(plot_data)
    #plotting
    fig,ax = plt.subplots()
    for line,solenoid_current in zip(plot_data,unique_solenoid_currents):
        #ax.set_yscale('log')
        
        line = line.T
        ind = np.lexsort(np.flipud(line))
        #logging.debug(line[0][ind])
        
        ax.errorbar(line[0][ind],line[1][ind],yerr=line[2][ind],marker='.',label='{}A'.format(solenoid_current))
    ax.legend()        
    
if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    #for i in range(4):
    #    fig,ax = plt.subplots()
    #    data = np.loadtxt('data/08_03_2018/2/data_{}.txt'.format(i)).T
    #    a,b = calc(data,ax=ax)
    #    logging.info(a)
        
    scan_plot()
    
    
    plt.show()
