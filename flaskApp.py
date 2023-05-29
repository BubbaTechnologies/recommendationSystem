import time

import os
import modin.pandas as pd
import models.tools as tools
import operator

from waitress import serve
from apscheduler.schedulers.background import BackgroundScheduler
from distributed import Client
from flask import Flask, redirect, request, Response, jsonify
from typing import List
from models.onlineKNeighborClassifier import OnlineKNeighborClassifier
from flask_caching import Cache

CONNECTION_STRING = f'mysql+mysqlconnector://{os.getenv("SERVER_USERNAME")}:{os.getenv("SERVER_PASSWORD")}@awseb-e-actsphbery-stack-awsebrdsdatabase-glefupggrhnl.csggsk1g25yj.us-east-1.rds.amazonaws.com:3306/ebdb'
INFO_DICT = {}

#Offline Parameters
ITEM_COUNT = 25
MONTHS_INTERVAL = 1
DAYS_INTERVAL = 3

#Online Learning Parameters
WINDOW_SIZE = 50
N_NEIGHBORS = 2
PENALTY = 1000

oknn = OnlineKNeighborClassifier(WINDOW_SIZE, N_NEIGHBORS, PENALTY)

#Flask Parameters
config = {
    "CACHE_TYPE":"SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 5
}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

#Scheduler Parameters
scheduler = BackgroundScheduler()


@app.route("/")
def home():
    return redirect("https://www.peachsconemarket.com", code=302)

@app.route("/reccomendation", methods=['GET'])
def reccomendation():
    try:
        userId = request.args.get('userId', type=int)
        if userId == None:
            raise Exception()
        gender = request.args.get('gender', type=str).lower()
        clothingType = request.args.get('type', None, type=str)
        if clothingType != None:
            clothingType = clothingType.replace("_"," ").lower()
    except:
        return "Invalid URL parameters.", 400
    
    if not tools.checkGender(gender) or (clothingType and not tools.checkType(clothingType)):
        return "Invalid URL parameters.", 400
    
    startTime = time.time()
    
    #Checks if reccomendations in cache
    timeout = 5
    itemIdList = cache.get(userId)
    if itemIdList is None and oknn.userInModel(userId):
        itemIdList = postModelRanking(oknn.reccomendItem(userId))
    elif itemIdList is None:
        itemIdList = cache.get(f"{gender}List")
        #Sets cache timeout to 43200
        timeout = 43200
    
    returnItemId = getItem(itemIdList, gender, clothingType)
    if not returnItemId:
        return '', 204

    itemIdList.remove(returnItemId)
    cache.set(userId, itemIdList, timeout=timeout)
    
    response = {
        "itemId": int(returnItemId)
    }

    return jsonify(response)

@app.route("/like", methods=['POST'])
def like():
    """
    {
    "userId": int,
    "clothingId": int,
    "rating": double
    }
    """
    
    requestJson = request.get_json()
    print(requestJson)
    try:
        oknn.update(requestJson["userId"], requestJson["clothingId"], requestJson["rating"])
        return '', 200
    except:
        return "Invalid JSON.", 415
        

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

    df = pd.read_sql(f"SELECT id, clothing_type, gender FROM ebdb.clothing", CONNECTION_STRING)
    for item in itemList:
        val = df[df['id'] == item]
        queriedType = val['clothing_type'].values[0]
        queriedGender = val['gender'].values[0]
        if queriedGender == genderInt and ((clothingType and clothingTypeInt == queriedType) or not clothingType):
            return item
    return None

def getRatings():
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
        cache.set(f"{gender}List", rankings, timeout=86400)

if __name__ == '__main__':
    os.environ["MODIN_ENGINE"] = "dask"
    client = Client()

    scheduler.start()
    
    df = pd.read_sql("SELECT ebdb.likes.user_id, ebdb.likes.clothing_id, ebdb.likes.rating FROM ebdb.likes", CONNECTION_STRING)
    for i,row in df.iterrows():
        oknn.update(row["user_id"], row["clothing_id"], row["rating"])

    #Adds getRatings
    getRatings()
    scheduler.add_job(getRatings, 'interval', hours=24)

    port = int(os.environ.get('PORT', 5000))
    app.run(port=port)
    #serve(app, host="127.0.0.1",port=port)