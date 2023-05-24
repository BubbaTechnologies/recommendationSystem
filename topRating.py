#Generates a list of the itemCount most popular items for each gender

import os
import sqlalchemy
import pandas as pd
import csv

itemCount = 25
monthsInterval = 1
daysInterval = 3

genders = {
    "female":0,
    "male":1,
    "boy":2,
    "girl":3,
    "kid":4,
    "unisex":5
}

def getRatings():
    engine = sqlalchemy.create_engine(f'mysql+mysqlconnector://{os.getenv("SERVER_USERNAME")}:{os.getenv("SERVER_PASSWORD")}@awseb-e-actsphbery-stack-awsebrdsdatabase-glefupggrhnl.csggsk1g25yj.us-east-1.rds.amazonaws.com:3306/ebdb')
    connection = engine.connect()
    for gender in genders.keys():
        df = pd.read_sql(f"SELECT ebdb.likes.id, clothing_id, rating, date_updated, date_created FROM ebdb.likes INNER JOIN ebdb.clothing ON ebdb.clothing.id = ebdb.likes.clothing_id WHERE ebdb.likes.date_updated >= CURRENT_DATE - INTERVAL '{daysInterval}' DAY AND ebdb.clothing.date_created >= CURRENT_DATE - INTERVAL '{monthsInterval}' MONTH AND ebdb.clothing.gender = {genders[gender]};",connection)
        #Get all unique clothing items with likes
        averageRatings = df.groupby('clothing_id')['rating'].mean()
        averageRatingsDf = pd.DataFrame({"clothing_id":averageRatings.index, "average_rating": averageRatings.values}).sort_values(by=["average_rating"], ascending=False).head(itemCount)
        with open(f"./offlineResults/{gender}Results.csv", "w") as file:
            writer = csv.writer(file)
            for clothing_id in averageRatingsDf["clothing_id"]:
                writer.writerow([clothing_id])
    connection.close()
    


