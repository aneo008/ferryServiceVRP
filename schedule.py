import argparse
import matplotlib
matplotlib.use('SVG')
import matplotlib.pyplot as plt
import os
import shutil
import pandas as pd
import time as timer

from lpModel import calculateRoute
from lpTools import drawSolution
from utils import MapGraph, computeDistMatrix, computeDistMatrix2, separateTasks

##############################################################################################
#---------------------------------df format---------------------------------------------------
# | Order_ID         |     Request_Type    |    Zone   | Demand |    Start_TW   |    End_TW  | 
# | YYYY-MM-DD-ID    | 1-pickup 2-delivery | Zone Name | Amount | TourStart <=  x <= TourEnd |
##############################################################################################

# Convert minutes to time
def minutes2Time(minutes):
    return str(int(minutes//60))+':'+ str(int(minutes%60))

# Print table to file
def printTable(table,f):
    for i in range(7):
        line = ''
        try:
            for j in range(7):
                try:
                    line += str(table[j][i][0])
                    line += ','
                    if table[j][i][1] == 'NA':
                        line+='NA'
                    else:
                        line += minutes2Time(table[j][i][1])
                    line += ','
                    if table[j][i][2] == 'NA':
                        line+='NA'
                    else:
                        line += minutes2Time(table[j][i][2])
                    line += ','
                except IndexError or KeyError or TypeError:
                    line += ',,,'
            print(line, file = f)
        except IndexError or KeyError or TypeError:
            pass

# Organise routes in a timetable
def route2Timetable(df, fleetsize, solutionSet, launchlocation):
    if launchlocation == None:
        distMatrix = computeDistMatrix(df, MapGraph)
        start_time = df.iloc[0,4] # Start Time
    elif launchlocation[1] == None:
        distMatrix = computeDistMatrix(df, MapGraph)
        start_time = launchlocation[2]  # Start Time
    else:
        distMatrix = computeDistMatrix2(df, launchlocation)
        start_time = launchlocation[2] # Start Time
    
    route_set=[] # Set of routes
    links = [] # List of edges in all routes
    locations = [] # Locations column
    arrival_time = [] # Arrival Time column
    departure_time = [] # Departure Time column
    timetable = [] # Timetable

    # All Routes
    for i in range(fleetsize):
        temp_list = []
        for j in range(len(solutionSet)):
            if solutionSet[j][2] == i+1:
                temp_list.append(solutionSet[j])
        route_set.append(temp_list)

    # All links
    for i in range(len(route_set)):
        temp_link = []
        start = 0
        for j in range(len(route_set[i])):
            for k in range(len(route_set[i])):
                if route_set[i][k][0]== start:
                    end=route_set[i][k][1]
                    temp_link.append(end)
                    start = end
                    break
        links.append(temp_link)
    
    # Populate Location, Arrival and Departure columns
    for i in range(len(links)):
        temp_location = []
        temp_arrival = []
        temp_departure = []

        if launchlocation == None:
            if df['Port'][0]=='West':
                temp_location.append('Port West')
            else:
                temp_location.append('Port MSP')
        elif launchlocation[1] == None:
            # port launches are from
            temp_location.append(launchlocation[0][i])
        else:
            temp_location.append('launchlocation{}'.format(launchlocation[3]))
            '''
            if df['Zone'][len(links[i])]=='Port West':
                temp_location.append('Port West')
            else:
                temp_location.append('Port MSP')
            '''
        temp_arrival.append('NA') # Departure only (First Node)
        temp_departure.append(start_time)
        last_time = int(start_time)

        # Tracks the location, arrival and departure times for each row
        for j in range(len(links[i])):
            if links[i][j] != 0:
                temp_location.append(df['Zone'][links[i][j]])
                travel_time = round(distMatrix[links[i][j]][links[i][j-1]]/0.463)
                temp_arrival.append(travel_time+last_time)
                temp_departure.append(travel_time+df['Demand'][links[i][j]]+last_time)
                last_time += travel_time+df['Demand'][links[i][j]]
            # For case where timetable only has launch location and port, there would only be one link ie launch-port
            if (len(links[i]) == 1) & (links[i][j] != 0):
                temp_location.append(df['Zone'][links[i][j]])
                travel_time = round(distMatrix[links[i][j]][2]/0.463)
                temp_arrival.append(travel_time+last_time)
                temp_departure.append(
                    travel_time+df['Demand'][links[i][j]]+last_time)
                last_time += travel_time+df['Demand'][links[i][j]]

        if launchlocation == None:
            if df['Port'][0]=='West':
                temp_location.append('Port West')
            else:
                temp_location.append('Port MSP')
        elif launchlocation[1] == None:
            # port launches are from
            temp_location.append(launchlocation[0][i])
        else:
            temp_departure = temp_departure[:-1]
        travel_time = round(distMatrix[links[i][j]][links[i][j-1]]/0.463)
        temp_arrival.append(travel_time+last_time)
        last_time += travel_time+df['Demand'][links[i][j]]
        temp_departure.append('NA') # Arrival Only (Last Node)

        locations.append(temp_location)
        arrival_time.append(temp_arrival)
        departure_time.append(temp_departure)
    
    # Populate timetable
    # Check if there are any solution that are feasible and within time window. Otherwise no solution
    tw_fail = True
    for i in range(len(locations)):
        # Check if arrival time back at port is passed time window
        if launchlocation != None:
            
            # Check if it is only port and port, which would show [NA,time]
            if len(arrival_time[i]) == 2:
                continue
            if arrival_time[i][-2] > 540 + 150*(launchlocation[3]+1):
                print("Arrival for Launch",i, "is ", arrival_time[i][-1], ", which is passed time window")
            else:
                tw_fail = False
            
        if (launchlocation != None) & tw_fail:
            return False

        temp_table = []
        for j in range(len(locations[i])):
            temp_table.append([locations[i][j], arrival_time[i][j], departure_time[i][j]])
        timetable.append(temp_table)
    
    # For case where timetable only has launch location and port, 2nd entry would have same arrival and departure
    if (launchlocation != None):
        if (timetable[0][1][1] == timetable[0][1][2]):
            del timetable[0][1]

    return timetable

def schedule(file,fleet,tour_ip):
    # Start timer
    time_start = timer.time()

    # Directory and File name
    dirName = os.path.dirname(os.path.abspath(__file__))
    fileName = os.path.join(dirName, 'datasets', file + '.csv')
    
    # Outputs directory
    outputsDir = os.path.join(dirName, 'outputs')
    outputsPlotsDir = os.path.join(outputsDir, 'plots','schedule')
    if not os.path.exists(outputsPlotsDir):
        os.mkdir(outputsPlotsDir)
    outputsLogsDir = os.path.join(outputsDir, 'logs')
    if not os.path.exists(outputsLogsDir):
        os.mkdir(outputsLogsDir)

    # Results csv file
    resultsFile = os.path.join(outputsLogsDir,'schedule.csv')
    f = open(resultsFile, 'w+')

    # Headers of csv file

    launch_string = "Launch "
    header_string = "Location,Arrival,Departure,"
    f_write_string_1 = ""
    f_write_string_2 = ""

    for i in range(fleet):
        f_write_string_1 += launch_string + str(i+1) +",,,"
        f_write_string_2 += header_string
    else:
        f_write_string_1 += "\n"
        f_write_string_2 += "\n"
    f.write(f_write_string_1)
    f.write(f_write_string_2)

    # Orders dataset
    print('Reading orders dataset...')
    order_df = pd.read_csv(fileName, encoding='latin1', on_bad_lines='warn')
    order_df = order_df.sort_values(by=['Start_TW','End_TW'])

    # Anchorage map
    img = plt.imread("Port_Of_Singapore_Anchorages_Chartlet.png")

    # New 'Port' column
    print('Performing data preprocessing...')
    port = []
    for i in range(len(order_df)):
        order_df.iloc[i,0]=int(order_df.iloc[i,0][11:13]) # Truncate orderId to last 2 digits
        if int(order_df.iloc[i,2][1:3])<=16: # Index [1:3] refers to the zone number
            port.append('MSP')
        else:
            port.append('West') # Zones 1-16 belong to Marina South Pier, while Zones 17-30 belong to West Coast Pier 
    order_df['Port']=port

    # Split the orders according to tours, also ignores orders with unfeasible time windows
    tours = [(540,690), (690,840), (840,990), (990,1140)] # 0900-1130, 1130-1400, 1400-1630, 1630-1900
    df_tours = []
    i=1
    for tour in tours:
        df = order_df[(order_df['Start_TW'] >= tour[0]) & (order_df['End_TW'] <= tour[1])]
        if not df.empty: # Store tour
            df_tours.append((tour,df)) 

    print('End of data preprocessing.\n')

    # Optimise the schedule of each tour
    print('Beginning optimisation...\n')
    objFn = {}
    for i in range(len(df_tours)):
        fig, ax = plt.subplots()
        ax.imshow(img)
        
        if tour_ip != None:
            # Modify which tour the program is processing, only for optimisation of next time window booking / cancellation
            for j in range(len(df_tours)):
                if df_tours[j][0][0] == 540 + 150*tour_ip:
                    i=j
        df_MSP, fleetsize_MSP, df_West, fleetsize_West = separateTasks(df_tours[i], fleet)
        
        if tour_ip != None:
            i = tour_ip

        print('Tour {}'.format(i+1))

        # Perform LP
        _, solutionSet_West, _, cost1, _, _, _,_ = calculateRoute(len(df_West)-1, fleetsize_West, df_West, None, False) 
        _, solutionSet_MSP, _, cost2, _, _, _, _= calculateRoute(len(df_MSP)-1, fleetsize_MSP, df_MSP, None, False)     

        # Draw and visualise solutions
        drawSolution(solutionSet_West, df_West, ax)
        drawSolution(solutionSet_MSP, df_MSP, ax)
        print('Drawing solutions')
        # print(df_West)
        # plt.show() 

        # Save visualisations in a png file
        # outputPlot = os.path.join(outputsPlotsDir,file + '_' + 'Tour' + str(i+1) + '_schedule.png')
        outputPlot = os.path.join(dirName,'static/img/order_Tour' + str(i+1) + '_schedule.png')
        fig.savefig(outputPlot)
        print('Saved visualisation map as {}'.format(outputPlot))

        # Organise routes in timetables
        table_West = route2Timetable(df_West, fleetsize_West, solutionSet_West, None)  
        table_MSP = route2Timetable(df_MSP, fleetsize_MSP, solutionSet_MSP, None)
        
        # Consolidate both West and MSP timetables
        for j in range(len(table_MSP)):
            table_West.append(table_MSP[j])

        # Write consolidated timetable to csv file
        tt_df = pd.DataFrame(table_West)
        tt_df.to_csv(os.path.join(outputsLogsDir,'raw_Timetable_{}.csv'.format(i)), encoding='latin1',index=False)

        objFn[i] = [cost1,cost2]
        
        printTable(table_West,f)
        print('Wrote timetable to {}\n'.format(resultsFile))

        if tour_ip != None:
            break

    f.close()
    plt.close('all')
    print('Finished optimisation.\n')

    # End timer
    time_end = timer.time()
    total_time = time_end - time_start

    print('Total runtime for {} tours: {}.'.format(len(df_tours), total_time))
    print('Average runtime for 1 tour: {}.'.format(total_time/len(df_tours)))

    return objFn

def main():
    
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('--file', metavar='f', default='order', help='File name of the order book')
    argparser.add_argument('--fleetsize', metavar='l', default='5', help='Total number of launches available')
    args = argparser.parse_args()
    file = args.file
    fleet = int(args.fleetsize)

    schedule(file,fleet,None)
    
    return

if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\ndone.')










