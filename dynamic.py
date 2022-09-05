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

# Run optimiser from schedule.py
def optimiser(file,fleetsize):
    os.system("python3 schedule.py --file {} --fleetsize {}".format(file,fleetsize))

    # Outputs directory
    dirName = os.path.dirname(os.path.abspath(__file__))
    raw_Timetable = os.path.join(dirName, 'outputs/logs/raw_Timetable.csv')
    timetable = pd.read_csv(
        raw_Timetable, encoding='latin1', on_bad_lines='warn')
    return timetable

# Import pre-calculated route and objective value


# Identify launch's respective locations

# Caluculate ETA for vessels serve by respective launches

# Main code
def main():
    # Run optimiser
    file,fleetsize = inputs()
    timetable = optimiser(file,fleetsize)
    print(timetable)
    
    

# Run main code
if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\ndone.')
