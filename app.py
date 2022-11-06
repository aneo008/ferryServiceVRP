from flask import Flask, render_template, redirect, request
import time

from schedule import schedule
from dynamic import dynamic, reader
from utils import Locations
from appTools import time_convert,delete_Q,deleteBooking,addBookingFn,drawLaunch,capacity,file,fleetsize

# Default global variables
global time_start_epoch
time_start_epoch = int(time.time())

# Run Scheduler
#schedule(file, fleetsize, None)

app = Flask(__name__)

# Note this does not account for after 2359hr
# Divide by 4 so 1 min in timer = 4s irl
def t_now():
    return 540 + (int(time.time()) - time_start_epoch)/4
    
def cur_tour():
    for i in range(4):
        if t_now() <= 540+(i+1)*150:
            return i  

@app.route('/', methods=['POST','GET'])
def index():
    timetable,_,_, launch_route = dynamic('mainQ',fleetsize,t_now())
    return render_template("index.html", timetable=timetable[cur_tour()], launch_route=launch_route[cur_tour()],time_now=time_convert(t_now()))

@app.route('/timetable', methods=['POST','GET'])
def timetable():
    timetable,_,_, launch_route = dynamic('mainQ',fleetsize,t_now())
    timetable = capacity(timetable,launch_route)
    return render_template("timetable.html", timetable=timetable, launch_route=launch_route, time_now=time_convert(t_now()))

@app.route('/location', methods=['POST','GET'])
def location():
    _,launch_location,launch_etd,_ = dynamic('mainQ',fleetsize,t_now())
    drawLaunch(launch_location, cur_tour())
    return render_template ("location.html",time_now=time_convert(t_now()),launch_location=launch_location,launch_etd = launch_etd)

@app.route('/booking', methods=['POST','GET'])
def booking():
    dynamic('mainQ',fleetsize,t_now())
    mainQ,_ = reader('mainQ')
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
    id = int(request.form.get("bookingid"))
    err = deleteBooking(id, t_now(), cur_tour())
    if err == 500:
        return render_template('500.html'), 500
    return redirect('/booking')

@app.route("/add_ten",methods=['POST'])
def add_ten():
    global time_start_epoch
    time_start_epoch -= 5*4 # same as t_now factor
    return redirect ('/booking')

@app.route('/newbooking')
def newbooking():
    return render_template("newbooking.html",time_now=time_convert(t_now()),Locations=Locations, cur_tour = cur_tour())

@app.route('/addbooking', methods=['POST'])
def addbooking():
    request_type = int(request.form.get("request"))
    if request_type == 2:
        request_type2 = 'Linehaul'
    else:
        request_type2 = 'Backhaul'
    zone = request.form.get("zone")
    passengers = int(request.form.get("passengers"))
    timewindow = int(request.form.get("timewindow"))
    timewindow2 = time_convert(540+timewindow*150) + ' - ' + time_convert(540+(timewindow+1)*150)
    user_ip = [request_type2, zone, passengers, timewindow2]

    success = addBookingFn(request_type, zone, passengers,
                           timewindow, t_now(), cur_tour())

    return render_template("addbooking.html",time_now=time_convert(t_now()), user_ip=user_ip, success=success)

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