# -*- coding: utf-8 -*-
"""
Created on Mon Jan 22 11:52:49 2018

@author: nhermans
"""
import os 
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from scipy import stats
import Functions as func
import Tools
#import peakdetect as pk
#from scipy.optimize import curve_fit

#folder = 'N:\\Rick\\Tweezer data\\2018_02_19_15x167 DNA\\data_013_Fit' #folder with chromosome sequence files (note, do not put other files in this folder)
folder = 'P:\\NonEqData\\H1_197\\Best Traces'
#folder = 'C:\\Users\\Klaas\\Documents\\NonEquilibriumModel\\2018'
filenames = os.listdir(folder)
os.chdir(folder)
Handles = {'Select':0,'Pulling':1,'DelBreaks':1,'MinForce':2.5,'MinZ':0,'MaxZ':True,'Denoise':False} 
Fmax_Hook=10
steps , stacks = [],[] #used to save data
plt.close() #close all references to figures still open

for Filename in filenames:
    if Filename[-4:] != '.fit' :
        continue
    Force,Time,Z,Z_Selected = Tools.read_data(Filename)        #loads the data from the filename
    LogFile=Tools.read_log(Filename[:-4]+'.log')    #loads the log file with the same name
    Pars=Tools.log_pars(LogFile)                    #Reads in all the parameters from the logfile
    
    if Pars['FiberStart_bp'] <0: 
        print('<<<<<<<< warning: ',Filename, ': bad fit >>>>>>>>>>>>')
        continue
    print(Pars['N_tot'], Filename)
    
    #### Remove all datapoints that should not be fitted 
    Z_Selected,ForceSelected = Tools.handle_data(Force,Z,Z_Selected, Handles, Pars)
    if len(Z_Selected)==0: 
        print(Filename,'==> No data points left after filtering!')
        continue

    #Generate FE curves for possible states
    PossibleStates = np.arange(Pars['FiberStart_bp']-200, Pars['L_bp']+50,1)                                #range to fit 
    ProbSum=func.probsum(ForceSelected, Z_Selected, PossibleStates, Pars)   #Calculate probability landscape
    PeakInd,Peak=func.findpeaks(ProbSum, 25)                                #Find Peaks
    #Peaks = signal.find_peaks_cwt(ProbSum, np.arange(2.5,30))               #numpy peakfinder
    #Peaks = pk.peakdetect(ProbSum, PossibleStates, 42)[0]
    States=PossibleStates[PeakInd]                                          #Defines state for each peak
    #States=PossibleStates[Peaks]
        
    #Calculate for each datapoint which state it most likely belongs too 
    StateMask=func.attribute2state(ForceSelected,Z_Selected,States,Pars)
    
    #Remove states with fewer than 3 datapoints
    RemoveStates=func.removestates(StateMask)
    if len(RemoveStates)>0: 
        States=func.mergestates(States,RemoveStates)
        StateMask=func.attribute2state(ForceSelected,Z_Selected,States,Pars)
    
    # Merging states that are have similar mean/variance according to Welch test
    UnMergedStates=States
    MergeStates=True
    if len(States) <1 : MergeStates=False
    P_Cutoff=0.5                                       #Significance for merging states    
    
    while MergeStates == True:                          #remove states untill all states are significantly different
        T_test=np.array([])                             #array for p values comparing different states
                    
        for i,x in enumerate(States):
            if i >0: 
                Prob=stats.ttest_ind((StateMask==i)*Z_Selected,(StateMask==i-1)*Z_Selected, equal_var=False) #get two arrays for t_test
                T_test=np.append(T_test,Prob[1])       #Calculates the p-value of neighboring states with Welch test
        
        #Merges states that are most similar, and are above the p_cutoff minimal significance t-test value
        HighP = np.argmax(T_test)
        if T_test[HighP] > P_Cutoff:  # Merge the highest p-value states
            DelState = HighP
            if sum((StateMask == HighP + 1) * 1) < sum((StateMask == HighP) * 1): DelState = HighP + 1
            States = np.delete(States, DelState)  # deletes the state with the fewest datapoints from the state array
            StateMask = StateMask - (StateMask > HighP) * 1  # merges the states in the mask
            Z_NewState = (StateMask == HighP) * Z_Selected  # Get all the data for this state to recalculate mean
            MergeStates = True
        else:
            MergeStates = False  # Stop merging states
                   
        #calculate the number of L_unrwap for the new state
        if MergeStates:
            #find value for merged state with gaus fit / mean
            StateProbSum = func.probsum(ForceSelected[Z_NewState != 0],Z_NewState[Z_NewState != 0],PossibleStates,Pars)
            States[HighP] = PossibleStates[np.argmax(StateProbSum)]                     #Takes the highest value of the probability landscape
            #InsertState = np.sum(PossibleStates*(StateProbSum/np.sum(StateProbSum)))    #Calculates the mean
            #Fit a Guass:
