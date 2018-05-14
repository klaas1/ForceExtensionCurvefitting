# -*- coding: utf-8 -*-
"""
Created on Mon Apr 23 14:35:29 2018

@author: nhermans
"""
import numpy as np
import matplotlib.pyplot as plt
from numpy import genfromtxt
import csv
import os 
from scipy import signal
plt.close()

def read_dat(Filename):
    f = open(Filename, 'r')
    #get headers
    headers = f.readlines()[0]
    headers = headers.split('\t')
    f.close()  
    #get data
    data = genfromtxt(Filename, skip_header = 1)
    return data, headers
    
def subtract_reference(data, headers, Beads=3, MedianFilter=5):
    """Open .dat file from magnetic tweezers, averages the least moving beads and substracts them from the signal. 
    Output is a 2D array with all the data
    ***kwargs:
        Beads = number of beads to use for averaging, default = 3
        MedianFilter = LowPass filter for applied to averaged signal, default = 5. Needs to be an odd number
    """
    T = data[:,headers.index('Time (s)')]
    Z_all = data[:,headers.index('Z0'+' (um)')::4]
    X_all = data[:,headers.index('X0'+' (um)')::4]
    Y_all = data[:,headers.index('Y0'+' (um)')::4]
    Z_std =  np.std(X_all, axis=0) * np.std(Y_all, axis=0) * np.std(Z_all, axis=0)
    Z = Z_all[:,np.nanargmin(Z_std)]
    fit = np.polyfit(np.append(T[:100], T[len(T)-100:len(T)]),np.append(Z[:100], Z[len(Z)-100:len(Z)]),1)
    fit_fn = np.poly1d(fit)                              # fit_fn is a function which takes in x and returns an estimate for y  
#    plt.scatter(T,fit_fn(T), color = 'g')
    
    Z_DriftCorrected = np.subtract(Z_all, np.tile(fit_fn(T),[len(Z_all[0,:]),1]).T)
    Z_std =  np.std(X_all, axis=0) * np.std(Y_all, axis=0) * np.std(Z_all, axis=0)
    dZ = np.nanmax(Z_DriftCorrected,axis=0) - np.nanmin(Z_DriftCorrected,axis=0)
    Z_std = dZ * Z_std
    
    AveragedStuckBead = np.zeros(len(T))
    StuckBead=np.array([])
    mean=0
    ReferenceBeads = []
    
    for i in range(0,Beads):
        Low = np.nanargmin(Z_std)
        ReferenceBeads = np.append(ReferenceBeads,Low)
        StuckBead = Z_all[:,Low]
        mean += np.mean(StuckBead)
        StuckBead = np.subtract(StuckBead,np.mean(StuckBead))
        StuckBead = np.nan_to_num(StuckBead)
        AveragedStuckBead = np.sum([AveragedStuckBead,StuckBead/Beads], axis=0)
        Z_std[Low] = np.nan
        
    mean = mean / Beads    
    AveragedStuckBead = signal.medfilt(AveragedStuckBead,MedianFilter)
    for i,x in enumerate(Z_std):
        Position = headers.index('Z'+str(i)+' (um)')
        data[:,Position] = np.subtract(data[:,Position], AveragedStuckBead + mean )
        
#    for i in ReferenceBeads:
#        plt.scatter(T,data[:,headers.index('Z'+str(int(i))+' (um)')], alpha=0.5, label=str(i), lw=0) 
    return ReferenceBeads, Z_std, AveragedStuckBead, headers, data

folder = r'G:\Klaas\Tweezers\Yeast Chromatin\Regensburg_18S\2017\170728\FlowCell PDMS'
newpath = folder+r'\CorrectedDat'   

if not os.path.exists(newpath):
    os.makedirs(newpath)
    
filenames = os.listdir(folder)
os.chdir(folder)
    
Filenames = []                                                                  #All .fit files    
for filename in filenames:
    if filename[-4:] == '.dat':
        Filenames.append(filename)

for Filenum, DatFile in enumerate(Filenames):
    try: data, headers = read_dat(DatFile)
    except OSError: 
        print('>>>>>>>>>>>>File ', DatFile,' skipped>>>>>>>>>' ) 
        continue
    try: ReferenceBeads, Z_std, AveragedStuckBead, headers, data = subtract_reference(data, headers,3,11)
    except ValueError:
        print('>>>>>>>>>>>>no Z found in ', DatFile,', probably a calibration file>>>>>>>>>' )
        continue
    
    plt.figure(Filenum)
    T = data[:,headers.index('Time (s)')]
    plt.scatter(T,AveragedStuckBead, color = 'b')
    plt.title(DatFile)
    plt.xlabel('time (s)')
    plt.ylabel('Z (um)')
    
    for i in ReferenceBeads:
        plt.scatter(T,data[:,headers.index('Z'+str(int(i))+' (um)')], alpha=0.5, label=str(i), lw=0)
        #plt.scatter(T,data_original[:,headers.index('Z'+str(int(i))+' (um)')], alpha=0.5, label=str(i), lw=0, color=plt.cm.cool(i))
    plt.legend(loc='best')
    plt.show()
    
    with open(newpath +'\\'+ DatFile, 'w') as outfile:    
        writer = csv.writer(outfile, delimiter ='\t') 
        writer.writerow(headers)
        for row in data:
            writer.writerow(row)