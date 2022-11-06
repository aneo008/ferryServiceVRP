import os
import shutil
import matplotlib.pyplot as plt
import pandas as pd
import time
from datetime import datetime

from schedule import schedule, route2Timetable
from dynamic import dynamic,reader,convert_to_list
from utils import Locations
from lpModel import calculateRoute
from lpTools import drawSolution2

file = 'order'
fleetsize = 5
dirName = os.path.dirname(os.path.abspath(__file__))

''' 
t_now: what does it do
'''

def time_convert(t):
    hr = str(round(t) // 60).rjust(2, '0')
    m = str(round(t) % 60).rjust(2, '0')
    t = ("{}:{}".format(hr, m))
    return t

def find_tour_launch(zone, launch_route, tw):
    for tour in range(4):
        if tw <= 540+(tour+1)*150:
            break
    try:
        for launch in range(len(launch_route[tour])):
            for z in range(len(launch_route[tour][launch])):
                if launch_route[tour][launch][z] == zone:
                    return tour, launch
                else:
                    continue
    except:
        return tour, None
    return None, None

def delete_Q():
    logs_path = os.path.join(dirName, 'outputs/logs')
    mainQ_path = os.path.join(logs_path, 'mainQ.csv')
    ogQ_path = os.path.join(dirName, 'datasets/ogQ.csv')
    ogQ2_path = os.path.join(dirName, 'datasets/ogQ2.csv')
    img_path = os.path.join(dirName, 'static/img')

    if os.path.exists(mainQ_path):
        os.remove(mainQ_path)
    if os.path.exists(ogQ_path):
        os.remove(ogQ_path)
    if os.path.exists(ogQ2_path):
        os.remove(ogQ2_path)

    for i in range(4):
        # Remove raw_Timetable file if no more orders in that tour
        rawtt_path = os.path.join(os.path.join(
            dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(i)))
        if os.path.exists(rawtt_path):
            os.remove(rawtt_path)

    # Reset maps
    anchorage_map = os.path.join(
        dirName, "Port_Of_Singapore_Anchorages_Chartlet.png")
    for i in range(4):
        map_path = os.path.join(
            img_path, 'order_Tour{}'.format(i+1) + '_schedule.png')
        shutil.copy(anchorage_map, map_path)

     # Reset maps
    anchorage_map = os.path.join(
        dirName, "Port_Of_Singapore_Anchorages_Chartlet.png")
    for i in range(4):
        map_path = os.path.join(
            img_path, 'order_Tour{}'.format(i+1) + '_schedule.png')
        
        shutil.copy(anchorage_map, map_path)

def deleteBooking(id,t_now,cur_tour):
    # Define variables
    t_start = time.time()
    mainQ, _ = reader('mainQ')
    _, launch_location, launch_etd, launch_route = dynamic(
        'mainQ', fleetsize, t_now)
    b_id = mainQ.iloc[id, 0]
    req_type = mainQ.iloc[id, 1]
    zone = mainQ.iloc[id, 2]
    tw = mainQ.iloc[id, 5]
    tour, launch = find_tour_launch(zone, launch_route, tw)

    raw_Timetable = convert_to_list(pd.read_csv(os.path.join(
        dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1'), fleetsize)

    # Remove booking from ogQ - tracks all bookings served and to be served
    if os.path.exists(os.path.join(dirName, 'datasets/ogQ.csv')):
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/ogQ.csv'),
                          encoding='utf-8', on_bad_lines='warn')
    else:
        ogQ = pd.read_csv(os.path.join(
            dirName, 'datasets/{}.csv'.format(file)), encoding='utf-8', on_bad_lines='warn')
    ogQ = ogQ[ogQ.Order_ID != b_id]
    ogQ.to_csv(os.path.join(dirName, 'datasets/ogQ.csv'),
               encoding='utf-8', index=False)

    # Remove booking from mainQ - tracks all bookings to be served
    mainQ = mainQ[mainQ.Order_ID != b_id]

    # Remove booking from route
    launch_route[tour][launch].remove(zone)
    print ("Removed", zone)

    # If deleted request is from upcoming tour
    if tour > cur_tour:
        # Pre-optimisation step. If there is only 1 booking, that is the one to be deleted, delete raw_Timetable
        tour_in_og = ogQ[ogQ.Start_TW >= 540 + 150*tour]
        if len(tour_in_og) == 0:
            rawtt_path = os.path.join(os.path.join(dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)))
            os.remove(rawtt_path)
            anchorage_map = os.path.join(
                dirName, "Port_Of_Singapore_Anchorages_Chartlet.png")
            map_path = os.path.join(
                dirName, 'static/img', 'order_Tour{}'.format(tour+1) + '_schedule.png')
            shutil.copy(anchorage_map, map_path)
        else:
            schedule('ogQ', fleetsize, tour)

    # If launch has not left
    elif (launch_location[tour][launch][1] == Locations["Port West"]) or (launch_location[tour][launch][1] == Locations["Port MSP"]):
        # Get route for launches that have not left
        not_left = []
        for l in range(fleetsize):
            if (launch_location[tour][l][1] == Locations["Port West"]) or (launch_location[tour][l][1] == Locations["Port MSP"]) or (len(launch_route[tour][l]) == 2):
                not_left.append(l)
        mainQ_tour = mainQ.loc[(mainQ['Start_TW'] <= 540+tour*150) & (
            mainQ['End_TW' >= 540+(tour+1)*150]) & (mainQ.Zone.isin(launch_route[tour][l]))]

        # Solve for launches that have not left in current tour
        _, solutionSet, _, _, _, _, _, _ = calculateRoute(
            len(mainQ_tour)-1, len(not_left), mainQ_tour, None, False)
        r2t = route2Timetable(mainQ_tour, len(not_left), solutionSet, None)

        # Replace timetable for routes that have not left
        for l2 in not_left:
            for j in range(len(raw_Timetable)):
                try:
                    raw_Timetable.iloc[l2, j] = r2t[0][j]
                except:
                    raw_Timetable.iloc[l2, j] = ''

        raw_Timetable.to_csv(os.path.join(
            dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1', index=False)

        # Replace map for routes that have not left
        drawSolution2(raw_Timetable, tour, True)

    # If launch has left
    else:
        # Ignore linehaul request cancellations
        if req_type == 1:
            return 500
        
        # Departure Point launch location
        df = pd.DataFrame(
            [[0, 0, 'launchlocation{}'.format(launch), 0, t_now, t_now+150]], columns=mainQ.columns)
        edge = []
        count = 0
        for r in launch_route[tour][launch]:
            if (r == 'Port West') or (r == 'Port MSP'):
                r_port = r
            else:
                if launch_etd[tour][launch][count] > t_now:
                    df = pd.concat([df, ogQ[(ogQ.Zone == r) & (ogQ.Start_TW >= 540+150*(tour)) & (ogQ.End_TW <= 540+150*(tour+1))]])
                    edge.append(r)
            count+=1

        edge.append(r_port)
        r_port_df = pd.DataFrame(
            [['return', 0, r_port, 0, t_now, t_now+150]], columns=mainQ.columns)
        df = pd.concat([df, r_port_df])
        df = df.reset_index(drop=True)

        launchlocation = {}
        launchlocation[0] = launch_location[tour][launch]
        launchlocation[1] = edge
        # Original departure time is launch_etd[tour][launch][0] // implement only if want the timetable to show port instead of launch location
        launchlocation[2] = t_now
        launchlocation[3] = launch

        _, solutionSet, _, _, _, _, _, _ = calculateRoute(len(df)-1, 1, df, launchlocation, False)
        if solutionSet == None:
            return 500
        else:
            r2t = route2Timetable(df, 1, solutionSet, launchlocation)

        # Replace with new timetable
        for j in range(len(raw_Timetable[0].iloc[0])):
            if j < len(r2t[0]):
                raw_Timetable[0].iloc[launch, j] = r2t[0][j]
            else:
                raw_Timetable[0].iloc[launch, j] = ''

        raw_Timetable[0].to_csv(os.path.join(
            dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1', index=False)

        # Replace map for routes that left
        drawSolution2(raw_Timetable, tour, True)

    mainQ.to_csv(os.path.join(dirName, 'outputs/logs/mainQ.csv'),
                 encoding='latin1', index=False)
    time_taken = time.time() - t_start
    print("Time take: ",time_taken)

def addBookingFn(request_type,zone,passengers,timewindow,t_now,cur_tour):
    # Define variables
    t_start = time.time()
    mainQ, _ = reader('mainQ')
    _, launch_location, launch_etd, launch_route = dynamic(
        'mainQ', fleetsize, t_now)
    
    # Add booking to ogQ - tracks all bookings served and to be served
    if os.path.exists(os.path.join(dirName, 'datasets/ogQ.csv')):
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/ogQ.csv'),
                          encoding='utf-8', on_bad_lines='warn')
    else:
        ogQ = pd.read_csv(os.path.join(
            dirName, 'datasets/{}.csv'.format(file)), encoding='utf-8', on_bad_lines='warn')

    # Create booking data
    newbooking_id = int(ogQ.iloc[-1, 0][11:13]) + 1
    newbooking_df = pd.DataFrame([[datetime.today().strftime('%Y-%m-%d')+'-'+str(newbooking_id),
                                 request_type, zone, passengers, 540+timewindow*150, 540+(timewindow+1)*150]], columns=ogQ.columns)

    ogQ2 = pd.concat([ogQ, newbooking_df])
    ogQ2.to_csv(os.path.join(dirName, 'datasets/ogQ2.csv'),
                encoding='utf-8', index=False)

    # Try adding to customer requested timewindow
    # 1. If timewindow requested is not current tour, add to mainQ for tour and reoptimise. Implement
    if timewindow > cur_tour:
        try:
            schedule('ogQ2', fleetsize, timewindow)
        
        except:
            # if no results
            return False
        
    # 2. Else try current tour but launch that have not left, add to mainQ for tour and reoptimise. Calculate total objective value and increase (ie cost)
    else:
        # Get route for launches that have not left
        not_left = []
        left = []
        options = {}  # {case no.: [r2t, change_in_objFn]}
        for l in range(fleetsize):
            if (launch_location[timewindow][l][1] == Locations["Port West"]) or (launch_location[timewindow][l][1] == Locations["Port MSP"]) or (len(launch_route[timewindow][l]) == 2):
                not_left.append(l)
            else:
                left.append(l)

        if not_left != []:
            case = 1
            options[case] = []
            # Create df for zones served by launches that have not left; excluding new booking ogQ, ogQ2 including
            for l in not_left:
                ogQ_tour = ogQ.loc[(ogQ['Start_TW'] <= 540+timewindow*150) & (ogQ['End_TW'] >= 540+(
                    timewindow+1)*150) & (ogQ.Zone.isin(launch_route[timewindow][l]))]
                if ogQ_tour.empty:
                    # Index [1:3] refers to the zone number
                    if int(zone[1:3]) <= 16:
                        ogQ_tour = pd.DataFrame(
                            [[0, 0, 'Port MSP', 0, 540+timewindow*150, 540+(timewindow+1)*150]], columns=mainQ.columns)
                        ogQ_tour['Port'] = 'MSP'
                    else:
                        ogQ_tour = pd.DataFrame(
                            [[0, 0, 'Port West', 0, 540+timewindow*150, 540+(timewindow+1)*150]], columns=mainQ.columns)
                        ogQ_tour['Port'] = 'West'
                ogQ2_tour = pd.concat([ogQ_tour, newbooking_df])
                ogQ2_tour = ogQ2_tour.reset_index(drop=True)

            # Solve for launches that have not left in current tour
                _, solutionSet, _, objFn2, _, _, _, _ = calculateRoute(
                    len(ogQ2_tour)-1, len(not_left), ogQ2_tour, None, False)
                if objFn2 != None:
                    r2t = route2Timetable(ogQ2_tour, len(
                        not_left), solutionSet, None)
                    options[case].append(r2t)

                    # Calculate change in objFn by calculating objFn of original without new booking
                    _, _, _, objFn, _, _, _, _ = calculateRoute(
                        len(ogQ_tour)-1, len(not_left), ogQ_tour, None, False)
                    if objFn == None:
                        objFn = 0
                    options[case].append(objFn2-objFn)
                    options[case].append(l)

                else:
                    options[case].extend((None, None, None))

    # 3. Then try current tour but launches that left, reoptimise route. Calculate total objective value and increase (ie cost)
        # Only for backhaul requests
        if (len(not_left) != fleetsize) & (request_type == 2):
            case = 2

            # Departure Point launch location
            for launch in left:
                print("Launch", launch)
                options[case] = []
                df = pd.DataFrame(
                    [[0, 0, 'launchlocation{}'.format(launch), 0, t_now, t_now+150]], columns=mainQ.columns)
                edge = []
                for r in launch_route[timewindow][launch]:
                    if (r == 'Port West') or (r == 'Port MSP'):
                        r_port = r
                    else:
                        df = pd.concat([df, ogQ[(ogQ.Zone == r) & (
                            ogQ.Start_TW >= 540+150*(timewindow)) & (ogQ.End_TW <= 540+150*(timewindow+1))]])
                        edge.append(r)
                edge.append(r_port)
                r_port_df = pd.DataFrame(
                    [['Returned', 0, r_port, 0, t_now, t_now+150]], columns=mainQ.columns)
                temp_df = df
                df = pd.concat([df, r_port_df])
                df = df.reset_index(drop=True)
                df2 = pd.concat([temp_df, newbooking_df, r_port_df])
                df2 = df2.reset_index(drop=True)

                launchlocation = {}
                launchlocation[0] = launch_location[timewindow][launch]
                launchlocation[1] = edge
                # Original departure time // launch_etd[timewindow][launch][0]
                launchlocation[2] = t_now
                launchlocation[3] = launch

                _, solutionSet, _, objFn2, _, _, _, _ = calculateRoute(
                    len(df2)-1, 1, df2, launchlocation, False)

                if objFn2 != None:
                    # Have to consider what happens if some zones have already been served
                    r2t = route2Timetable(df2, 1, solutionSet, launchlocation)
                    options[case].append(r2t)

                    # Calculate change in objFn by calculating objFn of original without new booking
                    _, _, _, objFn, _, _, _, _ = calculateRoute(
                        len(df)-1, len(not_left), df, launchlocation, False)
                    if objFn == None:
                        objFn = 0
                    options[case].append(objFn2-objFn)
                    options[case].append(launch)

                else:
                    options[case].extend((None, None, None))

                case += 1

        # Compare all objFn
        min_objFn = float('inf')  # large number
        no_soln = True
        for i in options:
            change = options[i][1]
            print('Case:', i, ', Change:', change, ', Launch', options[i][2])
            if change != None:
                no_soln = False
                if change < min_objFn:
                    min_objFn = change
                    r2t = options[i][0]
                    case_no = i

        if no_soln:
            return False

        # Replace timetable for routes that have not left
        raw_Timetable = convert_to_list(pd.read_csv(os.path.join(
            dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(timewindow)), encoding='latin1'), fleetsize)
        # Create new column
        while len(raw_Timetable[0].iloc[0]) < len(r2t[0]):
            raw_Timetable[0]['{}'.format(len(raw_Timetable[0].iloc[0]))] = ''

        # Original route length + 1 (incorporate new booking) - length of new route; to take into account zones that have been served
        served = len(launch_route[timewindow]
                     [options[case_no][2]]) + 1 - len(r2t[0])
        for j in range(served, len(raw_Timetable[0].loc[0])):
            if j < len(r2t[0]):
                raw_Timetable[0].iloc[options[case_no][2], j] = r2t[0][j]
            else:
                raw_Timetable[0].iloc[options[case_no][2], j] = ''

        raw_Timetable[0].to_csv(os.path.join(
            dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(timewindow)), encoding='latin1', index=False)

        # Replace map
        drawSolution2(raw_Timetable, timewindow, True)

    # Save as mainQ, let dynamic.py handle mainQ dropping
    ogQ2.to_csv(os.path.join(dirName, 'outputs/logs/mainQ.csv'),
                encoding='latin1', index=False)
    ogQ2.to_csv(os.path.join(dirName, 'datasets/ogQ.csv'),
                encoding='utf-8', index=False)
    time_taken = time.time() - t_start
    print("Time take: ", time_taken)
    return True

def drawLaunch(launch_location, tour):
    outputsPlotsDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/img/')
    outputPlot = os.path.join(outputsPlotsDir, 'order_Tour' + str(tour+1) + '_schedule.png')
    if not os.path.exists(os.path.join(dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour))):
        return

    raw_Timetable = convert_to_list(pd.read_csv(os.path.join(dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1'), fleetsize)

    fig, ax = drawSolution2(raw_Timetable, tour, False)
    for i in range(fleetsize):
        ax.scatter(launch_location[tour][i][1][0], launch_location[tour][i][1][1], marker='x', color='r')

    # Save visualisations in a png file
    fig.savefig(outputPlot)
    plt.close('all')

def capacity(timetable,launch_route):
    ogQ_path = os.path.join(dirName, 'datasets/ogQ.csv')
    ogQ2_path = os.path.join(dirName, 'datasets/ogQ2.csv')
    order_path = os.path.join(dirName, 'datasets/order.csv')
    if os.path.exists(ogQ2_path):
        ogQ2 = pd.read_csv(ogQ2_path, encoding='utf-8', on_bad_lines='warn')
    elif os.path.exists(ogQ_path):
        ogQ2 = pd.read_csv(ogQ_path, encoding='utf-8', on_bad_lines='warn')
    else:
        ogQ2 = pd.read_csv(order_path, encoding='utf-8', on_bad_lines='warn')
    
    for tour in launch_route:
        for launch in launch_route[tour]:
            cap = 14 # Max capacity is 14
            linehaul = 0
            count = 0
            for zone in launch_route[tour][launch]:
                if zone != "Port West" and zone != "Port MSP" and zone != "launchlocation{}".format(launch):
                    # Find demand and request type at zone
                    b = ogQ2[(ogQ2.Zone == zone) & (ogQ2.Start_TW >= 540+150*tour) & (ogQ2.End_TW <= 540+150*(tour+1))]
                    if len(b) > 1:
                        b = b.iloc[:1]
                        b_in = ogQ2[ogQ2.Order_ID == b.iloc[0,0]].index
                        ogQ2 = ogQ2.drop(b_in)
                    
                    request_type = b.iloc[0,1]
                    demand = b.iloc[0,3]

                    # Find capacity demand from ogQ2 ie queue that includes new bookings
                    if request_type == 1:
                        cap += demand
                        linehaul += demand
                    else:
                        cap -= demand
                timetable[tour].iloc[launch,count].append(cap)
                count += 1

            # Adjust for linehaul
            for zone in range(len(launch_route[tour][launch])):
                timetable[tour].iloc[launch,zone][3] -= linehaul
    return timetable