import os
import asyncio
import uvicorn
import logging
import models.tools as tools
import properties

from recommendationService import RecommendationService
from apscheduler.schedulers.background import BackgroundScheduler
from cachetools import TTLCache

from typing import Union, List

from fastModels.likeRequest import LikeRequest
from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse

app = FastAPI()
cache = TTLCache(maxsize=10000, ttl=10)
recommendCache = TTLCache(maxsize=10000, ttl=600)
scheduler = BackgroundScheduler()
logger = logging.getLogger(__name__)
service = RecommendationService(logger)

@app.on_event("startup")
async def startup():
    #Creates logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    os.environ["MODIN_ENGINE"] = "dask"
    logger.info("Running with {0} threads.".format(service.maxThreads))
    await asyncio.gather(service.loadModel(), service.getRatings())
    logger.info("Finished initial offline ratings and loading model.")
    await asyncio.gather(service.loadItems()) 
    scheduler.add_job(service.getRatings, 'interval', hours=24)
    scheduler.add_job(service.loadItems, 'interval', hours=12)

@app.on_event("shutdown")
async def shutdown():
    return

@app.get("/")
async def index():
    return RedirectResponse(url="https://www.peachsconemarket.com")

@app.get("/health")
async def health():
    return Response(content="", status_code=200)

@app.get("/recommendationList")
async def reccomendationList(userId: int, gender: int, clothingType:Union[str, None] = None):
    if clothingType:
        clothingType = getClothingTypeList(clothingType)

    recList = service.recommendClothing(userId, gender, clothingType)

    if len(recList) == 0:
        return Response(content="No recommendation", status_code=503)
    
    recommendCacheItem(userId, recList, recommendCache)
    return {"clothingIds":recList}
    
@app.get("/recommendation")
async def recommendation(userId: int, gender: int, clothingType:Union[str, None] = None):  
    recItem = None
    if userId in cache.keys() and cache[userId][0] == gender and cache[userId][1] == clothingType:
        recItem = cache[userId][2].pop(0)
    else:
        if clothingType:
            clothingType = getClothingTypeList(clothingType)

        recList = service.recommendClothing(userId, gender, clothingType)
        if len(recList) == 0:
            return Response(content="No recommendation", status_code=503)

        recItem = recList.pop(0)
        cache[userId] = (gender, clothingType, recList)

    recommendCacheItem(userId, [recItem], recommendCache)
    return {"clothingId": recItem}

@app.post("/like")
async def like(likeRequest: LikeRequest):
    if likeRequest.userId in cache.keys():
        cache.pop(likeRequest.userId)
    await service.postLike(likeRequest)
    return Response(content="", status_code=200)

def getClothingTypeList(urlParam: str) -> list[int]:
    return [int(param) for param in urlParam.split(",")]

def recommendCacheItem(userId: int, items: [int], recommendCache):
    if userId in recommendCache.keys():
        #Get difference of recommendCache list size and items list size.
        #Pop difference
        itemsToPop = len(items)
        if itemsToPop > properties.LIST_AMOUNT:
            recommendCache[userId] = items[(itemsToPop):]
        else:
            recommendCache[userId] = recommendCache[userId][(itemsToPop):] + items
    else:
        #Add userId to cache
        recommendCache[userId] = items

if __name__ == "__main__":
    uvicorn.run("main:app", port=os.getenv("FAST_PORT", 5000))