import os
import multiprocessing

DATABASE_NAME = "sys"
CONNECTION_STRING = f'mysql+mysqlconnector://{os.getenv("DB_USERNAME")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_ADDR_READER")}:{os.getenv("DB_PORT", 3306)}/{DATABASE_NAME}'

LIST_AMOUNT = 10

OTHER_INDEX = 10
GENDER_AMOUNT = 5

AVOID_INDEXS = [OTHER_INDEX, 7]

#Online Learning Parameters
WINDOW_SIZE = 50
N_NEIGHBORS = 2

#Offline Parameters
ITEM_COUNT = 25
MONTHS_INTERVAL = 2
DAYS_INTERVAL = 14

#Random Parameters
RANDOM_CLOTHING_CHANCE = 1
RANDOM_UPPER_BOUND = 100
WEEKS_AGO = 3

MAX_THREADS = multiprocessing.cpu_count()