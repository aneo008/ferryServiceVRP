from flask import Flask, render_template, redirect, request
import time
import os
import pandas as pd

from lpModel import calculateRoute
from schedule import schedule, route2Timetable
from dynamic import dynamic, reader, convert_to_list
from utils import Locations

# Default global variables
global file, fleetsize
file = 'order'
fleetsize = 5
time_start_epoch = time.time()

app = Flask(__name__)

# Run initial optimiser
#schedule(file, fleetsize, None)

# Note this does not account for after 2359hr
def t_now():
    return 540 + time.time() - time_start_epoch
    
def time_convert(t):
    hr = str(round(t) // 60).rjust(2,'0')
    m = str(round(t) % 60).rjust(2,'0')
    t = ("{}:{}".format(hr,m))
    return t

def find_tour_launch(zone,launch_route):
    for tour in range(len(launch_route)):
        for launch in range(len(launch_route[tour])):
            for z in range(len(launch_route[tour][launch])):
                if launch_route[tour][launch][z] == zone:
                    return tour, launch
                else:
                    continue
    return None, None

def cur_tour():
    for i in range(4):
        if t_now() <= 540+(i+1)*150:
            return i  

# Delete mainQ
def delete_Q():
    dirName = os.path.dirname(os.path.abspath(__file__))
    mainQ_path = os.path.join(dirName, 'outputs/logs/mainQ.csv')
    ogQ_path = os.path.join(dirName, 'datasets/ogQ.csv')
    if os.path.exists(mainQ_path):
        os.remove(mainQ_path)
    if os.path.exists(ogQ_path):
        os.remove(ogQ_path)

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
    mainQ,_,_ = reader('mainQ', fleetsize)
    if mainQ is not None:
        for i in range(len(mainQ)):
            try:
                mainQ.iloc[i,0]=int(mainQ.iloc[i,0][11:13]) # Truncate orderId to last 2 digits
            except: # Already truncated
                continue
        for j in range(len(mainQ.index)):
            mainQ.iloc[j,4] = time_convert(mainQ.iloc[j,4])
            mainQ.iloc[j,5] = time_convert(mainQ.iloc[j,5])
    else:
        pass
    
    return render_template ("booking.html",time_now=time_convert(t_now()), mainQ=mainQ)

@app.route('/delete',methods=['POST'])
def delete():
    mainQ,_,_ = reader('mainQ', fleetsize)
    _,launch_location,_,launch_route = dynamic('mainQ',fleetsize,t_now())
    id = int(request.form.get("bookingid"))
    b_id = mainQ.iloc[id,0]
    zone = mainQ.iloc[id,2]
    tour,launch = find_tour_launch(zone,launch_route)
    if tour == None:
        return render_template('500.html'), 500
    dirName = os.path.dirname(os.path.abspath(__file__))
    raw_Timetable = convert_to_list(pd.read_csv(os.path.join(dirName,'outputs/logs/raw_Timetable_{}.csv'.format(tour)),encoding='latin1'),1,fleetsize)

    # Remove booking from ogQ - tracks all bookings served and to be served
    if not os.path.exists(os.path.join(dirName, 'datasets/ogQ.csv')):
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/{}.csv'.format(file)), encoding='utf-8', on_bad_lines='warn')
    else:
        ogQ = pd.read_csv(os.path.join(dirName, 'datasets/ogQ.csv'), encoding='utf-8', on_bad_lines='warn')
    ogQ = ogQ[ogQ.Order_ID != b_id]
    ogQ.to_csv(os.path.join(dirName, 'datasets/ogQ.csv'), encoding='utf-8', index=False)

    # Remove booking from mainQ - tracks all bookings to be served
    mainQ=mainQ[mainQ.Order_ID != b_id]
    mainQ.to_csv(os.path.join(dirName, 'outputs/logs/mainQ.csv'), encoding='latin1',index=False)
    
    # Remove booking from raw_Timetable
    for rd in range(len(raw_Timetable.iloc[launch])):
        try:
            if raw_Timetable.iloc[launch,rd][0] == zone:
                raw_Timetable.drop([rd])
        except:
            continue

    # If deleted request is from upcoming tour
    if tour > cur_tour():
        schedule('ogQ',fleetsize,tour)
    # If launch has not left
    elif (launch_location[tour][launch][1] == Locations["Port West"]) or (launch_location[tour][launch][1] == Locations["Port MSP"]):
        # Get route for launches that have not left
        not_left = []
        for l in fleetsize:
            if (launch_location[tour][l][1] == Locations["Port West"]) or (launch_location[tour][l][1] == Locations["Port MSP"]) or (len(launch_route[tour][l])==2):
                not_left.append(l)
        mainQ_tour = mainQ.loc[(mainQ['Start_TW']<=540+tour*150)&(mainQ['End_TW'>=540+(tour+1)*150])]
        
        # Solve for launches that have not left in current tour
        _, solutionSet, _, _, _, _, _,_ = calculateRoute(len(mainQ_tour)-1, len(not_left), mainQ_tour, None, False)
        r2t = route2Timetable(df, 1, solutionSet, launchlocation)
        
        # Replace timetable for routes that have not left
        for l2 in not_left:
            for j in range(len(raw_Timetable)):
                try:
                    raw_Timetable.iloc[l2,j] = r2t[0][j]
                except:
                    raw_Timetable.iloc[l2,j] = ''

        # Replace map for routes that have not left
        
    # If launch has left
    else:
        # Departure Point launch location
        df = pd.DataFrame([[0, 0, 'launchlocation', 0, t_now(), t_now()+150]],columns=mainQ.columns) 
        edge = []
        for r in launch_route[tour][launch]:
            try:
                df = pd.concat([df,mainQ[mainQ.Zone == r]])
                edge.append(r)
            except:
                continue
        df = df.reset_index(drop=True)

        launchlocation = {}
        launchlocation[0] = launch_location[tour][launch]
        launchlocation[1] = edge
        _, solutionSet, _, _, _, _, _,_ = calculateRoute(len(df)-1, 1, df,launchlocation, False)
        r2t = route2Timetable(df, 1, solutionSet, launchlocation)

        for j in range(len(raw_Timetable)):
            try:
                raw_Timetable.iloc[rd,j] = r2t[0][j]
            except:
                raw_Timetable.iloc[rd,j] = ''
    
        raw_Timetable.to_csv(os.path.join(dirName,'outputs/logs/raw_Timetable_{}.csv'.format(tour)), encoding='latin1',index=False)

    return redirect('/booking')

@app.route("/add_ten",methods=['POST'])
def add_ten():
    global time_start_epoch
    time_start_epoch -= 5
    return redirect ('/booking')

@app.route("/restart",methods=['POST'])
def restart():
    schedule(file, fleetsize,None)
    global time_start_epoch
    time_start_epoch = time.time()
    delete_Q()
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