from onlineKNeighborClassifier import OnlineKNeighborClassifier
import pandas as pd
import sqlalchemy
import os
import tools
import operator

def totalRatingCalculation(reccomendationScore, newestUploadScore, averageRatingsScore):
    return 0.6 * (reccomendationScore) + 0.25 * (newestUploadScore) + .15 * (averageRatingsScore)

oknn = OnlineKNeighborClassifier(50, 2, 1000)
gender = "female"
clothingType = "bottom"

engine = sqlalchemy.create_engine(f'mysql+mysqlconnector://{os.getenv("SERVER_USERNAME")}:{os.getenv("SERVER_PASSWORD")}@awseb-e-actsphbery-stack-awsebrdsdatabase-glefupggrhnl.csggsk1g25yj.us-east-1.rds.amazonaws.com:3306/ebdb')
connection = engine.connect()
df = pd.read_sql("SELECT ebdb.likes.user_id, ebdb.likes.clothing_id, ebdb.likes.rating, date_created FROM ebdb.likes INNER JOIN ebdb.clothing ON ebdb.clothing.id = ebdb.likes.clothing_id;",connection)

for _, row in df.iterrows():
    oknn.update(row["user_id"], row["clothing_id"],row["rating"])

algorithmReccomendations = oknn.reccomendItem(11)
print(algorithmReccomendations)

#Performs sorting: .7(Previous Ranking) + .2(Newest Upload) + .1(Highest Rating Per User Ratio)
averageRatingsSeries = df.groupby('clothing_id')['rating'].mean()
averageRatingsRank = []

uploads = df.groupby("clothing_id")["date_created"]
uploadRatingsRank = []

for i in algorithmReccomendations:
    averageRatingsRank.append((i,averageRatingsSeries[i]))
    uploadRatingsRank.append((i, uploads.get_group(i).iloc[0]))
    
averageRatingsRank = sorted(averageRatingsRank, key=operator.itemgetter(1), reverse=True)
uploadRatingsRank = sorted(uploadRatingsRank, key=operator.itemgetter(1), reverse=True)

rankDict = {}

for i in range(len(uploadRatingsRank)):
    rankDict[uploadRatingsRank[i][0]] = (0,len(uploadRatingsRank) - i,0)

for i in range(len(averageRatingsRank)):
    rankDict[averageRatingsRank[i][0]] = (0,rankDict[averageRatingsRank[i][0]][1],len(averageRatingsRank) - i)

for i in range(len(algorithmReccomendations)):
    rankDict[algorithmReccomendations[i]] = (len(algorithmReccomendations) - i,rankDict[algorithmReccomendations[i]][1],rankDict[algorithmReccomendations[i]][2])

totalRank = []
for i in rankDict.keys():
    rankTuple = rankDict[i]
    totalRank.append((i, totalRatingCalculation(rankTuple[0], rankTuple[1], rankTuple[2])))
totalRank = sorted(totalRank, key=operator.itemgetter(1), reverse=True)

#Removes all clothing that don't fit gender and type
for i in range(len(totalRank)):
    item = totalRank[i][0]
    totalRank[i] = item
    genderType = connection.execute(sqlalchemy.text(f"SELECT gender, clothing_type FROM ebdb.clothing WHERE id = {item}")).fetchone()
    if tools.typeToInt(clothingType) != genderType[1] or tools.genderToInt(gender) != genderType[0]:
        algorithmReccomendations.remove(item)

print(totalRank)



