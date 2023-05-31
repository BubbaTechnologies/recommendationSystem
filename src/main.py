import os
import modin.pandas as pd
import models.tools as tools
import operator
import asyncio
import time
import concurrent.futures
import multiprocessing
import uvicorn

from apscheduler.schedulers.background import BackgroundScheduler
from cachetools import TTLCache
from distributed import Client
from typing import Union, List, Tuple
from models.onlineKNeighborClassifier import OnlineKNeighborClassifier

from fastModels.likeRequest import LikeRequest
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

app = FastAPI()
cache = TTLCache(maxsize=10000, ttl=5)
topRatings = {}
clothingDict = {}
lock = asyncio.Lock()

CONNECTION_STRING = f'mysql+mysqlconnector://{os.getenv("SERVER_USERNAME")}:{os.getenv("SERVER_PASSWORD")}@awseb-e-actsphbery-stack-awsebrdsdatabase-glefupggrhnl.csggsk1g25yj.us-east-1.rds.amazonaws.com:3306/ebdb'
MAX_THREADS = multiprocessing.cpu_count() - 1

#Offline Parameters
ITEM_COUNT = 25
MONTHS_INTERVAL = 1
DAYS_INTERVAL = 3

#Online Learning Parameters
WINDOW_SIZE = 50
N_NEIGHBORS = 2
PENALTY = 1000

oknn = OnlineKNeighborClassifier(WINDOW_SIZE, N_NEIGHBORS, PENALTY)

#Scheduler Parameters
scheduler = BackgroundScheduler()

#Modin parameters
client = Client()

@app.on_event("startup")
async def startup():
    os.environ["MODIN_ENGINE"] = "dask"
    await asyncio.gather(loadModel(), getRatings())
    print(f"[{time.time()}]: Finished initial offline ratings and loading model.")
    await asyncio.gather(loadItems()) 
    scheduler.add_job(getRatings, 'interval', hours=24)
    scheduler.add_job(loadItems, 'interval', hours=12)

@app.on_event("shutdown")
async def shutdown():
    return

@app.get("/")
async def index():
    return RedirectResponse(url="https://www.peachsconemarket.com")

@app.get("/reccomendation")
async def reccomendation(userId: int, gender: str, clothingType:Union[str, None] = None):
    gender = gender.lower()
    if clothingType != None:
        clothingType = clothingType.replace("_"," ").lower()
    
    if not tools.checkGender(gender) or (clothingType and not tools.checkType(clothingType)):
        raise HTTPException(status_code=400, detail="Invalid URL query parameters.")
    
    startTime = time.time()
    #Checks if in cache
    inModel = oknn.userInModel(userId)
    itemIdList = []
    if userId not in cache.keys() and inModel:
        await lock.acquire()
        try:
            itemIdList = oknn.reccomendItem(userId)
        finally:
            lock.release()
        itemIdList = postModelRanking(itemIdList)
    elif userId not in cache.keys():
        itemIdList = topRatings[gender]
    else:
        itemIdList = cache[userId]

    returnItemId = getItem(itemIdList, gender, clothingType)
    if not returnItemId:
        return HTTPException(status_code=204, detail="Could not reccomend an item.")
    
    itemIdList.remove(returnItemId)
    cache[userId] = itemIdList
    print(f"Elapsed time: {time.time() - startTime}")
    return {"itemId":int(returnItemId)}

@app.post("/like")
async def like(likeRequest: LikeRequest):
    await lock.acquire()
    try:
        oknn.update(likeRequest.userId, likeRequest.clothingId, likeRequest.rating)
    finally:
        lock.release()
    return 

async def getRatings():
    for gender in tools.getGenders().keys():
        df = pd.read_sql(f"SELECT ebdb.likes.id, clothing_id, rating, date_updated, date_created FROM ebdb.likes INNER JOIN ebdb.clothing ON ebdb.clothing.id = ebdb.likes.clothing_id WHERE ebdb.likes.date_updated >= CURRENT_DATE - INTERVAL '{DAYS_INTERVAL}' DAY AND ebdb.clothing.date_created >= CURRENT_DATE - INTERVAL '{MONTHS_INTERVAL}' MONTH AND ebdb.clothing.gender = {tools.genderToInt(gender)}",CONNECTION_STRING)
        if df.empty:
            continue

        #Get all unique clothing items with likes
        averageRatings = df.groupby('clothing_id')['rating'].mean()
        averageRatingsDf = pd.DataFrame({"clothing_id":averageRatings.index, "average_rating": averageRatings.values}).sort_values(by=["average_rating"], ascending=False).head(ITEM_COUNT)
        rankings = []
        for clothing_id in averageRatingsDf["clothing_id"]:
            rankings.append(clothing_id)
        topRatings[gender] = rankings
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
                print(e)
    return

def totalRatingCalcuation(reccomendationScore, newestUploadScore, averageRatingScore):
    return 0.6 * (reccomendationScore) + 0.25 * (newestUploadScore) + .15 * (averageRatingScore)

def postModelRanking(itemList: List[int]) -> List[int]:
    #Gets all uploads and ratings
    df = pd.read_sql(f"SELECT ebdb.likes.clothing_id, ebdb.likes.rating, date_created FROM ebdb.likes INNER JOIN ebdb.clothing ON ebdb.clothing.id = ebdb.likes.clothing_id", CONNECTION_STRING)
    uploadsDf = df.groupby("clothing_id")["date_created"]
    averageRatingsSeries = df.groupby('clothing_id')['rating'].mean()

    uploads = []
    averageRatings = []

    for item in itemList:
        uploads.append((item, uploadsDf.get_group(item).iloc[0]))
        averageRatings.append((item, averageRatingsSeries[item]))
    
    uploadsRank = sorted(uploads, key=operator.itemgetter(1), reverse=True)
    averageRatingsRank = sorted(averageRatings, key=operator.itemgetter(1), reverse=True)

    returnList = []
    for item in itemList:
        returnList.append((item, totalRatingCalcuation(len(itemList) - itemList.index(item),len(uploadsRank) - getIndex(uploadsRank, item), len(averageRatingsRank) - getIndex(averageRatingsRank, item))))

    returnList = sorted(returnList, key=operator.itemgetter(1), reverse=True)
    return [element[0] for element in returnList]

def getIndex(list: List[tuple[int, int]], element: int)->int:
    for i, tupleItem in enumerate(list):
        if tupleItem[0] == element:
            return i
    return None

def getItem(itemList: List[int], gender, clothingType=None):
    #Filters items
    genderInt = tools.genderToInt(gender)
    if clothingType:
        clothingTypeInt = tools.typeToInt(clothingType)

    for item in itemList:
        values = getItemInformation(item)
        if values != None:
            queriedType = values[0]
            queriedGender = values[1]
            if queriedGender == genderInt and ((clothingType and clothingTypeInt == queriedType) or not clothingType):
                return item
    return None

def getItemInformation(clothingId: int)->Union[Tuple[int, int], None]:
    if clothingId in clothingDict.keys():
        return clothingDict[clothingId]
    return None

if __name__ == "__main__":
    uvicorn.run("main:app", port=os.getenv("FAST_PORT", 5000))