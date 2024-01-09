# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 19:11:26 2023

@author: austi
"""

import pandas as pd
import numpy as np
import os
import seaborn as sns
from sqlalchemy import create_engine, insert, MetaData
from sqlalchemy.sql import func
from urllib.parse import quote_plus
import warnings
import math
import datetime
warnings.filterwarnings('ignore')

def getConn():
    user = ####
    pw = ####
    db = ####
    host = ####
    port = ####
    uri = f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(pw)}@{host}:{port}/{db}"
    alchemyEngine = create_engine(uri)
    conn = alchemyEngine.connect()
    
    meta = MetaData(alchemyEngine)
    meta.reflect()
    table = meta.tables['results']
    return conn, table, alchemyEngine



def getTackleData(conn):
    sql = f'''
    SELECT *
    FROM tackles
    '''
    df = pd.read_sql(sql, conn)
    return df

def getPlayData(conn):
    sql = f'''
    SELECT *
    FROM plays
    WHERE "playId" IN (SELECT DISTINCT "playId" FROM tackles)
    '''
    df = pd.read_sql(sql, conn)
    return df

def getTrackingData(gameId, playId, conn):
    sql = f'''
    SELECT *
    FROM tracking
    WHERE "playId" = {playId} AND "gameId" = {gameId}
    '''
    df = pd.read_sql(sql, conn)
    return df

def getPlayerData(conn):
    sql = '''
    SELECT *
    FROM players
    '''
    df = pd.read_sql(sql, conn)
    return df

def getMaxSpeed(conn):
    sql = '''
    SELECT "nflId"
    ,MAX("s") as "maxSpeed"
    FROM tracking
    GROUP BY "nflId"
    ORDER BY "maxSpeed" ASC
    '''
    df = pd.read_sql(sql, conn)
    return df

def getOpenFieldData(conn):
    sql = '''
    SELECT "gameId"
    ,"playId"
    ,"tacklerId"
    ,"carrierId"
    ,"maxFrame"
    ,"minFrame"
    ,ROUND(CAST("maxDis" AS numeric),1) as "maxDis"
    ,"tackle"
    ,"lastUpdate"
    FROM results
    WHERE "maxDis" >= 5.0 AND ("maxFrame"-"minFrame") != 0
    '''
    df = pd.read_sql(sql, conn)
    return df

def getDistance(x1, x2, y1, y2): #Finds the the distance between (x1,y1) and (x2,y2)
    dis = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    return dis

def getDistanceFromPlayer(Id, dfTS, mess): #Finds every player and footballs distance from the player given
    dfOther = dfTS.query('nflId != @Id')
    dfPlayer = dfTS.query('nflId == @Id') #Split out unique player and create unique x,y
    dfPlayer['x_bc'] = dfPlayer['x']
    dfPlayer['y_bc'] = dfPlayer['y']
    dfPlayer = dfPlayer[['frameId', 'x_bc', 'y_bc']]
    dfOther = dfOther.merge(dfPlayer, on='frameId', how='left') #Merge player x,y back on with all others
    dfOther['disFrom'+mess] = np.vectorize(getDistance)(dfOther['x'], dfOther['x_bc'], dfOther['y'], dfOther['y_bc']) #calculate the distance from bc by vectorizing dis function
    dfFinal = dfTS.merge(dfOther[['nflId', 'frameId', 'disFrom'+mess]], on=['nflId', 'frameId'], how='outer') #Join distance back on full play df and return
    return dfFinal

def checkInFront(dis, playDir, x_b, x_t): #Function returns True if the tackler is between the ballcarrier and the endzone
    ###Intended for vectorizatoin in checkInFront(): Function###
    if dis >= 1.0:
        if playDir == 'left':
            if x_b > x_t:
                val = True
            else:
                val = False
        elif playDir == 'right':
            if x_b < x_t:
                val = True
            else:
                val = False
    else :
        val = True
    return val

def checkBySideline(y, y_b):
    if y_b < 5:
        val = True
    elif y_b > 48.3:
        val = True
    elif y < 5:
        val = True
    elif y > 48.3:
        val = True
    else:
        val = False
    return val

def checkFacingForward(playDir, o_t, o_b):
    if playDir == 'left':
        if ((o_b >= 225) and (o_b <= 315) and (o_t >= 45) and (o_t <= 135)):
            val = True
        else:
            val = False
    if playDir == 'right':
        if ((o_t >= 225) and (o_t <= 315) and (o_b >= 45) and (o_b <= 135)):
            val = True
        else:
            val = False
    return val
    
def checkClearLane(dfFinal, df_O, df_B):
    dfFinal['clearLane'] = True 
    for i in dfFinal.index.to_list():
        frame = dfFinal.loc[i, 'frameId']
        dfTemp = df_O.query('frameId == @frame')
        x_t = dfFinal.query('frameId == @frame')['x'].item()
        y_t = dfFinal.query('frameId == @frame')['y'].item()
        x_b = df_B.query('frameId == @frame')['x'].item()
        y_b = df_B.query('frameId == @frame')['y'].item()
        if x_t > x_b:
            xMin = x_b - 1.0
            xMax = x_t + 1.0
        else:
            xMin = x_t - 1.0
            xMax = x_b + 1.0
        if y_t > y_b:
            yMin = y_b - 1.0
            yMax = y_t + 1.0
        else:
            yMin = y_t - 1.0
            yMax = y_b + 1.0
        if len(dfTemp.query('x >= @xMin & x <= @xMax & y >= @yMin & y <= @yMax').index) >= 1:
            dfFinal.loc[i, 'clearLane'] = False
    return dfFinal

def getPositionExclusions(df, dfFinal):
    df['x_bc'] = df['x']
    df['y_bc'] = df['y']
    df['o_bc'] = df['o']
    df = df[['frameId', 'x_bc', 'y_bc', 'o_bc']]
    dfFinal = dfFinal.merge(df, on='frameId', how='left') #Merge player x,y back on with all others
    dfFinal['inFront'] = np.vectorize(checkInFront)(dfFinal['disFromBc'], dfFinal['playDirection'], dfFinal['x_bc'], dfFinal['x'])
    dfFinal['bySideline'] = np.vectorize(checkBySideline)(dfFinal['y'], dfFinal['y_bc'])
    dfFinal['facingForward'] = np.vectorize(checkFacingForward)(dfFinal['playDirection'], dfFinal['o'], dfFinal['o_bc'])
    dfFinal = dfFinal.drop(['x_bc', 'y_bc', 'o_bc'], axis=1)
    return dfFinal

def getMinFrame(df):
    listFrame = df['frameId'].to_list()
    listFrame.sort(reverse=True)
    for i in listFrame:
        inFront = df.query('frameId == @i')['inFront'].item()
        bySideline = df.query('frameId == @i')['bySideline'].item()
        clearLane = df.query('frameId == @i')['clearLane'].item()
        faceForward = df.query('frameId == @i')['facingForward'].item()
        if df.query('frameId == @i')['disFromBc'].item() >= 1:
            if ((inFront == True) and (bySideline == False) and (clearLane == True) and (faceForward == True)):
                continue
            else:
                break
        else:
            if clearLane == True:
                continue
            else:
                break
    frame = i
    maxD = df.query('frameId >= @i')['disFromBc'].max()
    return frame, maxD

def getAcc(df): #Gets Acceleration 
    Acc = df['s'].diff()
    df['aBiDir'] = Acc*10
    return df

def ETL():
    #Retrieve connection object, results table and engine object from getConn()
    con, results, engine = getConn()
    num = 1
    #Retireve play and tackle data to loop through
    dfTackles = getTackleData(con)
    dfPlays = getPlayData(con)
    dfMax = getMaxSpeed(con)
    #Loop through all games
    for i in dfTackles['gameId'].unique().tolist():
        gid = i #assign game id variable
        for j in dfPlays.query('gameId == @gid')['playId'].to_list(): #loop through all unique plays for each  game
            pid = j #assign play id variable
            print(pid)
    
            #Retrieve data needed
            dfTrack = getTrackingData(i, j, con) #Pull tracking data for the each play
            cid = dfPlays.query('gameId == @gid & playId == @pid')['ballCarrierId'].item() #Assign carrierId from plays table
            dfTacklers = dfTackles.query('gameId == @gid & playId == @pid') #Get df of all tacklers for the given play
            if dfTacklers['assist'].sum() > 0: #If there are assists on the play, we only want to look at missed tacklers
                dfTacklers = dfTacklers.query('assist == 0 & pff_missedTackle == 1')
            else: #Else look at tacklers and missed tacklers combined
                dfTacklers = dfTacklers.query('tackle == 1 | pff_missedTackle == 1')
            dfTrack = getDistanceFromPlayer(cid, dfTrack, 'Bc') #Add a column for distance from ballcarrier
            
            if dfTacklers.shape[0] > 0: #Check if there are results after the assist/missed filters
                for k in dfTacklers['nflId'].to_list(): #Loop through all tacklers returned
                    tid = k #Assign tacklerId
                    if dfTacklers.query('nflId == @tid')['pff_missedTackle'].item() == 1: #If a missed tackle play then tackle = False
                        result = 0
                    else:
                        result = 1
                        
                    #Create tackler df, find point of intersection, and reduce tackler df to needed frames
                    dfTackler = dfTrack.query('nflId == @tid') #get tracking data for the tackler only
                    intPoint = dfTackler['disFromBc'].min() #Find point of intersection 
                    if intPoint > 1: #Make sure the two actually meet on the field
                        continue
                    if dfTackler.query('disFromBc == @intPoint')['frameId'].shape[0] > 1: #If there are more than one frames at min distance then find the lowest to start from
                        dfTemp = dfTackler.query('disFromBc == @intPoint')
                        maxF = dfTemp['frameId'].min()
                    else:
                        maxF = dfTackler.query('disFromBc == @intPoint')['frameId'].item()
                        
                    dfTackler = dfTackler.query('frameId <= @maxF') #Limit tackler df to point of intersection
                    
                    #Create additional reference DataFrames and get exclusions
                    dfBc = dfTrack.query('nflId == @cid & frameId <= @maxF') #create carrier df
                    dfTackler = getPositionExclusions(dfBc, dfTackler) #create boolean column if defenders 
                    dfOther = dfTrack.query('nflId != @cid & nflId != @tid & frameId < @maxF & club != "football"') #create frame of players other than tackler and bc
                    dfTackler = checkClearLane(dfTackler, dfOther, dfBc) #Create boolean column for if the tackle lane is clear
                    
                    #Find the minimum frame, max distance and export to results table
                    tempF, tempDis  = getMinFrame(dfTackler) #Get min frame and max distance from int point to frame where exclusions fail
                    if tempDis < 5:
                        continue
                    else:
                        dfBc = dfBc.query('frameId > @tempF')
                        dfTackler = dfTackler.query('frameId > @tempF')
                    dfBc = getAcc(dfBc)
                    dfTackler = getAcc(dfTackler)
                    dfTackler = dfTackler.query('disFromBc >= 1 & disFromBc <= 5')
                    dfTackler.dropna(subset=['aBiDir'], inplace=True)
                    maxF = dfTackler['frameId'].max()
                    minF = dfTackler['frameId'].min()
                    dfBc = dfBc.query('frameId >= @minF & frameId <= @maxF')
                    
                    scs = dfBc.query('frameId == @minF')['s'].item() #carrier start speed
                    sce = dfBc.query('frameId == @maxF')['s'].item() #carrier end speed
                    scm = dfBc['s'].mean() #carrier mean speed
                    scd = dfMax.query('nflId == @cid')['maxSpeed'].item() #carrier normalized speed denominator
                    acs = dfBc.query('frameId == @minF')['aBiDir'].item() #carrier starting acceleration
                    acm = dfBc['aBiDir'].mean() #carrier mean acceleration
                    ace = dfBc.query('frameId == @maxF')['aBiDir'].item() #carrier ending acceleration
                    sts = dfTackler.query('frameId == @minF')['s'].item() #tackler starting speed
                    ste = dfTackler.query('frameId == @maxF')['s'].item() #tackler ending speed
                    stm = dfTackler['s'].mean() #tackler mean speed
                    std = dfMax.query('nflId == @tid')['maxSpeed'].item() #tackler normalized speed denominator
                    ats = dfTackler.query('frameId == @minF')['aBiDir'].item() #tackler starting acceleration
                    atm = dfTackler['aBiDir'].mean() #tackler mean acceleration
                    ate = dfTackler.query('frameId == @maxF')['aBiDir'].item() #tackler ending acceleration
                    
                    stmt = (insert(results).values(gameId=gid, playId=pid, tacklerId=tid, carrierId=cid, maxFrame=maxF, minFrame=minF, tSpdStart=sts, tSpdEnd=ste
                            , tSpdMean=stm, tDenom=std, tAccStart=ats, tAccEnd=ate, tAccMean=atm, cSpdStart=scs, cSpdEnd=sce, cSpdMean=scm, cDenom=scd, cAccStart=acs
                            , cAccEnd=ace, cAccMean=acm, tackle=result, lastUpdate=func.now()))
                    with engine.begin() as connection:
                        connection.execute(stmt)
                    print(str(num) + ' Successful')
                    num += 1
            else:
                continue
    con.close()
        

#ETL()






