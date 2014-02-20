#######################################################################
# PixelAliveAnalysisForThr.py
# Original author : M . Malberti 17/12/2013
#
#######################################################################

import os
import sys
from ROOT import *
import itertools



pixelAnalysisExe   = './bin/linux/x86_64_slc5/PixelAnalysis.exe'
config             = 'configuration/PixelAliveAnalysis.xml'
rundir             = os.environ['POS_OUTPUT_DIRS']
dacdir             = os.environ['PIXELCONFIGURATIONBASE']+'/dac'



def RunPixelAliveAnalysis(run):
    currentdir = os.getcwd() 
    cmd = '%s %s %d'%(pixelAnalysisExe, config, run)
    os.system(cmd) 


def CheckEfficiency(run, filename, iteration, maxDeadPixels):
    
    maxeff = 100
    numPixels = 4160
    numFailingRocs = 0

    # prepare output file where ROCs failing PixelAlive will be written
    outfile = open("%s_%d.txt"%(filename,iteration),'w')

    # open PixelAlive root file to be analyzed
    path = '%s/Run_%d/Run_%d/' % (rundir,runfolder(run),run)
    files = [ file for file in os.listdir('%s'%path) if 'PixelAlive_Fed_' in file]
    print 'Found files: ', files
    if len(files)!=1:
        sys.exit('PixelAlive root file NOT found !!!')
    file = TFile( '%s/Run_%d/Run_%d/%s' % (rundir,runfolder(run),run,files[0]) )

    #file = TFile('PixelAlive_Fed_37-38_Run_1171.root') # for test
    
    FPix.cd()
   
    for obj0 in gDirectory.GetListOfKeys(): #FPix_BmI
        if obj0.IsFolder():
            obj0.ReadObj().cd()

            for obj1 in gDirectory.GetListOfKeys(): # DISK folder 
                if obj1.IsFolder():
                    obj1.ReadObj().cd()

                    for obj2 in gDirectory.GetListOfKeys(): ## BLD folder
                        if  obj2.IsFolder():
                            obj2.ReadObj().cd()

                            for obj3 in gDirectory.GetListOfKeys(): ## PNL folder
                                if  obj3.IsFolder():
                                    obj3.ReadObj().cd()

                                    for obj4 in gDirectory.GetListOfKeys(): ## PLQ folder
                                        if  obj4.IsFolder():
                                            obj4.ReadObj().cd()

                                            for obj5 in gDirectory.GetListOfKeys(): ## ROC folder: find one TH2F for each ROC
                                                histo = obj5.ReadObj()
                                                hname   = histo.GetName()
                                                xBins   = histo.GetNbinsX()
                                                yBins   = histo.GetNbinsY()
 
                                                # count dead pixels in each roc
                                                numDeadPixels=0
                                                for x in range(1,xBins+1):
                                                    for y in range(1,yBins+1):
                                                        if histo.GetBinContent(x,y) < maxeff:
                                                            numDeadPixels=numDeadPixels+1;
                                                if (numDeadPixels > maxDeadPixels):
                                                    numFailingRocs=numFailingRocs+1
                                                    rocname = hname.replace(' (inv)','')
                                                    print '%s - Number of dead pixels = %d' %(rocname,numDeadPixels)
                                                    outfile.write('%s\n'%rocname)

    print 'Number of failing ROCs = %d'% numFailingRocs
    outfile.close()
    

def runfolder(run):
    f = int(run/1000)*1000
    return f 



def findDacFromKey(key):
    #find dac settings corresponding to the key used for this run
    aliases = open(os.environ['PIXELCONFIGURATIONBASE']+'aliases.txt','r')
    a = [item for item in aliases if item.startswith('PixelAlive     %s'%key)]
    if len(a)<1:
        sys.exit('ERROR: incorrect key! Please check ')
    else:
        aliases.seek(0)
        dac = [item.split()[1] for item in aliases if item.startswith('dac') ]

    print "Used dac ", dac[0]
    return dac[0]



