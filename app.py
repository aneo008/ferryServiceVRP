from ctypes.wintypes import LARGE_INTEGER
from flask import Flask, render_template, redirect, request
import time
from datetime import datetime
import os
import numpy as np
import pandas as pd
import shutil

from lpModel import calculateRoute
from schedule import schedule, route2Timetable
from dynamic import dynamic, reader, convert_to_list
from utils import Locations

# Default global variables
global file, fleetsize, time_start_epoch
file = 'order'
fleetsize = 5
time_start_epoch = int(time.time())

# Run Scheduler
schedule(file, fleetsize, None)

app = Flask(__name__)

# Note this does not account for after 2359hr
''' 
t_now: what does it do
'''
def t_now():
    return 540 + int(time.time()) - time_start_epoch
    
def time_convert(t):
    hr = str(round(t) // 60).rjust(2,'0')
    m = str(round(t) % 60).rjust(2,'0')
    t = ("{}:{}".format(hr,m))
    return t

def find_tour_launch(zone,launch_route,tw):
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

def cur_tour():
    for i in range(4):
        if t_now() <= 540+(i+1)*150:
            return i  

# Delete mainQ
def delete_Q():
    dirName = os.path.dirname(os.path.abspath(__file__))
    logs_path = os.path.join(dirName, 'outputs/logs')
    mainQ_path = os.path.join(logs_path, 'mainQ.csv')
    ogQ_path = os.path.join(dirName, 'datasets/ogQ.csv')
    img_path = os.path.join(dirName, 'static/img')

    if os.path.exists(mainQ_path):
        os.remove(mainQ_path)
    if os.path.exists(ogQ_path):
        os.remove(ogQ_path)

    for i in range(4):
        # Remove raw_Timetable file if no more orders in that tour
        rawtt_path = os.path.join(os.path.join(dirName,'outputs/logs/raw_Timetable_{}.csv'.format(i)))
        if os.path.exists(rawtt_path):
            os.remove(rawtt_path)

    # Reset maps
    anchorage_map = os.path.join(dirName,"Port_Of_Singapore_Anchorages_Chartlet.png")
    for i in range(4):
        map_path = os.path.join(img_path,file + '_Tour{}'.format(i+1)+ '_schedule.png')
        shutil.copy(anchorage_map, map_path)

@app.route('/', methods=['POST','GET'])
def index():
    timetable,_,_, launch_route = dynamic('mainQ',fleetsize,t_now())
    return render_template("index.html", timetable=timetable[cur_tour()], launch_route=launch_route[cur_tour()],time_now=time_convert(t_now()))

@app.route('/timetable', methods=['POST','GET'])
def timetable():
    timetable,_,_, launch_route = dynamic('mainQ',fleetsize,t_now())
    return render_template("timetable.html", timetable=timetable, launch_route=launch_route, time_now=time_convert(t_now()))

@app.route('/location', methods=['POST','GET'])
def location():
    _,launch_location,launch_etd,_ = dynamic('mainQ',fleetsize,t_now())
    return render_template ("location.html",time_now=time_convert(t_now()),launch_location=launch_location,launch_etd = launch_etd)

@app.route('/booking', methods=['POST','GET'])
def booking():
    dynamic('mainQ',fleetsize,t_now())
    mainQ,_ = reader('mainQ', fleetsize)
    mainQ2=[]
    if mainQ is not None:
        for i in range(len(mainQ)):
            try:
                mainQ.iloc[i,0]=int(mainQ.iloc[i,0][11:13]) # Truncate orderId to last 2 digits
            except: # Already truncated
                continue
        for j in range(len(mainQ.index)):
            mainQ.iloc[j,4] = time_convert(mainQ.iloc[j,4])
            mainQ2.append(mainQ.iloc[j,5])
            mainQ.iloc[j,5] = time_convert(mainQ.iloc[j,5])
    else:
        pass
    
    return render_template ("booking.html",time_now=time_convert(t_now()), mainQ=mainQ, mainQ2=mainQ2, tour=cur_tour())

@app.route('/delete',methods=['POST'])
def delete():
    # Define variables
    mainQ,_ = reader('mainQ', fleetsize)
    _,launch_location,launch_etd,launch_route = dynamic('mainQ',fleetsize,t_now())
    id = int(request.form.get("bookingid"))
    b_id = mainQ.iloc[id,0]
    zone = mainQ.iloc[id,2]
    tw = mainQ.iloc[id,5]
    tour,launch = find_tour_launch(zone,launch_route,tw)

    if tour == None:
        return render_template('500.html'), 500
    dirName = os.path.dirname(os.path.abspath(__file__))
    raw_Timetable = convert_to_list(pd.read_csv(os.path.join(dirName,'outputs/logs/raw_Timetable_{}.csv'.format(tour)),encoding='latin1'),1,fleetsize)

    # Remove booking from ogQ - tracks all bookings served and to be served
    if os.path.exists(os.path.join(dirName, 'datasets/ogQ.csv')):
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/ogQ.csv'), encoding='utf-8', on_bad_lines='warn')
    else:
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format(file)), encoding='utf-8', on_bad_lines='warn')
    ogQ = ogQ[ogQ.Order_ID != b_id]
    ogQ.to_csv(os.path.join(dirName, 'datasets/ogQ.csv'), encoding='utf-8', index=False)

    # Remove booking from mainQ - tracks all bookings to be served
    mainQ=mainQ[mainQ.Order_ID != b_id]

    # Remove booking from route
    launch_route[tour][launch].remove(zone)

    # If deleted request is from upcoming tour
    if tour > cur_tour():
        schedule('ogQ',fleetsize,tour)

    # If launch has not left
    elif (launch_location[tour][launch][1] == Locations["Port West"]) or (launch_location[tour][launch][1] == Locations["Port MSP"]):
        # Get route for launches that have not left
        not_left = []
        for l in range(fleetsize):
            if (launch_location[tour][l][1] == Locations["Port West"]) or (launch_location[tour][l][1] == Locations["Port MSP"]) or (len(launch_route[tour][l])==2):
                not_left.append(l)
        mainQ_tour = mainQ.loc[(mainQ['Start_TW']<=540+tour*150)&(mainQ['End_TW'>=540+(tour+1)*150])&(mainQ.Zone.isin(launch_route[tour][l]))]
        
        # Solve for launches that have not left in current tour
        _, solutionSet, _, _, _, _, _,_ = calculateRoute(len(mainQ_tour)-1, len(not_left), mainQ_tour, None, False)
        r2t = route2Timetable(mainQ_tour, len(not_left), solutionSet, None)
        
        # Replace timetable for routes that have not left
        for l2 in not_left:
            for j in range(len(raw_Timetable)):
                try:
                    raw_Timetable.iloc[l2,j] = r2t[0][j]
                except:
                    raw_Timetable.iloc[l2,j] = ''
        
        raw_Timetable.to_csv(os.path.join(dirName,'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1',index=False)

        # Replace map for routes that have not left
        
        
    # If launch has left
    else:
        # Departure Point launch location
        df = pd.DataFrame([[0, 0, 'launchlocation', 0, t_now(), t_now()+150]],columns=mainQ.columns) 
        edge = []
        for r in launch_route[tour][launch]:
            if (r == 'Port West') or (r == 'Port MSP'):
                r_port = r
            else:
                df = pd.concat([df,ogQ[(ogQ.Zone == r)&(ogQ.Start_TW>=540+150*(tour))&(ogQ.End_TW<=540+150*(tour+1))]])
                edge.append(r)
        edge.append(r_port)
        r_port_df = pd.DataFrame([['return', 0, r_port, 0, t_now(), t_now()+150]],columns=mainQ.columns) 
        df = pd.concat([df,r_port_df])
        df = df.reset_index(drop=True)

        launchlocation = {}
        launchlocation[0] = launch_location[tour][launch]
        launchlocation[1] = edge
        launchlocation[2] = launch_etd[tour][launch][0] # Original departure time
        _, solutionSet, _, _, _, _, _,_ = calculateRoute(len(df)-1, 1, df,launchlocation, False)
        if solutionSet == None:
            return render_template('500.html'), 500
        else:
            r2t = route2Timetable(df, 1, solutionSet, launchlocation)

        # Replace with new timetable
        for j in range(len(raw_Timetable.iloc[0])):
            if j<len(r2t[0]):
                raw_Timetable.iloc[launch,j] = r2t[0][j]
            else:
                raw_Timetable.iloc[launch,j] = ''
    
        raw_Timetable.to_csv(os.path.join(dirName,'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1',index=False)


    mainQ.to_csv(os.path.join(dirName, 'outputs/logs/mainQ.csv'), encoding='latin1',index=False)

    return redirect('/booking')

@app.route("/add_ten",methods=['POST'])
def add_ten():
    global time_start_epoch
    time_start_epoch -= 5
    return redirect ('/booking')

@app.route('/newbooking')
def newbooking():
    return render_template("newbooking.html",time_now=time_convert(t_now()),Locations=Locations, cur_tour = cur_tour())

@app.route('/addbooking', methods=['POST'])
def addbooking():
    # Define variables
    mainQ, _ = reader('mainQ', fleetsize)
    _,launch_location,launch_etd,launch_route = dynamic('mainQ',fleetsize,t_now())
    request_type = int(request.form.get("request"))
    if request_type == 1:
        request_type2 = 'Linehaul'
    else:
        request_type2 = 'Backhaul'
    zone = request.form.get("zone")
    passengers = int(request.form.get("passengers"))
    timewindow = int(request.form.get("timewindow"))
    timewindow2 = time_convert(540+timewindow*150) + ' - ' + time_convert(540+(timewindow+1)*150)
    user_ip = [request_type2, zone, passengers, timewindow2]

    dirName = os.path.dirname(os.path.abspath(__file__))   
    
    # Add booking to ogQ - tracks all bookings served and to be served
    if os.path.exists(os.path.join(dirName, 'datasets/ogQ.csv')):
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/ogQ.csv'), encoding='utf-8', on_bad_lines='warn')
    else:
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format(file)), encoding='utf-8', on_bad_lines='warn')

    # Create booking data
    newbooking_id = int(ogQ.iloc[-1, 0][11:13]) + 1
    newbooking_df = pd.DataFrame([[datetime.today().strftime('%Y-%m-%d')+'-'+str(newbooking_id), request_type, zone, passengers, 540+timewindow*150, 540+(timewindow+1)*150]],columns=ogQ.columns)
    
    ogQ2 = pd.concat([ogQ, newbooking_df])
    ogQ2.to_csv(os.path.join(dirName, 'datasets/ogQ2.csv'),
                encoding='utf-8', index=False)

    # Try adding to customer requested timewindow
    # 1. If timewindow requested is not current tour, add to mainQ for tour and reoptimise. Implement
    if timewindow > cur_tour():
        try:
            schedule('ogQ2',fleetsize,timewindow)
        except:
            # if no results
            return render_template("addbooking.html",time_now=time_convert(t_now()), user_ip=user_ip, success = False)

    # 2. Else try current tour but launch that have not left, add to mainQ for tour and reoptimise. Calculate total objective value and increase (ie cost)
    else:
        # Get route for launches that have not left
        not_left = []
        left = []
        options = {} # {case no.: [r2t, change_in_objFn]}
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
                ogQ_tour = ogQ.loc[(ogQ['Start_TW'] <= 540+timewindow*150) & (ogQ['End_TW'] >= 540+(timewindow+1)*150) & (ogQ.Zone.isin(launch_route[timewindow][l]))]
                if ogQ_tour.empty:
                    # Index [1:3] refers to the zone number
                    if int(zone[1:3]) <= 16:
                        ogQ_tour = pd.DataFrame([[0, 0, 'Port MSP', 0, 540+timewindow*150, 540+(timewindow+1)*150]], columns=mainQ.columns)
                        ogQ_tour['Port'] = 'MSP'
                    else:
                        ogQ_tour = pd.DataFrame([[0, 0, 'Port West', 0, 540+timewindow*150, 540+(timewindow+1)*150]], columns=mainQ.columns)
                        ogQ_tour['Port'] = 'West'
                ogQ2_tour = pd.concat([ogQ_tour, newbooking_df])
                ogQ2_tour = ogQ2_tour.reset_index(drop=True)

            # Solve for launches that have not left in current tour
                _, solutionSet, _, objFn2, _, _, _, _ = calculateRoute(len(ogQ2_tour)-1, len(not_left), ogQ2_tour, None, False)
                if objFn2 != None:
                    r2t = route2Timetable(ogQ2_tour, len(not_left), solutionSet, None)
                    options[case].append(r2t)
                    
                    # Calculate change in objFn by calculating objFn of original without new booking
                    _, _, _, objFn, _, _, _, _ = calculateRoute(len(ogQ_tour)-1, len(not_left), ogQ_tour, None, False)
                    if objFn == None:
                        objFn = 0
                    options[case].append(objFn2-objFn)
                    options[case].append(l)
                
                else: 
                    options[case].extend((None,None,None))

    # 3. Then try current tour but launches that left, reoptimise route. Calculate total objective value and increase (ie cost)
        # Only for backhaul requests
        if (len(not_left) != fleetsize) & (request_type == 2):
            case = 2
            
            # Departure Point launch location
            for launch in left:   
                print("Launch",launch)
                options[case] = []
                df = pd.DataFrame([[0, 0, 'launchlocation', 0, t_now(), t_now()+150]], columns=mainQ.columns)
                edge = []
                for r in launch_route[timewindow][launch]:
                    if (r == 'Port West') or (r == 'Port MSP'):
                        r_port = r
                    else:
                        df = pd.concat([df, ogQ[(ogQ.Zone == r) & (ogQ.Start_TW >= 540+150*(timewindow)) & (ogQ.End_TW <= 540+150*(timewindow+1))]])
                        edge.append(r)
                edge.append(r_port)
                r_port_df = pd.DataFrame(
                    [['Returned', 0, r_port, 0, t_now(), t_now()+150]], columns=mainQ.columns)
                temp_df = df
                df = pd.concat([df, r_port_df])
                df = df.reset_index(drop=True)
                df2 = pd.concat([temp_df,newbooking_df,r_port_df])
                df2 = df2.reset_index(drop=True)

                launchlocation = {}
                launchlocation[0] = launch_location[timewindow][launch]
                launchlocation[1] = edge
                # Original departure time
                launchlocation[2] = launch_etd[timewindow][launch][0]
                _, solutionSet, _, objFn2, _, _, _, _ = calculateRoute(len(df2)-1, 1, df2, launchlocation, False)
                
                if objFn2 != None:
                    # Have to consider what happens if some zones have already been served
                    r2t = route2Timetable(df2, 1, solutionSet, launchlocation)
                    options[case].append(r2t)

                    # Calculate change in objFn by calculating objFn of original without new booking
                    _, _, _, objFn, _, _, _, _ = calculateRoute(len(df)-1, len(not_left), df, launchlocation, False)
                    if objFn == None:
                        objFn = 0
                    options[case].append(objFn2-objFn)
                    options[case].append(launch)

                else:
                    options[case].extend((None, None, None))
                
                case += 1

        # Compare all objFn
        min_objFn = float('inf') # large number
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
            return render_template("addbooking.html", time_now=time_convert(t_now()), user_ip=user_ip, success=False)
        
        # Replace timetable for routes that have not left
        raw_Timetable = convert_to_list(pd.read_csv(os.path.join(
            dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(timewindow)), encoding='latin1'), 1, fleetsize)
        # Create new column
        while len(raw_Timetable.iloc[0]) < len(r2t[0]):
            raw_Timetable['{}'.format(len(raw_Timetable.iloc[0]))] = ''

        # Original route length + 1 (incorporate new booking) - length of new route; to take into account zones that have been served
        served = len(launch_route[timewindow][options[case_no][2]]) + 1 - len(r2t[0])
        for j in range(served,len(raw_Timetable.loc[0])):
            if j<len(r2t[0]):
                raw_Timetable.iloc[options[case_no][2], j] = r2t[0][j]
            else:
                raw_Timetable.iloc[options[case_no][2], j] = ''
        
        raw_Timetable.to_csv(os.path.join(dirName, 'outputs/logs/raw_Timetable_{}.csv'.format(timewindow)), encoding='latin1', index=False)
            

    # Replace map

    # Except if all no solution, tell customer choose another timewindow

    # For 2. and 3., Implement option with lowest increase in objective value (ie cost)

    # Save as mainQ, let dynamic.py handle mainQ dropping
    ogQ2.to_csv(os.path.join(dirName, 'outputs/logs/mainQ.csv'), encoding='latin1',index=False)
    ogQ2.to_csv(os.path.join(dirName, 'datasets/ogQ.csv'), encoding='utf-8', index=False)

    return render_template("addbooking.html",time_now=time_convert(t_now()), user_ip=user_ip, success=True)

@app.route("/restart",methods=['POST'])
def restart():
    delete_Q()
    # Run initial optimiser
    schedule(file, fleetsize, None)
    global time_start_epoch
    time_start_epoch = int(time.time())
    return redirect('/')

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)
    delete_Q()