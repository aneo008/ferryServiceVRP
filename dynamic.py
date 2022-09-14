from ast import literal_eval
from utils import Locations
from schedule import schedule

import time as timer
import os
import argparse
import pandas as pd

# Input dataset file and fleetsize
def inputs():
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('--file', metavar='f',
                           default='order', help='File name of the order book')
    argparser.add_argument('--fleetsize', metavar='l',
                           default='5', help='Total number of launches available')
    args = argparser.parse_args()
    file = args.file
    fleet = int(args.fleetsize)
    return file, fleet

# Reads outputs
def reader(file,fleetsize):
    # Obtain orders, can replace later, no need to save to csav
    dirName = os.path.dirname(os.path.abspath(__file__))
    if file == 'mainQ':
        mainQ_path = os.path.join(dirName, 'outputs/logs/mainQ.csv')
        if os.path.exists(mainQ_path):
            try:
                mainQ = pd.read_csv(mainQ_path, encoding='latin1', on_bad_lines='warn')
            except:
                mainQ = None
        else:
            mainQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format('order')), encoding='latin1', on_bad_lines='warn')
            
    else:
        mainQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format(file)), encoding='latin1', on_bad_lines='warn')
        

    # Obtain objective function, can replace later, no need to save to csav
    objFn = pd.read_csv(os.path.join(dirName, 'outputs/logs/objFn.csv'), encoding='latin1', on_bad_lines='warn')

    # Obtain timetable data, can replace later, no need to save to csav
    timetable = {}
    for tour in range(len(objFn)):
        timetable[tour] = pd.read_csv(
            os.path.join(dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1', on_bad_lines='warn')

    return mainQ, timetable, objFn

# Estimate coordinates of launch
def estCor(time_now,launch_etd,tour,i,etd,timetable,cur):
    tri_factor = (time_now - launch_etd[tour][i][etd]) / (launch_etd[tour][i][etd+1] - launch_etd[tour][i][etd])
    diff_coor = [Locations[timetable[tour].iloc[i,etd+1][0]][x] - Locations[cur][x] for x in range(2)]
    mul_coor = [tri_factor * diff_coor[y] for y in range(2)]
    est_coor = [round(mul_coor[z]) + Locations[cur][z] for z in range(2)]
    return est_coor

# Converts string '[list]' to [list]
def convert_to_list(timetable, num_of_tours, fleetsize):
    for tour in range (num_of_tours):
        for i in range (fleetsize):
            for j in range(len(timetable[tour].iloc[0])):
                try:
                    timetable[tour].iloc[i,j] = literal_eval(timetable[tour].iloc[i,j])
                except:
                    pass                     
    return timetable

# Code for dynamic element
def dynamic(file, fleetsize, time_now):
    # Run optimiser
    mainQ,timetable,objFn = reader(file,fleetsize)

    # To change when implement server to detect for change rather than looping
    launch_route = {}
    launch_location = {}
    launch_etd = {}
    num_of_tours = len(objFn.iloc[0])

    # Convert list entries in pandas from string to list
    timetable = convert_to_list(timetable, num_of_tours, fleetsize)
    
    # Running through all the tours 
    for tour in range(num_of_tours):
        launch_route[tour]={}
        launch_etd[tour] = {}
        # Running through all launches
        for i in range(fleetsize):
            # Calculating Launch i ETD for all tours
            launch_etd[tour][i] = []    
            for j in range(len(timetable[tour].iloc[0])):
                if timetable[tour].iloc[i,j][2] == 'NA':
                    launch_etd[tour][i].append(timetable[tour].iloc[i,j][1]) # ETA back to port
                    break
                elif timetable[tour].iloc[i,j][1] == 'NA':
                    launch_etd[tour][i].append(timetable[tour].iloc[i,j][2]) # ETD from port
                else:
                    launch_etd[tour][i].append(timetable[tour].iloc[i,j][2])

            # Running through all the estinations of launch departure times to find previous or current destination
            launch_location[tour] = {}
            for etd in range(len(launch_etd[tour][i])):
                try:
                    if launch_etd[tour][i][etd] <= time_now:
                        if etd < len(launch_etd[tour][i])-1:
                            launch_location[tour][i]=[timetable[tour].iloc[i,etd][0]]
                        else:
                            launch_location[tour][i]=['Returned']
                            etd -= 1
                    else:
                        etd -= 1
                        break
                except:
                    continue
            
            # Calculating launch route
            launch_route[tour][i] = []
            for zone in range(len(timetable[tour].iloc[i])):
                try: # Only if it is a list, since some are empty
                    launch_route[tour][i].append(timetable[tour].iloc[i,zone][0])
                except:
                    pass
            
            # Only calculate launch info for current tour
            if (540 + 150 * tour) <= time_now <= (540 + 150 * (tour+1)): 
                # Calculate estimated coordinates
                cur = launch_location[tour][i][0]
                if cur == 'Returned': # Check if launch has returned, if yes, append port coordinates
                    launch_location[tour][i].append(Locations[timetable[tour].iloc[i,0][0]])
                else:
                    est_coor = estCor(time_now,launch_etd,tour,i,etd,timetable,cur)
                    launch_location[tour][i].append(est_coor)
            
                # Removing bookings from mainQ for launches that left
                vessel = launch_location[tour][i][0]
                if mainQ is not None:
                    if (vessel != 'Port West') and (vessel != 'Port MSP') and (vessel != 'Returned'):
                        for v in launch_route[tour][i]:
                            mainQ = mainQ[mainQ.Zone != v]
                            mainQ.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs/logs/mainQ.csv'), index=False)
                    else:
                        pass
                else:
                    pass        
            else:
                pass

        
            #print(timetable[tour])  
        #print('\nLaunch location for tour {} is: '.format(tour), launch_location) 
        #print('\nLaunch_etd is: ', launch_etd)
        #print('\nLaunch route is: ', launch_route)
        #print('\nMainQ is: ', mainQ)

        # Convert min in timetable to hr
        for tour in range (num_of_tours):
            for i in range(fleetsize):
                for j in range(len(timetable[tour].iloc[i])):
                    try:    
                        for k in range(3):
                            try:
                                t = timetable[tour].iloc[i,j][k]
                                hr = str(t // 60).rjust(2,'0')
                                m = str(t % 60).rjust(2,'0')
                                timetable[tour].iloc[i,j][k] = ("{}:{}".format(hr,m))
                            except:
                                continue
                    except:
                        continue

    return timetable, launch_location, launch_etd, launch_route

def main():
    print("Program is running...")
    time_start = timer.time() # Start timer. Assume 1s = 1min
    time_passed = timer.time() - time_start
    # Finding "current" time
    time_now =  540 + time_passed + 50 # can add time here next time # + 150 * (chosen-1) # 2.5hrs tours

    run_loop = 1
    while run_loop == 1:
        file,fleetsize = inputs()
        # Run schedule.py optimiser
        #schedule(file,fleetsize)

        # Dynamic analysis
        dynamic(file,fleetsize,time_now)
        
        #if (time_now > (540 + (tour+1) * 150)):
        run_loop = 0

    return

# Run main code
if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\ndone.')