def ChangeVcThr(run,key,filename,iteration,excluded,deltafilename,singleStep,largeStep,safetyMargin):
    
    # --- Read file containing the list of rocs that you want to exclude from the procedure              ---
    # --- (for example: known problematic ROCs that fail PixelAlive no matter how high the threshold is) ---
    excludedfile = open(excluded,'r')
    excludedrocs = [line.replace('\n','') for line in excludedfile]
    #print 'ROCs to be excluded at this iteration: ', excludedrocs
    
    # --- Read file containing the list of rocs that failed the PixelAlive at this iteration ---------------
    failedfile = open("%s_%d.txt"%(filename,iteration),'r')
    failedrocs = [line.replace('\n','') for line in failedfile]
    # print 'ROCs failing at this iteration: ', failedrocs                   
   
    # --- Read file containing the list of deltas from the previous iteration ------------------------------
    # --- build a dictionary with key = roc, value = delta
    rocsdelta = {}
    if os.path.isfile('%s_%d.txt'%(deltafilename,iteration-1) ):
        deltafile = open("%s_%d.txt"%(deltafilename,iteration-1),'r')
        list = [line.replace('\n','').split() for line in deltafile]
        rocsdelta = { el[0]:int(el[1]) for el in list } 
        #print rocsdelta
                
    # --- Prepare dir for new dac settings -----------------------------------------------------------------
    tmpdir = 'new'
    cmd = 'mkdir %s'%tmpdir
    os.system(cmd)

    # -- Copy dac settings used for the PixelAlive run locally ---------------------------------------------
    dac = findDacFromKey(key)    
    cmd = 'cp  %s/%s/*.dat ./'%(dacdir,dac)
    os.system(cmd)

    # --- change VcThr: ------------------------------------------------------------------------------------
    # --- 
    deltafilenew = open("%s_%d.txt"%(deltafilename,iteration),'w')
    files = [file for file in os.listdir('./') if 'ROC_DAC_module' in file]
    for f in files:
        fileold = open(f)
        filenew = open('%s/%s'%(tmpdir,f),'w')
        # --- group dac settings via a separator - the group separator is ROC
        for key,group in itertools.groupby(fileold,isa_group_separator):
            for item in group:
                if key:
                    roc,name = item.split()
                    filenew.write(item)
                elif 'VcThr' in item:
                    vcthr,value = item.split()
                    #newvalue = int(value)
                    #delta = 0
                    if name in excludedrocs:
                        newvalue = int(value)
                        delta = 0
                    else:
                        # -- if the ROC pass PixelAlive
                        if name not in failedrocs:
                            if iteration == 0:
                                newvalue = int(value) + largeStep
                                delta    = largeStep
                            else:                                     
                                if rocsdelta[name] == largeStep:
                                    newvalue = int(value) + largeStep
                                    delta    = largeStep
                                elif rocsdelta[name] == 0:
                                    newvalue = int(value)
                                    delta    = 0
                                elif (rocsdelta[name] >  0 and rocsdelta[name] < largeStep) or (rocsdelta[name]<0):
                                    newvalue = int(value) - (safetyMargin - singleStep)
                                    delta    = 0
                        # -- if the ROC fails PixelAlive        
                        else:
                            if iteration == 0:
                                newvalue = int(value) - singleStep
                                delta    = - singleStep
                            else:
                                if rocsdelta[name] == largeStep:
                                    newvalue = int(value) - singleStep
                                    delta    = largeStep - singleStep
                                elif rocsdelta[name] <= 0:
                                    newvalue = int(value) - singleStep
                                    delta    = rocsdelta[name] - singleStep
                                elif (rocsdelta[name] >  0 and rocsdelta[name] < largeStep):
                                    newvalue = int(value) - singleStep
                                    if ( rocsdelta[name] != 2 ):
                                        delta    = rocsdelta[name] - singleStep
                                    else:
                                        delta    = 1
                    #print name, value, newvalue                
                    filenew.write('VcThr:         %d\n'%newvalue)
                    deltafilenew = open("%s_%d.txt"%(deltafilename,iteration),'a')
                    deltafilenew.write('%s %d\n'%(name,delta))
                else:
                    filenew.write(item)
        fileold.close()
        filenew.close()
        deltafilenew.close()


