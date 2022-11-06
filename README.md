# FYP Project C109

## Summary
This project aims to study and model the ferry service operations optimisation problem as a Dynamic Capacitated Vehicle Routing Problem with Backhauls and Time Windows (DCVRPBTW).

The objective of this repository is to develop a robust scheduling system that can handle last minute bookings and cancellations while generating an optimal set of routes and schedules that best maximises the ability of ferry service operations to meet its daily demands. The exact method was employed to tackle this optimisation problem.

#### Exact method - Linear Programming Model

All the above methods were implemented using Python 3.10.
The algorithms were run and tested on a MacBook Pro 13-inch 2018 model with a 2.3 GHz Quad-Core Intel Core i5 and 16 GB RAM.

## Installation

#### 1. Clone this repository in your working directory (Skip this step if this folder is already downloaded in your computer)

```bash
git clone https://github.com/aneo008/ferryServiceVRP.git
```

#### 2. Install dependencies in virtual environment 

```bash
cd /YourDirectory/ferryServiceVRP # Change directory to ferry service VRP folder
# If venv file already exist, delete it and create it again every time you shift the location of this project
# See https://stackoverflow.com/questions/20952797/pip-installing-in-global-site-packages-instead-of-virtualenv if you are facing venv issues
python3.10 -m venv venv # Create Virtual Environment for Python 3.10 named "venv"

# Enter virtual environment
source venv/bin/activate 
pip install -r requirements.txt # If venv file exists, this should already be installe

# To exit virtual environment when done
deactivate 
```

## Usage

#### 1. Test python scripts on a sample dataset: *LT1.csv*, by default. 

Integer Linear Programming Model
```python
python3 lpModel.py
```

The input datasets can be found in the folder: */datasets*.
The outputs from the above scripts can be found in folder: */outputs*.
Output logs from *lpModel.py* is manually compiled in *lpModel.txt* in folder: */outputs/logs*.
When running *lpModel.py* , the scripts generate visualisation maps that are automatically saved in folder: */outputs/plots*.

The analysis of the output logs from *lpModel.py* can be found in *resultsAll.xlsx*, in folder: */outputs/logs*.

#### 2. Run scheduling system, which optimises the sets of routes for the following test case.

Dataset: *datasets/order.csv*,

Tours: 0900-1130, 1130-1400,

Fleet size: 5

```python
python3 schedule.py
```
When *schedule.py* is run, it generates a timetable, *schedule.csv*, which is automatically saved in folder: */outputs/logs*.
It also generates visualisation maps that are automatically saved in folder: */outputs/plots/schedule*.

#### 3. Run the FLASK app which would start a local host server on your computer and allow you to view all relevant data generated on a browser.

```python
python3 app.py
```
After running *app.py*, the terminal should show the address the server is running on that would look something like "Running on http://127.0.0.1:5000". Copy this address and paste it into your browser. To close the server, press CTRL+C. 

For the server, the HTML templates are found in */templates*, CSS in */static/css*, images including the solution of each tour route in */static/img*.

Ensure you have internet connection for the formatting to work as the formatting uses BootStrap Library. 

Currently, *schedule.py* runs every time you start up the server. If this takes too much time (eg when debugging), you may wish to hash out #schedule.py in line 14 of *app.py*. However if you do this, remember to run *schedule.py* before running *app.py*.

## References
1. [Modelling and Analysis of a Vehicle Routing Problem with Time Windows in Freight Delivery (MIP Model)](https://github.com/dungtran209/Modelling-and-Analysis-of-a-Vehicle-Routing-Problem-with-Time-Windows-in-Freight-Delivery/)
2. [A Python Implementation of a Genetic Algorithm-based Solution to Vehicle Routing Problem with Time Windows](https://github.com/iRB-Lab/py-ga-VRPTW/)
3. [Final Year Project: Modelling the scheduling and routing of ferry service operations as a VRPTW-SDP ](https://github.com/chensxb97/ferryServiceVRP)