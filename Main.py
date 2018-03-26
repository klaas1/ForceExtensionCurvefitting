# -*- coding: utf-8 -*-
"""
Created on Mon Jan 22 11:52:49 2018

@author: nhermans & rrodrigues
"""
import os 
import matplotlib
matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['text.latex.unicode'] = True
import matplotlib.pyplot as plt
import numpy as np
import Functions as func
import Tools
import pickle
from sklearn.cluster import DBSCAN

folder = 'N:\\Rick\\Tweezer data\\Pythontestfit\\New folder' #folder with chromosome sequence files (note, do not put other files in this folder)
filenames = os.listdir(folder)
os.chdir(folder)

Handles = Tools.Define_Handles()
Steps , Stacks = [],[]                                                          #used to save data (Clustering)
Fignum = 1

plt.close('all')                                                                #Close all the figures from previous sessions

for Filenum, Filename in enumerate(filenames):
    if Filename[-4:] != '.fit' :
        continue
    Force, Time, Z, Z_Selected = Tools.read_data(Filename)                      #loads the data from the filename
    LogFile = Tools.read_log(Filename[:-4]+'.log')                              #loads the log file with the same name
    Pars = Tools.log_pars(LogFile)                                              #Reads in all the parameters from the logfile

    if Pars['FiberStart_bp'] <0: 
        print('<<<<<<<< warning: ',Filename, ': bad fit >>>>>>>>>>>>')
        continue
    print(int(Pars['N_tot']), "Nucleosomes in", Filename, "( Fig.", Fignum, ")")

    #Remove all datapoints that should not be fitted
    Z_Selected, F_Selected, T_Selected = Tools.handle_data(Force, Z, Time, Z_Selected, Handles, Pars)

    if len(Z_Selected)<10:  
        print("<<<<<<<<<<<", Filename,'==> No data points left after filtering!>>>>>>>>>>>>')
        continue

    Filename = Filename.replace('_', '\_')                                      #Right format for the plot headers

    #Generate FE curves for possible states
    PossibleStates = np.arange(Pars['FiberStart_bp']-200, Pars['L_bp']+50,1)    #range to fit 

    #Finding groups/clusters of datapoints      
    ZF_Selected = np.vstack((Z_Selected, F_Selected)).T
    ZT_Selected = np.vstack((Z_Selected, T_Selected)).T

    #fig0 plots the Extension-Force curve
    fig0 = plt.figure()
    ax0 = fig0.add_subplot(1,2,1) 
    
    #fig00 plots the Time-Extension curve
