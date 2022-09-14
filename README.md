# FYP Project C112

## Summary
This project aims to study and model the ferry service operations optimisation problem as a Dynamic Capacitated Vehicle Routing Problem with Backhauls and Time Windows (DCVRPBTW).

The objective of this repository is to develop a scheduling system that can generate an optimal set of routes and schedules that best maximises the ability of ferry service operations to meet its daily demands. The following methods were employed to tackle this optimisation problem.

#### 1. Exact methods - Exhaustive Search, Integer Linear Programming Model
#### 2. Heuristic methods - Genetic Algorithm

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

Exhaustive Search
```python
python exhaustiveSearch.py
```
Integer Linear Programming Model
```python
python lpModel.py
```
Genetic Algorithm
```python
python ga.py
```
The input datasets can be found in the folder: */datasets*.
The outputs from the above scripts can be found in folder: */outputs*.
Output logs from *lpModel.py* and *ga.py* were manually compiled in *GA.txt* and *lpModel.txt* in folder: */outputs/logs*.
When running *lpModel.py* and *ga.py*, the scripts generate visualisation maps that are automatically saved in folder: */outputs/plots*.

The analysis of the output logs from *lpModel.py* and *ga.py* can be found in *resultsAll.xlsx*, in folder: */outputs/logs*.

#### 2. Run scheduling system, which optimises the sets of routes for the following test case.

Dataset: *datasets/order.csv*,

Tours: 0900-1130, 1130-1400,

Fleet size: 5

```python
python schedule.py
```

When *schedule.py* is run, it generates a timetable, *schedule.csv*, which is automatically saved in folder: */outputs/logs*.
It also generates visualisation maps that are automatically saved in folder: */outputs/plots/schedule*.

## References
1. [Modelling and Analysis of a Vehicle Routing Problem with Time Windows in Freight Delivery (MIP Model)](https://github.com/dungtran209/Modelling-and-Analysis-of-a-Vehicle-Routing-Problem-with-Time-Windows-in-Freight-Delivery/)
2. [A Python Implementation of a Genetic Algorithm-based Solution to Vehicle Routing Problem with Time Windows](https://github.com/iRB-Lab/py-ga-VRPTW/)




