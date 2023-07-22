import os
import multiprocessing

DATABASE_NAME = "sys"
CONNECTION_STRING = f'mysql+mysqlconnector://{os.getenv("DB_USERNAME")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_ADDR_READER")}:{os.getenv("DB_PORT", 3306)}/{DATABASE_NAME}'

#Online Learning Parameters
WINDOW_SIZE = 50
N_NEIGHBORS = 2

#Offline Parameters
ITEM_COUNT = 25
MONTHS_INTERVAL = 2
DAYS_INTERVAL = 14

#Random Parameters
RANDOM_CLOTHING_CHANCE = 0.4
RANDOM_UPPER_BOUND = 1000
WEEKS_AGO = 3

MAX_THREADS = multiprocessing.cpu_count() 