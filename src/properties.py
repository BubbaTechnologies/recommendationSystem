import os
import multiprocessing

CONNECTION_STRING = f'mysql+mysqlconnector://{os.getenv("DB_USERNAME")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_ADDR_READER")}:3306/sys'
DATABASE_NAME = "sys"

#Online Learning Parameters
WINDOW_SIZE = 50
N_NEIGHBORS = 2
PENALTY = 1000

#Offline Parameters
ITEM_COUNT = 25
MONTHS_INTERVAL = 1
DAYS_INTERVAL = 3

#Random Parameters
RANDOM_CLOTHING_CHANCE = 0.4
RANDOM_UPPER_BOUND = 1000

MAX_THREADS = multiprocessing.cpu_count() 