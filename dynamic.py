from ast import literal_eval
from utils import Locations

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
def reader(file):
    # Obtain orders, can replace later, no need to save to csav
    dirName = os.path.dirname(os.path.abspath(__file__))
    if file == 'mainQ':
        mainQ_path = os.path.join(dirName, 'outputs/logs/mainQ.csv')
        if os.path.exists(mainQ_path):
            try:
                mainQ = pd.read_csv(mainQ_path, encoding='utf-8', on_bad_lines='warn')
            except:
                mainQ = None
        else:
            mainQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format('order')), encoding='utf-8', on_bad_lines='warn')
            
    else:
        mainQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format(file)), encoding='utf-8', on_bad_lines='warn')

    # Obtain timetable data, can replace later, no need to save to csav
    timetable = {}
    for tour in range(4):
        try:
            timetable[tour] = pd.read_csv(
                os.path.join(dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1', on_bad_lines='warn')
        except:
            continue

    return mainQ, timetable

# Estimate coordinates of launch
def estCor(time_now,launch_etd,tour,i,etd,timetable,cur):
    tri_factor = (time_now - launch_etd[tour][i][etd]) / (launch_etd[tour][i][etd+1] - launch_etd[tour][i][etd])
    diff_coor = [Locations[timetable[tour].iloc[i,etd+1][0]][x] - Locations[cur][x] for x in range(2)]
    mul_coor = [tri_factor * diff_coor[y] for y in range(2)]
    est_coor = [round(mul_coor[z]) + Locations[cur][z] for z in range(2)]
    return est_coor

# Converts string '[list]' to [list]
def convert_to_list(timetable, fleetsize):
    if type(timetable) != dict:
        timetable = {0:timetable}
    for tour in timetable:
        for i in range (fleetsize):
            try:
                for j in range(len(timetable[tour].iloc[0])):
                    try:
                        timetable[tour].iloc[i,j] = literal_eval(timetable[tour].iloc[i,j])
                    except:
                        pass   
            except:
                for j in range(len(timetable.iloc[0])):
                    try:
                        timetable.iloc[i,j] = literal_eval(timetable.iloc[i,j])
                    except:
                        pass                   
    return timetable

# Code for dynamic element
def dynamic(file, fleetsize, time_now):
    # Run optimiser
    mainQ,timetable = reader(file)
    
    # To change when implement server to detect for change rather than looping
    launch_route = {}
    launch_location = {}
    launch_etd = {}

    # Convert list entries in pandas from string to list
    timetable = convert_to_list(timetable, fleetsize)
    
    # Running through all the tours 
    for tour in timetable:
        launch_route[tour]={}
        launch_etd[tour] = {}
        launch_location[tour] = {}
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
            for etd in range(len(launch_etd[tour][i])):
                try:
                    if launch_etd[tour][i][etd] <= time_now:
                        if etd < len(launch_etd[tour][i])-1: # For launches that did not leave
                            pass
                        else:
                            launch_location[tour][i]=['Returned']
                            etd -= 1
                    else:
                        etd -= 1
                        launch_location[tour][i]=[timetable[tour].iloc[i,etd][0]]
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
            
            # Removing bookings from mainQ for zones served
            if mainQ is not None:
                for v in range(len(launch_route[tour][i])):
                    # Visualise which booking is deleted, debugging purposes
                    #if not mainQ[(mainQ.Zone == launch_route[tour][i][v]) & (mainQ.End_TW < time_now) & (launch_etd[tour][i][v] <= time_now)].empty:
                        #print(mainQ[(mainQ.Zone == launch_route[tour][i][v]) & (mainQ.End_TW < time_now) & (launch_etd[tour][i][v] <= time_now)])
                    b_in = mainQ[(mainQ.Zone == launch_route[tour][i][v])].index # &(mainQ.End_TW < time_now) to include condition for end tw
                    if (launch_etd[tour][i][v] <= time_now):
                        mainQ = mainQ.drop(b_in)
                    mainQ.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs/logs/mainQ.csv'), encoding='utf-8', index=False)

            #print(timetable[tour])  
        #print('\nLaunch location for tour {} is: '.format(tour), launch_location) 
        #print('\nLaunch_etd is: ', launch_etd)
        # print('\nLaunch route is: ', launch_route)
        #print('\nMainQ is: ', mainQ)

    # Convert min in timetable to hr
    for tour in timetable:
        for i in range(fleetsize):
            for j in range(len(timetable[tour].iloc[i])):
                try:    
                    for k in range(3):
                        try:
                            t = int(timetable[tour].iloc[i,j][k])
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
        #schedule(file,fleetsize,None)

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
