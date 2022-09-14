from flask import Flask, render_template, request, redirect
import time as timer

from schedule import schedule
from dynamic import dynamic, reader
import os

# Default global variables
global file, fleetsize, time_now
file = 'order'
fleetsize = 5
time_start = timer.time()/10
time_now = 540

# Run initial optimiser
#schedule(file, fleetsize)

app = Flask(__name__)

def t_now():
    global time_now
    time_now = time_now + timer.time()/10 - time_start
    return time_now

def time_convert(t):
    hr = str(round(t) // 60).rjust(2,'0')
    m = str(round(t) % 60).rjust(2,'0')
    t = ("{}:{}".format(hr,m))
    return t

# Delete mainQ
def delete_mainQ():
    dirName = os.path.dirname(os.path.abspath(__file__))
    mainQ_path = os.path.join(dirName, 'outputs/logs/mainQ.csv')
    if os.path.exists(mainQ_path):
        os.remove(mainQ_path)

@app.route('/', methods=['POST','GET'])
def index():
    return render_template("index.html",time_now=time_convert(t_now()))

@app.route('/timetable', methods=['POST','GET'])
def timetable():
    timetable,_,_, launch_route = dynamic('mainQ',fleetsize,time_now)
    return render_template("timetable.html", timetable=timetable, launch_route=launch_route, time_now=time_convert(t_now()))

@app.route('/location', methods=['POST','GET'])
def location():
    return render_template ("location.html",time_now=time_convert(t_now()))

@app.route('/booking', methods=['POST','GET'])
def booking():
    dynamic('mainQ',fleetsize,time_now)
    mainQ,_,_ = reader('mainQ', fleetsize)
    if mainQ is not None:
        for i in range(len(mainQ)):
            mainQ.iloc[i,0]=int(mainQ.iloc[i,0][11:13]) # Truncate orderId to last 2 digits
        for j in range(len(mainQ.index)):
            mainQ.iloc[j,4] = time_convert(mainQ.iloc[j,4])
            mainQ.iloc[j,5] = time_convert(mainQ.iloc[j,5])
    else:
        pass
    
    return render_template ("booking.html",time_now=time_convert(t_now()), mainQ=mainQ)

@app.route("/restart")
def restart():
    global time_now,time_start
    time_now = 540
    time_start = timer.time()/10
    delete_mainQ()
    return render_template("index.html", time_now=time_convert(time_now))

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
    delete_mainQ()