import os
import modin.pandas as pd
import pandas as rpd
import models.tools as tools
import operator
import asyncio
import concurrent.futures
import multiprocessing
import uvicorn
import logging
import time
import contextvars

from apscheduler.schedulers.background import BackgroundScheduler
from cachetools import TTLCache
from distributed import Client
from typing import Union, List, Tuple
from models.onlineKNeighborClassifier import OnlineKNeighborClassifier
from models.ReaderWriterLock import ReaderWriterLock
from sqlalchemy import create_engine, text

from fastModels.likeRequest import LikeRequest
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

app = FastAPI()
cache = TTLCache(maxsize=10000, ttl=30)
topRatings = {}
clothingDict = {}
lock = ReaderWriterLock()

CONNECTION_STRING = f'mysql+mysqlconnector://{os.getenv("SERVER_USERNAME")}:{os.getenv("SERVER_PASSWORD")}@awseb-e-actsphbery-stack-awsebrdsdatabase-glefupggrhnl.csggsk1g25yj.us-east-1.rds.amazonaws.com:3306/ebdb'
ENGINE_CONNECTION = create_engine(CONNECTION_STRING).connect()
MAX_THREADS = multiprocessing.cpu_count() 

#SQL Alchemy
ENGINE = create_engine(CONNECTION_STRING)

#Offline Parameters
ITEM_COUNT = 25
MONTHS_INTERVAL = 1
DAYS_INTERVAL = 3

#Online Learning Parameters
WINDOW_SIZE = 50
N_NEIGHBORS = 2
PENALTY = 1000

WRITE_ID = contextvars.ContextVar('name')

oknn = OnlineKNeighborClassifier(WINDOW_SIZE, N_NEIGHBORS, PENALTY)

#Scheduler Parameters
scheduler = BackgroundScheduler()

#Modin parameters
client = Client()

#Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

@app.on_event("startup")
async def startup():
    os.environ["MODIN_ENGINE"] = "dask"
    logger.info(f"Running with {MAX_THREADS} threads.")
    WRITE_ID.set(0)
    await asyncio.gather(loadModel(), getRatings())
    logger.info("Finished initial offline ratings and loading model.")
    await asyncio.gather(loadItems()) 
    scheduler.add_job(getRatings, 'interval', hours=24)
    scheduler.add_job(loadItems, 'interval', hours=12)

@app.on_event("shutdown")
async def shutdown():
    return

@app.get("/")
async def index():
    return RedirectResponse(url="https://www.peachsconemarket.com")

@app.get("/recommendation")
async def recommendation(userId: int, gender: str, clothingType:Union[str, None] = None):
    gender = gender.lower()
    if clothingType != None:
        clothingType = clothingType.replace("_"," ").lower().split(",")
    
    if not tools.checkGender(gender) or (clothingType and not tools.checkType(clothingType)):
        raise HTTPException(status_code=400, detail="Invalid URL query parameters.")
    
    startTime = time.time()

    #Checks if in cache
    inModel = oknn.userInModel(userId)
    inCacheKeys = userId in cache.keys()
    itemIdList = []

    #Critical section
    if not inCacheKeys:
        await lock.acquire_read()
        try:
            if inModel:
                itemIdList = oknn.recommendItem(userId)
            else:
                itemIdList = topRatings[gender]
        finally:
            await lock.release_read()
    else:
        itemIdList = cache[userId]

    if not inCacheKeys and inModel:
        itemIdList = postModelRanking(itemIdList)
    
    returnItemId = getItem(itemIdList, gender, clothingType)
    if not returnItemId:
        logger.error(f"Could not reccomend item for userId: {userId}, gender: {gender}, clothingType: {clothingType}")
        return HTTPException(status_code=204, detail="Could not recommend an item.")
    itemIdList.remove(returnItemId)
    cache[userId] = itemIdList
    logger.info(f"Request with userId: {userId}, gender: {gender}, clothingType: {clothingType} returned with clothingId: {returnItemId} in elasped time {time.time() - startTime}")
    return {"clothingId" : int(returnItemId)}

@app.post("/like")
async def like(likeRequest: LikeRequest):
    await lock.acquire_write(WRITE_ID.get())
    incrementContext()
    try:
        cache.pop(likeRequest.userId)
        oknn.update(likeRequest.userId, likeRequest.clothingId, likeRequest.rating)
    finally:
        await lock.release_write()
    return "",200

