from utils import Color, Locations
import matplotlib.pyplot as plt
import math
import os

# Visualise solution on anchorage map           
def drawSolution(solutionSet, df, ax):
    for i in range(len(solutionSet)):
        ax.scatter(Locations[df.iloc[solutionSet[i][0], 2]][0], Locations[df.iloc[solutionSet[i][0], 2]][1], marker='o')
        zone_s = df.iloc[solutionSet[i][0], 2]
        zone_e = df.iloc[solutionSet[i][1], 2]
        launch_id = str(solutionSet[i][2])
        ax.arrow(Locations[zone_s][0], Locations[zone_s][1], 
                 Locations[zone_e][0]-Locations[zone_s][0], 
                 Locations[zone_e][1]-Locations[zone_s][1], 
                 head_width=10, head_length=10, color = Color[launch_id])

def drawSolution2(raw_Timetable, tour, draw):
    img = plt.imread("Port_Of_Singapore_Anchorages_Chartlet.png")
    outputsPlotsDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/img/')
    
    fig, ax = plt.subplots()
    ax.imshow(img)

    for i in range(len(raw_Timetable[0])):
        for j in range(len(raw_Timetable[0].loc[i])-1):
            try:
                zone_s = raw_Timetable[0].iloc[i,j][0]
                zone_e = raw_Timetable[0].iloc[i, j+1][0]
                launch_id = str(i+1)

                ax.scatter(Locations[zone_s][0],Locations[zone_s][1], marker='o')
                ax.arrow(Locations[zone_s][0], Locations[zone_s][1],
                        Locations[zone_e][0] - Locations[zone_s][0], 
                        Locations[zone_e][1] - Locations[zone_s][1],
                        head_width=10, head_length=10, color = Color[launch_id])
            except:
                break
    
    if draw:
        # Save visualisations in a png file
        outputPlot = os.path.join(outputsPlotsDir,'order_Tour' + str(tour+1) + '_schedule.png')
        fig.savefig(outputPlot)

    else:
        return fig,ax

# Print each launch's route from solution set
def printRoutes(solutionSet):
    graphs = {}
    solutionSet.sort(key=lambda x:x[2])
    for launch_edge in solutionSet:
        i , j, launch = launch_edge[0], launch_edge[1], launch_edge[2]
        if launch not in graphs:
            graphs[launch] = {}
            graphs[launch][i] = [j]
        else:
            if i not in graphs[launch]:
                graphs[launch][i] = [j]
            else:
                graphs[launch][i].append(j)
    for launch, graph in graphs.items():
        routeStr = '0'
        next = graph[0][0]
        while next != 0:
            routeStr+=' - '
            routeStr+= str(next)
            next = graph[next][0]
        routeStr += ' - 0'
        print('Launch', launch, ':', routeStr)