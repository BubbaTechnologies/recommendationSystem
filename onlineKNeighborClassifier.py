from sklearn.neighbors import NearestNeighbors
import numpy as np
import math
from typing import List

class OnlineKNeighborClassifier:
    def __init__(self, windowSize: int, nNeighbors: int, penalty: int):
        self.windowSize = windowSize
        self.nNeighbors = nNeighbors + 1
        self.penalty = penalty
        self.userProfiles:List[int] = []
        self.itemRatings = []
        self.nn = NearestNeighbors(n_neighbors=self.nNeighbors, metric=self.distance, algorithm="brute")

    def update(self, userId: int, itemId: int, rating: float):
        userId = [userId]
        #Find first index of userId in userProfiles
        if userId in self.userProfiles:
            userIndex = self.userProfiles.index(userId)
        else:
            userIndex = len(self.userProfiles)
            self.userProfiles.append(userId)
            self.itemRatings.append({})
        
        #Insert new like
        self.itemRatings[userIndex][itemId] = rating

        #If like window size is too large, pop the oldest value
        if len(self.itemRatings[userIndex].keys()) > self.windowSize:
            self.itemRatings[userIndex].pop(list(self.itemRatings[userIndex].keys())[0])

        self.nn.fit(self.userProfiles)

    def reccomendItem(self, userId, itemAmount=20):
        userIndex = self.userProfiles.index([userId])
        if self.itemRatings[userIndex].keys() == 0:
            raise ValueError(f"No data on {userId}")
        
        #Get neareast neighbors
        _, neighborIndices = self.nn.kneighbors([self.userProfiles[userIndex]])
        neighborIndices = neighborIndices[0].tolist()

        #Removes same user from neighbors
        neighborIndices.remove(userIndex)

        totalRatings = {}
        
        for neighbor in neighborIndices:
            for item in self.itemRatings[neighbor].keys() - self.itemRatings[userIndex].keys():
                if item in totalRatings.keys():
                    totalRatings[item] += self.itemRatings[neighbor][item]
                else:
                    totalRatings[item] = self.itemRatings[neighbor][item]

        sortedItems = sorted(totalRatings.items(), key=lambda x: x[1], reverse=True)
        reccomendedItems = [itemId for itemId, _ in sortedItems[:itemAmount]]
        return reccomendedItems

    def distance(self, user1, user2):
        totalRatingDistance = 0
        user1Index = self.userProfiles.index(user1)
        user2Index = self.userProfiles.index(user2)
        user2Keys = 0

        for key in self.itemRatings[user1Index].keys():
            if key in self.itemRatings[user2Index].keys():
                user2Keys += 1
                totalRatingDistance += pow((self.itemRatings[user1Index][key] - self.itemRatings[user2Index][key]),2)
            else:
                totalRatingDistance += self.penalty
        return math.sqrt(totalRatingDistance)
