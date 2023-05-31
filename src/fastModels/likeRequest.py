from pydantic import BaseModel

class LikeRequest(BaseModel):
    userId:int
    clothingId: int
    rating: float