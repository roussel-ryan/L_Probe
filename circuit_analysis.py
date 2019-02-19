import numpy as np
import matplotlib.pyplot as plt

def main():
    data = np.loadtxt('circuit_benchmark_data.txt',skiprows=1).T
    R = data[0]*1000
    V_diff = data[2] - data[1]
    V = 54
    I = V / R
    fig,ax = plt.subplots()
    
    ax.set_xlabel('R (Ohm)')
    ax.set_ylabel('I (A)')
    ax.loglog(R,I)
    
    fig2,ax2 = plt.subplots()
    ax2.semilogy(V_diff,I,'+')
    
    I_calc = 10**((V_diff-5.85)/1)/1.1
    ax2.semilogy(V_diff,I_calc)

    
    plt.show()

main()