async def getRatings():
    await lock.acquire_write(WRITE_ID.get())
    incrementContext()
    try:
        for gender in tools.getGenders().keys():
            df = pd.read_sql(f"SELECT ebdb.likes.id, clothing_id, rating, date_updated, date_created FROM ebdb.likes INNER JOIN ebdb.clothing ON ebdb.clothing.id = ebdb.likes.clothing_id WHERE ebdb.likes.date_updated >= CURRENT_DATE - INTERVAL '{DAYS_INTERVAL}' DAY AND ebdb.clothing.date_created >= CURRENT_DATE - INTERVAL '{MONTHS_INTERVAL}' MONTH AND ebdb.clothing.gender = {tools.genderToInt(gender)}",Connection())
            if df.empty:
                continue
            #Get all unique clothing items with likes
            averageRatings = df.groupby('clothing_id')['rating'].mean()
            averageRatingsDf = pd.DataFrame({"clothing_id":averageRatings.index, "average_rating": averageRatings.values}).sort_values(by=["average_rating"], ascending=False).head(ITEM_COUNT)
            rankings = []
            for clothing_id in averageRatingsDf["clothing_id"]:
                rankings.append(clothing_id)
            topRatings[gender] = rankings
    finally:
        await lock.release_write()
    logger.info("Finished offline rankings.")
    return

async def loadModel():
    df = pd.read_sql("SELECT ebdb.likes.user_id, ebdb.likes.clothing_id, ebdb.likes.rating FROM ebdb.likes", CONNECTION_STRING)
    for _,row in df.iterrows():
        oknn.update(row["user_id"], row["clothing_id"], row["rating"])
    return

def processRow(row, dict):
    key = row["id"]
    clothingType = row["clothing_type"]
    gender = row["gender"]

    dict[key] = (clothingType, gender)

async def loadItems():
    df = pd.read_sql(f"SELECT id, clothing_type, gender FROM ebdb.clothing", CONNECTION_STRING)
    with concurrent.futures.ThreadPoolExecutor(max_workers = MAX_THREADS) as executor:
        futureToRow = {executor.submit(processRow, row, clothingDict): row for _, row in df.iterrows()}
        for future in concurrent.futures.as_completed(futureToRow):
            try:
                future.result()
            except Exception as e:
                tools.printMessage(e)
    logger.info("Finished loading items.")
    return

def totalRatingCalcuation(recommendationScore, newestUploadScore, averageRatingScore):
    return 0.6 * (recommendationScore) + 0.25 * (newestUploadScore) + .15 * (averageRatingScore)

def postModelRanking(itemList: List[int]) -> List[int]:
    df = rpd.read_sql(text(f"SELECT ebdb.likes.clothing_id, ebdb.likes.rating, date_created FROM ebdb.likes INNER JOIN ebdb.clothing ON ebdb.clothing.id = ebdb.likes.clothing_id WHERE clothing_id IN ({','.join(map(str, itemList))})"), ENGINE_CONNECTION)
    uploadsDf = df.groupby("clothing_id")["date_created"]
    averageRatingsSeries = df.groupby('clothing_id')['rating'].mean()

    uploads = []
    averageRatings = []

    for item in itemList:
        uploads.append((item, uploadsDf.get_group(item).iloc[0]))
        averageRatings.append((item, averageRatingsSeries[item]))
    
    uploadsRank = sorted(uploads, key=operator.itemgetter(1), reverse=True)
    averageRatingsRank = sorted(averageRatings, key=operator.itemgetter(1), reverse=True)

    rankingsDict = {}
    for i in range(len(uploadsRank)):
        keys = rankingsDict.keys()
        #Uploads adding
        uploadRank = len(uploadsRank) - i
        if uploadsRank[i][0] in keys:
            rankingsDict[uploadsRank[i][0]] = (uploadRank, rankingsDict[uploadsRank[i][0]][1])
        else:
            rankingsDict[uploadsRank[i][0]] = (uploadRank, -1)

        #averageRatings adding
        averageRatingRank = len(averageRatingsRank) - i
        if averageRatingsRank[i][0] in keys:
            rankingsDict[averageRatingsRank[i][0]] = (rankingsDict[averageRatingsRank[i][0]][0], averageRatingRank)
        else:
            rankingsDict[averageRatingsRank[i][0]] = (-1, averageRatingRank)

    returnList = []
    for index, item in enumerate(itemList):
        returnList.append((item, totalRatingCalcuation(len(itemList) - index, rankingsDict[item][0], rankingsDict[item][1])))

    returnList = sorted(returnList, key=operator.itemgetter(1), reverse=True)
    return [element[0] for element in returnList]

def getIndex(list: List[tuple[int, int]], element: int)->int:
    for i, tupleItem in enumerate(list):
        if tupleItem[0] == element:
            return i
    return None

def getItem(itemList: List[int], gender, clothingType:List[str]=None):
    #Filters items
    genderInt = tools.genderToInt(gender)
    if clothingType != None:
        for index, item in enumerate(clothingType):
            clothingType[index] = tools.typeToInt(item)

    for item in itemList:
        values = getItemInformation(item)
        if values != None:
            queriedType = values[0]
            queriedGender = values[1]
            if queriedGender == genderInt and ((clothingType and queriedType in clothingType) or not clothingType):
                return item
    return None

def getItemInformation(clothingId: int)->Union[Tuple[int, int], None]:
    if clothingId in clothingDict.keys():
        return clothingDict[clothingId]
    return None

def incrementContext():
    WRITE_ID.set(WRITE_ID.get() + 1)

if __name__ == "__main__":
    uvicorn.run("main:app", port=os.getenv("FAST_PORT", 5000))