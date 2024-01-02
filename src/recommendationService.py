import properties
import modin.pandas as pd
import models.tools as tools
import random
import pandas as rpd
import operator
import concurrent.futures
import numpy
import modin.pandas as pd
import models.tools as tools

from models.readerWriterLock import ReaderWriterLock
from models.onlineKNeighborClassifier import OnlineKNeighborClassifier
from fastModels.likeRequest import LikeRequest
from typing import Union, List
from sqlalchemy import create_engine, text
from distributed import Client
from apscheduler.schedulers.background import BackgroundScheduler


class RecommendationService:
    def __init__(self, logger):
        self.logger = logger

        self.topRatings = dict()
        self.clothingDict = dict()

        self.maxThreads = properties.MAX_THREADS
        self.writeId = 0

        self.scheduler = BackgroundScheduler()
        self.engine = create_engine(properties.CONNECTION_STRING)
        self.lock = ReaderWriterLock()

        #Modin Paramertes
        self.client = Client()

        #oknn
        self.oknn = OnlineKNeighborClassifier(properties.WINDOW_SIZE, properties.N_NEIGHBORS, self.clothingDict)


    def recommendClothing(self, userId: int, gender: int, clothingType:Union[List[int], None] = None, blacklist:Union[List[int], None] = None, amount:int = properties.LIST_AMOUNT)->List[int]:
        #Converts numpy.int64 to int list
        recommendedList = [int(item) for item in self.getRecommendedList(userId, gender, clothingType)]
        returnList = []

        currentAmount = 0
        while currentAmount < amount:
            choice = random.random()
            itemId = -1

            #Gets recommended item id with randomness
            if (choice > properties.RANDOM_CLOTHING_CHANCE and len(recommendedList) > 1):
                itemId = recommendedList.pop(0)
            else:
                itemId = self.getRandom(userId, gender, clothingType)

            #Checks to see if item is in the blacklist
            if blacklist and itemId in blacklist:
                continue

            #Checks to see if item is already in itemId list
            if itemId in returnList:
                continue
            
            #Appends to list
            returnList.append(itemId)
            currentAmount += 1

        return returnList

    def getRandom(self, userId: int, gender: int, clothingType:Union[List[int], None] = None)->int:
        with self.engine.connect() as connection:
            query = "SELECT c.id FROM {0}.clothing c JOIN {0}.store s ON c.store_id = s.id WHERE c.gender={1}".format(properties.DATABASE_NAME, gender)
            if clothingType != None:                
                query += " AND c.clothing_type IN ({0})".format(str(clothingType).replace("'","")[1:-1])
            else:
                query += " AND NOT c.clothing_type IN ({0})".format(properties.OTHER_INDEX)
            query += " AND c.date_created >= {0} AND s.enabled = 1".format((rpd.Timestamp.now() - rpd.DateOffset(weeks=4)).strftime('%Y-%m-%d'))

            df = rpd.read_sql(text(query), connection)
            dfSize = df.shape[0]
            if dfSize == 0:
                return -1

            loopCount = 0
            while loopCount < properties.RANDOM_UPPER_BOUND:
                loopCount += 1
                randomIndex = random.randint(0, dfSize - 1)

                #Tries randomIndex of df
                randomChoice = df.iloc[randomIndex]["id"]
                if not self.checkLike(userId, randomChoice):
                    return int(randomChoice)
        return -1

    def getRecommendedList(self, userId: int, gender: int, clothingType:Union[List[int], None] = None)->List[numpy.int64]:
        recommendedItems = []
        if self.oknn.userInModel(userId):
            #Gets recommendedList from oknn
            oknnRecommendations = self.oknn.recommendItem(userId, gender, clothingType)
            
            if len(oknnRecommendations) == 0:
                self.logger.error("Empty oknn list for {0} with parameters {1} gender and {2} clothingType.".format(userId, gender, clothingType))
                return []
            
            recommendedItems = self.postModelRanking(oknnRecommendations)
        elif gender in self.topRatings.keys():
            recommendedItems = self.topRatings[gender]
        else:
            return []

        #Checks for liked clothing
        for i in recommendedItems:
            if not self.checkLike(userId, i):
                recommendedItems.remove(i)
    
        return recommendedItems

    def checkLike(self, userId, clothingId)->bool:
        with self.engine.connect() as connection:
            result = tuple(connection.execute(text("SELECT COUNT(*) FROM likes WHERE user_id={0} AND id={1}".format(userId, clothingId))))
            if len(result) > 0 and result[0][0] > 0:
                return True
        return False

    def postModelRanking(self, itemList: List[int]) -> List[int]:
        df = None

        with self.engine.connect() as connection:
            df = rpd.read_sql(text("SELECT {0}.likes.clothing_id, {0}.likes.rating, date_created FROM {0}.likes INNER JOIN {0}.clothing ON {0}.clothing.id = {0}.likes.clothing_id WHERE clothing_id IN ({1})".format(properties.DATABASE_NAME, ','.join(map(str, itemList)))), connection)
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
            returnList.append((item, RecommendationService.totalRatingCalcuation(len(itemList) - index, rankingsDict[item][0], rankingsDict[item][1])))

        returnList = sorted(returnList, key=operator.itemgetter(1), reverse=True)
        return [element[0] for element in returnList]
    
    async def postLike(self, like: LikeRequest)->bool:
        await self.lock.acquire_write(self.writeId)
        self.incrementContext()
        try:
            self.oknn.update(like.userId, like.clothingId, like.rating)
        finally:
            await self.lock.release_write()

    def processRow(self, row, dict):
        key = row["id"]
        clothingType = row["clothing_type"]
        gender = row["gender"]

        dict[key] = (clothingType, gender)

    def incrementContext(self):
        self.writeId += 1
        self.writeId %= 10000000

    async def getRatings(self):
        await self.lock.acquire_write(self.writeId)
        self.incrementContext()
        try:
            for gender in range(properties.GENDER_AMOUNT):
                df = pd.read_sql("SELECT {0}.likes.id, clothing_id, rating, date_updated, date_created FROM {0}.likes INNER JOIN {0}.clothing ON {0}.clothing.id = {0}.likes.clothing_id WHERE {0}.likes.date_updated >= CURRENT_DATE - INTERVAL '{1}' DAY AND {0}.clothing.date_created >= CURRENT_DATE - INTERVAL '{2}' MONTH AND {0}.clothing.gender = {3}".format(properties.DATABASE_NAME, properties.DAYS_INTERVAL, properties.MONTHS_INTERVAL, gender), properties.CONNECTION_STRING)
                rankings = []
                if df.empty:
                    for _ in range(properties.ITEM_COUNT):
                        clothing_id = self.getRandom(-1, gender)
                        if clothing_id >= 0:
                            rankings.append(clothing_id)
                    self.topRatings[gender] = rankings
                    continue
                #Get all unique clothing items with likes
                averageRatings = df.groupby('clothing_id')['rating'].mean()
                averageRatingsDf = pd.DataFrame({"clothing_id":averageRatings.index, "average_rating": averageRatings.values}).sort_values(by=["average_rating"], ascending=False).head(properties.ITEM_COUNT)
                for clothing_id in averageRatingsDf["clothing_id"]:
                    rankings.append(clothing_id)

                self.topRatings[gender] = rankings
        finally:
            await self.lock.release_write()
        self.logger.info("Finished offline rankings.")
        return

    async def loadModel(self):
        df = pd.read_sql("SELECT {0}.likes.user_id, {0}.likes.clothing_id, {0}.likes.rating FROM {0}.likes".format(properties.DATABASE_NAME), properties.CONNECTION_STRING)
        print(df.size)
        for _,row in df.iterrows():
            self.oknn.update(row["user_id"], row["clothing_id"], row["rating"])
        return
    
    async def loadItems(self):
        await self.lock.acquire_write(self.writeId)
        self.incrementContext()
        try:
            df = pd.read_sql("SELECT id, clothing_type, gender FROM {0}.clothing".format(properties.DATABASE_NAME), properties.CONNECTION_STRING)
            with concurrent.futures.ThreadPoolExecutor(max_workers = self.maxThreads) as executor:
                futureToRow = {executor.submit(self.processRow, row, self.clothingDict): row for _, row in df.iterrows()}
                for future in concurrent.futures.as_completed(futureToRow):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.info(e)
            self.logger.info("Finished loading items.")
        finally:
            await self.lock.release_write()
        return

    @staticmethod
    def totalRatingCalcuation(recommendationScore, newestUploadScore, averageRatingScore):
        return 0.6 * (recommendationScore) + 0.25 * (newestUploadScore) + .15 * (averageRatingScore)