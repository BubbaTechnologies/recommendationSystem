import datetime
from typing import List

clothingDict = {}

def getMessage(message: str) -> str:
    return datetime.datetime.now().strftime("%H:%M:%S") + ": " + message

