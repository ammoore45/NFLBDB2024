# dataPull.py

## Introduction
This script is designed to perform an analysis on football tackling events by extracting relevant tracking data from a PostgreSQL database. The analysis focuses on identifying and evaluating tackling situations during football plays. The results are then stored in a results table within the same database.

## Prerequisites
Before running the script, ensure the following prerequisites are met:

Python environment with necessary packages (Pandas, NumPy, Seaborn, SQLAlchemy)
PostgreSQL database with tracking data tables (tackles, plays, tracking, players, results)

## Script Structure
The script is organized into several functions to facilitate modularity and readability. Here's an overview of each function:

1. getConn()
Establishes a connection to the PostgreSQL database and returns the connection object, the 'results' table, and the engine object.

2. Data Retrieval Functions
Several functions (getTackleData, getPlayData, getTrackingData, getPlayerData, getMaxSpeed, getOpenFieldData) retrieve specific data from the database using SQL queries. These functions are responsible for fetching tackle, play, tracking, player, and speed-related data.

3. Utility Functions
getDistance: Calculates the Euclidean distance between two points.
getDistanceFromPlayer: Computes the distance of every player and football from a given player.
checkInFront: Checks if a tackler is between the ball carrier and the end zone.
checkBySideline: Checks if a player is near the sideline.
checkFacingForward: Checks if a player is facing forward.
checkClearLane: Checks if the tackle lane is clear.

4. getPositionExclusions
Applies position-based exclusions to the dataset, considering factors such as players in front, near the sideline, and facing forward.

5. getMinFrame
Identifies the minimum frame and maximum distance from the point of intersection to the frame where exclusions fail.

6. getAcc
Calculates acceleration by taking the difference of speed values.

7. ETL
The main Extract, Transform, and Load (ETL) function that performs the analysis. It loops through all games, plays, and tacklers, extracts relevant data, applies filters, and stores the results in the 'results' table.

# Austin_Moore_NFLBDB24
This notebook utilizes the results from dataPull.py and performs statistical analysis on the results data found.

## Analysis
The scipy Chi Square function was utilized to determine significance between the tackling result and categorical indications of tackler acceleration
