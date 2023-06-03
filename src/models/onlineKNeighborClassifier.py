from sklearn.neighbors import NearestNeighbors
from typing import List
import math

MULTIPLIER_DENOMINATOR = 5

class OnlineKNeighborClassifier:
    def __init__(self, windowSize: int, nNeighbors: int, penalty: int):
        self.windowSize = windowSize
        self.nNeighbors = nNeighbors + 1
        #The larger the number the greater the penalty
        self.penalty = penalty
        self.userProfiles:List[int] = []
        self.itemRatings = []
        self.nn = NearestNeighbors(n_neighbors=self.nNeighbors, metric=self.distance, algorithm="brute", n_jobs=-1)

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

    def recommendItem(self, userId, itemAmount=20):
        userIndex = self.userProfiles.index([userId])
        if self.itemRatings[userIndex].keys() == 0:
            raise ValueError(f"No data on {userId}")
        
        #Get neareast neighbors
        _, neighborIndices = self.nn.kneighbors([self.userProfiles[userIndex]])
        neighborIndices = neighborIndices[0].tolist()

        #Removes same user from neighbors
        neighborIndices.remove(userIndex)

        totalRatings = {}
        userKeys = self.itemRatings[userIndex].keys()
        
        for neighbor in neighborIndices:
            for item in self.itemRatings[neighbor].keys():
                if item not in userKeys:
                    if item in totalRatings.keys():
                        totalRatings[item] += self.itemRatings[neighbor][item]
                    else:
                        totalRatings[item] = self.itemRatings[neighbor][item]

        sortedItems = sorted(totalRatings.items(), key=lambda x: x[1], reverse=True)
        return [itemId for itemId, _ in sortedItems[:itemAmount]]
    
    def userInModel(self,userId:int) -> bool:
        if [userId] in self.userProfiles and len(self.itemRatings[self.userProfiles.index([userId])].keys()) > 10:
            return True
        else:
            return False

    def distance(self, user1, user2):
        totalRatingDistance = 0
        user1Index = self.userProfiles.index(user1)
        user2Index = self.userProfiles.index(user2)
        user2Keys = 0

        multiplier = len(self.itemRatings[user1Index].keys())/MULTIPLIER_DENOMINATOR

        for key in reversed(self.itemRatings[user1Index].keys()):
            if key in self.itemRatings[user2Index].keys():
                user2Keys += 1
                totalRatingDistance += pow(multiplier * (self.itemRatings[user1Index][key] - self.itemRatings[user2Index][key]),2)
            else:
                totalRatingDistance += self.penalty
            multiplier -= 1/MULTIPLIER_DENOMINATOR
        return math.sqrt(totalRatingDistance)
