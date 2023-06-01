# Reccomendation System

## Routes
### / (GET)
Description: Returns to www.peachsconemarket.com
### /reccomendation
METHOD: GET
Paremeters: userId (required), gender (required), clothingType (optional)
Description: Recommends item clothing. If no item can be reccomended HTTP Status Code 204 will be returned.
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

## Offline Reccomendation System
Description: Ranks all items added within the last 30 days and reccomends top 10.

## Online Reccomendation System
Description: Gets items from 2 nearest neighbors, ranks them, and provides reccomendations.