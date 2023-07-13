import datetime
from typing import List

__gendersDict = {
    "female":0,
    "male":1,
    "boy":2,
    "girl":3,
    "kid":4,
    "unisex":5
}

__typeDict = {
   "top":0,
   "bottom":1,
   "shoes":2,
   "underclothing":3,
   "jacket":4,
   "skirt":5,
   "one piece":6,
   "accessory":7,
   "swimwear":8,
   "sleepwear":9,
   "other":10,
   "dress":11,
   "set":12
}

clothingDict = {}

def getGenders():
    return __gendersDict

def checkGender(string: str)->bool:
    if string.lower() in __gendersDict.keys():
        return True
    return False

def checkTypes(stringList: List[str])->bool:
    for clothingType in stringList:
        if clothingType.lower() in __typeDict.keys():
            return True
        return False

def genderToInt(string: str)->int:
    return __gendersDict[string.lower()]

def typeToInt(string: str)->List[int]:
    stringList = string.split(",")
    intList = []
    try:
        for x in stringList:
            intList.append(__typeDict[x.lower()])
    except:
        return None
    
    return intList

def getMessage(message: str) -> str:
    return datetime.datetime.now().strftime("%H:%M:%S") + ": " + message

