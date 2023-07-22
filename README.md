# Reccomendation System
## Enviroment Variables
- ```DB_ADDR_READER```: Address of read only database.
- ```DB_USERNAME```: Username for database.
- ```DB_PASSWORD```: Password for database.
- ```DB_PORT```: Port for database.

## Properties
- ```CONNECTION_STRING```: String to connect to database.
- ```DATABASE_NAME```: Main database name.
- ```WINDOW_SIZE```: Amount of liked clothing to keep in memory per user. 
- ```N_NEIGHBORS```: Nearest neighbors to pull clothing from.
- ```ITEM_COUNT```: Amount of items to rank offline.
- ```MONTHS_INTERVAL```: Pulls clothing for offline rankings from the previous ```MONTHS_INTERVAL``` months.
- ```DAYS_AGO```: Pulls clothing for offline rankings that has been liked in previous ```DAYS_AGO``` days.
- ```RANDOM_CLOTHING_CHANCE```: Chance that random clothing is selected.
- ```RANDOM_UPPER_BOUND```: The amount of times to try to find a random clothing that has not been liked.
- ```WEEKS_AGO```: Pulls clothing for random selection from last ```WEEKS_AGO``` weeks.
- ```MAX_THREADS```: Amount of threads the service can use.

## Offline Reccomendation System
Description: Ranks all items added within the last 30 days and reccomends top 10.

## Online Reccomendation System
Description: Gets items from 2 nearest neighbors, ranks them, and provides reccomendations.

## Routes
### / (GET)
Description: Returns to www.peachsconemarket.com
### /recommendation
METHOD: GET
Paremeters: userId (required), gender (required), clothingType (optional)
Description: Recommends item clothing. If no item can be recommended HTTP Status Code 204 will be returned.
Response:
```
{
    "clothingId":int
}
```
### /like 
Method: POST
Content-Type: application/json
JSON Data: 
```
{
    "userId":int
    "clothingId":int
    "rating":float
}
```