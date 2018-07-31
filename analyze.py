import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt('data/07_31_2018/1/data_1.txt').T
plt.plot(data[0],data[2])
plt.show()