#    fig00 = plt.figure()
    ax00 = fig0.add_subplot(1, 2, 2, sharey=ax0)
    
    
    # Compute DBSCAN
    db = DBSCAN(eps=10, min_samples=7).fit(ZF_Selected)                         #Replace ZF with ZT to cluster in Timetrace
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels = db.labels_
    unique_labels = set(labels)

    NewStates = np.array([])
    Av = np.empty(shape=[0, 2])

    #Plotting the different clusters in different colors, also calculating the mean of each cluster
    colors = [plt.cm.brg(each) for each in np.linspace(0, 1, len(unique_labels))]

    for k, col in zip(unique_labels, colors):
        if k == -1:
           col = [0, 0, 0, 1] # Black used for noise.  

        class_member_mask = (labels == k)

        xy = ZF_Selected[class_member_mask & core_samples_mask]
        XY = ZT_Selected[class_member_mask & core_samples_mask]
        ax0.plot(xy[:, 1], xy[:, 0], 'o', markerfacecolor=tuple(col), markeredgecolor='k', markersize=4, lw=0.5)
        ax00.plot(XY[:, 1], XY[:, 0], 'o', markerfacecolor=tuple(col), markeredgecolor='k', markersize=4, lw=0.5)
        
        if k != -1:
            Av = np.append(Av, [np.array([np.mean(xy[:,0]),np.mean(xy[:, 1])])], axis=0)

        xy = ZF_Selected[class_member_mask & ~core_samples_mask]
        XY = ZT_Selected[class_member_mask & ~core_samples_mask]
        ax0.plot(xy[:, 1], xy[:, 0], 'o', markerfacecolor=tuple(col), markeredgecolor='k', markersize=3, lw=0.1) 
        ax00.plot(XY[:, 1], XY[:, 0], 'o', markerfacecolor=tuple(col), markeredgecolor='k', markersize=3, lw=0.1)  
    
    AllStates = np.empty(shape=[len(Av[:,1]),2,len(PossibleStates)])
    #Making a 3d array containing all the possible states
    for i, x in enumerate(PossibleStates):
        Ratio = func.ratio(x,Pars)
        Fit = np.array(func.wlc(Av[:,1],Pars)*x*Pars['DNAds_nm'] + func.hook(Av[:,1],Pars['k_pN_nm'])*Ratio*Pars['ZFiber_nm'])
        ForceFit = np.vstack((Fit, Av[:,1])).T
        AllStates[:,:,i] = ForceFit        

    #Calculating the states that are closest to the means computed above
    for I,J in enumerate(Av[:,0]):   
        AllDist = np.array([])
        for i,j in enumerate(AllStates[0,0,:]):
            Dist = np.abs(np.subtract(AllStates[:,:,i], Av[I,:]))
            Dist = np.square(Dist)
            Dist = np.sum(Dist, axis=1)
            AllDist = np.append(AllDist, np.min(Dist))
        NewStates = np.append(NewStates, PossibleStates[np.argmin(AllDist)])

    #Plotting the corresponding states in the same color as the clusters
    for i, col in zip(enumerate(NewStates), colors):
        Ratio = func.ratio(i[1],Pars)
        Fit = np.array(func.wlc(Force,Pars)*i[1]*Pars['DNAds_nm'] + func.hook(Force,Pars['k_pN_nm'])*Ratio*Pars['ZFiber_nm'])
        ax0.plot(Force, Fit, alpha=0.9, linestyle=':', color=tuple(col))
        ax00.plot(Time, Fit, alpha=0.9, linestyle='-.', color=tuple(col))        
        
    fig0.suptitle(Filename, y=.99)
    ax0.scatter(Force, Z , color='grey', lw=0.1, s=5, alpha=0.5)
    ax0.set_title(r'Extension-Force Curve of Chromatin Fibre')
    ax0.set_xlabel(r'\textbf{Force} (pN)')
    ax0.set_ylabel(r"\textbf{Extension} (nm)")     
    ax0.set_xlim(np.min(Force)-0.1*np.max(Force),np.max(Force)+0.1*np.max(Force))
    ax0.set_ylim(np.min(Z)-0.1*np.max(Z),np.max(Z)+0.1*np.max(Z))
    
    Plot_Select = True #case True: plot only shows the view of the selected data; case False: plot shows the whole dataset
    if Plot_Select:
        ax0.set_xlim(np.min(F_Selected)-0.1*np.max(F_Selected),np.max(F_Selected)+0.1*np.max(F_Selected))
        ax0.set_ylim(np.min(Z_Selected)-0.1*np.max(Z_Selected),np.max(Z_Selected)+0.1*np.max(Z_Selected))

    ax00.scatter(Time, Z,  c=Time, cmap='gray', lw=0.1, s=5)
    ax00.set_title(r'Timetrace Curve of Chromatin Fibre')
    ax00.set_xlabel(r'\textbf{Time} (s)')
    ax00.set_ylabel(r'\textbf{Extension} (bp nm)')
    ax00.set_xlim([np.min(Time)-0.1*np.max(Time), np.max(Time)+0.1*np.max(Time)])
    ax00.set_ylim([np.min(Z)-0.1*np.max(Z), np.max(Z)+0.1*np.max(Z)])
    if Plot_Select:
        ax00.set_xlim([np.min(T_Selected)-0.1*np.max(T_Selected), np.max(T_Selected)+0.1*np.max(T_Selected)])
        ax00.set_ylim([np.min(Z_Selected)-0.1*np.max(Z_Selected), np.max(Z_Selected)+0.1*np.max(Z_Selected)])

    Filename = Filename.replace( '\_', '_')                                     #Right format to safe the figure
    
    fig0.tight_layout()
    if Plot_Select:
        pickle.dump(fig0, open(Filename[0:-4]+'.FoEx_Time_all_Selected.pickle', 'wb'))  #Saves the figure, so it can be reopend
        fig0.savefig(Filename[0:-4]+'FoEx_Time_all_Selected.pdf', format='pdf')
    else:
        pickle.dump(fig0, open(Filename[0:-4]+'.FoEx_Time_all.pickle', 'wb'))       #Saves the figure, so it can be reopend    
        fig0.savefig(Filename[0:-4]+'FoEx__Time_all.pdf', format='pdf')

    fig0.show()     

    Unwrapsteps = []
    Stacksteps = []
    for x in NewStates:
        if x >= Pars['Fiber0_bp']:
            Unwrapsteps.append(x)
        else:
            Stacksteps.append(x)
    Stacksteps = np.diff(np.array(Stacksteps))
    Unwrapsteps = np.diff(np.array(Unwrapsteps))
    if len(Unwrapsteps)>0: Steps.extend(Unwrapsteps)
    if len(Stacksteps)>0: Stacks.extend(Stacksteps)

    Fignum += 1

#Stepsize,Sigma=func.fit_pdf(steps)
fig3 = plt.figure()
ax6 = fig3.add_subplot(1,1,1)
ax6.hist(Steps,  bins = 50, range = [0,400], label='25 nm steps')
ax6.hist(Stacks, bins = 50, range = [0,400], label='Stacking transitions')
ax6.set_xlabel('stepsize (bp)')
ax6.set_ylabel('Count')
ax6.set_title("Histogram stepsizes in bp using clustering")
ax6.legend()
fig3.tight_layout()
fig3.savefig('Histogram.pdf', format='pdf')
