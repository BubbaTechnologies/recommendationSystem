import os
import asyncio
import uvicorn
import logging
import models.tools as tools

from recommendationService import RecommendationService
from apscheduler.schedulers.background import BackgroundScheduler
from cachetools import TTLCache

from typing import Union, List

from fastModels.likeRequest import LikeRequest
from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse

app = FastAPI()
cache = TTLCache(maxsize=10000, ttl=10)
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

    recList = [int(x) for x in service.recommendClothing(userId, gender, clothingType)]
    cache[userId] = (gender, clothingType, recList)

    if len(recList) == 0:
        return Response(content="No recommendation", status_code=503)
    
    return {
        "clothingIds":recList
    }
    
@app.get("/recommendation")
async def recommendation(userId: int, gender: int, clothingType:Union[str, None] = None):  
    if userId in cache.keys() and cache[userId][0] == gender and cache[userId][1] == clothingType:
        recItem = cache[userId][0]
        return {"clothingId" : recItem}
    else:
        recList = reccomendationList(userId, gender, clothingType)
        return {"clothingId" : recList["clothingIds"][0]} if type(recList) == dict else recList

@app.post("/like")
async def like(likeRequest: LikeRequest):
    if like.userId in cache.keys():
        cache.pop(likeRequest.userId)
    await service.postLike(likeRequest)
    return Response(content="", status_code=200)

def getClothingTypeList(urlParam: str) -> tuple[int]:
    return [int(param) for param in urlParam.split(",")]

if __name__ == "__main__":
    uvicorn.run("main:app", port=os.getenv("FAST_PORT", 5000))