def isa_group_separator(line):
    return 'ROC:' in line



def MakeNewDacSettings():
    currentdir = os.getcwd()

    cmd = 'cd %s'%dacdir
    os.chdir('%s'%dacdir)
        
    # make list of subdirectories in dac/ directory    
    subdirs = [ int(x) for x in os.walk('.').next()[1] ]
    subdirs.sort()
    print 'Last dac dir : ', subdirs[-1]    
    lastsettings = subdirs[-1]
    newsettings = subdirs[-1]+1
    cmd = 'cp -r %d %d'%(lastsettings,newsettings)
    os.system(cmd)
 
    cmd = 'cd %s'%currentdir
    os.chdir('%s'%currentdir)

    cmd = 'cp new/ROC_DAC_module_FPix*dat %s/%d'%(dacdir,newsettings)    
    os.system(cmd)
        
    cmd = 'PixelConfigDBCmd.exe --insertVersionAlias dac %d Default'%newsettings
    print cmd
    os.system(cmd)




from optparse import OptionParser
parser = OptionParser()
parser.add_option("-r","--run",dest="run",type="int",help="Run number")
parser.add_option("-k","--key",dest="key",type="string",help="Number identifying the key used for the current run.")
parser.add_option("-i","--iteration",dest="iteration",type="int",default=-1,help="Iteration")
parser.add_option("-o","--outputFile",dest="output",type="string",default="failed",help="Name of the output file containing the list of failing rocs. Default is failed.txt")
parser.add_option("-d","--deltaFile",dest="delta",type="string",default="delta",help="Name of the output file containing the deltaVcThr. Default is delta.txt")
parser.add_option("-e","--exclude",dest="exclude",type="string",default="failed_0.txt",help="List of the ROCs you want to exclude from the iterative procedure")
parser.add_option("","--singleStep",dest="singleStep",type="int",default=2,help="Step width. Default is 2")
parser.add_option("","--largeStep",dest="largeStep",type="int",default=8,help="Large step width. Default is 8")
parser.add_option("","--safetyMargin",dest="safetyMargin",type="int",default=4,help="Safety margin. Default is 4")
parser.add_option("","--maxDeadPixels",dest="maxDeadPixels",type="int",default=10,help="Maximum number of dead pixels per ROC. Default is 10.")

(options,args)=parser.parse_args()

if not options.run or  not options.key  or options.iteration < 0:
    sys.exit('Usage: PixelAliveAnalysisForThr.py -r <run> -d <dac> -i <iteration> \n Exiting.')

# --- some sanity check
if os.path.isfile("%s_%d.txt"%(options.output,options.iteration)):
    sys.exit('Error: file %s_%d.txt exists'%(options.output,options.iteration))

if os.path.isfile("%s_%d.txt"%(options.delta,options.iteration)):
    sys.exit('Error: file %s_%d.txt exists'%(options.delta,options.iteration))

if (options.largeStep%options.singleStep != 0) :
    sys.exit('Error: used largeStep=%d and singleStep=%d are not valid: largeStep must be a multiple of the singleStep'%(options.largeStep,options.singleStep))

# --- analyze PixelAlive run
RunPixelAliveAnalysis(options.run)

# --- check the efficiency of all ROCS and make a list of failed rocs (i.e. rocs with more than 10 dead pixels)
CheckEfficiency(options.run,options.output,options.iteration,options.maxDeadPixels)

# --- prepare new dac settings by changing VcThr
ChangeVcThr(options.run,options.key,options.output,options.iteration,options.exclude,options.delta,options.singleStep,options.largeStep, options.safetyMargin)
MakeNewDacSettings()