#            mean = sum(PossibleStates[StateProbSum != 0]*StateProbSum[StateProbSum != 0])/len(StateProbSum[StateProbSum != 0])                   
#            sigma = sum(PossibleStates[StateProbSum != 0]*(StateProbSum[StateProbSum != 0]-mean)**2)/len(StateProbSum[StateProbSum != 0])
#            popt,pcov = curve_fit(func.gaus,PossibleStates,StateProbSum,p0=[1,mean,sigma])
        
        StateMask=func.attribute2state(ForceSelected,Z_Selected,States,Pars)
        for i,x in enumerate(States):    
            Z_NewState = (StateMask == i) * Z_Selected    
            StateProbSum = func.probsum(ForceSelected[Z_NewState != 0],Z_NewState[Z_NewState != 0],PossibleStates,Pars)
            States[i] = PossibleStates[np.argmax(StateProbSum)]
    
    #Calculates stepsize
    Unwrapsteps=[]
    Stacksteps=[]
    for x in States:
        if x >= Pars['Fiber0_bp']:
            Unwrapsteps.append(x)
        else:
            Stacksteps.append(x)
    Stacksteps=func.state2step(Stacksteps)
    Unwrapsteps=func.state2step(Unwrapsteps)
    if len(Unwrapsteps)>0: steps.extend(Unwrapsteps)
    if len(Stacksteps)>0: stacks.extend(Stacksteps)
    #Tools.write_data('AllSteps.txt',Unwrapsteps,Stacksteps)
    
    #plotting
    # this plots the FE curve
    fig1 = plt.figure()
    ax1 = fig1.add_subplot(1, 2, 1)
    ax2 = fig1.add_subplot(1, 2, 2)
    fig1.suptitle(Filename, y=1)
    ax1.set_xlabel('Extension [nm]'), ax2.set_xlabel('Free basepairs')
    ax1.set_ylabel('Force [pN]'), ax2.set_ylabel('Probability [AU]')
    ax1.scatter(Z,Force, color="grey",s=1)
    ax1.scatter(Z_Selected,ForceSelected, color="blue", s=1)
    ax2.set_xlim([0, Pars['L_bp']+50])    
    ax2.plot(PossibleStates,ProbSum)
    ax2.scatter(PossibleStates[(PeakInd)],Peak)
    #ax2.scatter(Peaks[:,0],Peaks[:,1], color="orange")
    #ax1.set_xlim([-100, Pars['L_bp']/2.8])
    #ax1.set_ylim([-4,25])

    #plotting
    # this plots the Timetrace    
    fig2 = plt.figure()    
    ax3 = fig2.add_subplot(1, 2, 1)
    ax4 = fig2.add_subplot(1, 2, 2, sharey=ax3)
    fig2.suptitle(Filename, y=1)
    ax3.set_xlabel('time [sec]'), ax4.set_xlabel('Probability [AU]')
    ax3.set_ylabel('Extension [bp nm]')
    ax3.set_ylim([0, Pars['L_bp']*Pars['DNAds_nm']+100])
    ax3.scatter(Time,Z, s=1)
    ax4.plot(ProbSum,PossibleStates*Pars['DNAds_nm'])
    ax4.scatter(Peak,PossibleStates[(PeakInd)]*Pars['DNAds_nm'], s=1)
    ax4.legend(label=States)
    
    for x in States:
        Ratio=func.ratio(x,Pars)
        Fit=np.array(func.wlc(Force,Pars)*x*Pars['DNAds_nm'] + func.hook(Force,Pars['k_pN_nm'],Fmax_Hook)*Ratio*Pars['ZFiber_nm'])
        ax1.plot(Fit,Force, alpha=0.9, linestyle='-.')
        ax3.plot(Time,Fit, alpha=0.9, linestyle='-.')
        
    for x in UnMergedStates:
        Ratio=func.ratio(x,Pars)
        Fit=np.array(func.wlc(Force,Pars)*x*Pars['DNAds_nm'] + func.hook(Force,Pars['k_pN_nm'],Fmax_Hook)*Ratio*Pars['ZFiber_nm'])
        ax1.plot(Fit,Force, alpha=0.1, linestyle=':')
        ax3.plot(Time,Fit, alpha=0.1, linestyle=':')
   

    fig1.tight_layout()
    #fig1.savefig(Filename[0:-4]+'FoEx_all.png', dpi=800)
    fig1.show()
    fig2.tight_layout()
    #fig2.savefig(Filename[0:-4]+'Time_all.png', dpi=800)    
    fig2.show()

#Stepsize,Sigma=func.fit_pdf(steps)
fig3 = plt.figure()
ax5 = fig3.add_subplot(1,1,1)
ax5.hist(steps,  bins = 50, range = [50,250] )
ax5.hist(stacks, bins = 50, range = [50,250])
ax5.set_xlabel('stepsize (bp)')
ax5.set_ylabel('Count')
ax5.set_title("Histogram stepsizes in bp")
ax5.legend(['25 nm steps', 'Stacking transitions'])
#fig3.savefig('hist.png')
fig3.show()
