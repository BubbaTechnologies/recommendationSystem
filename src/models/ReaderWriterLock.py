import threading
import asyncio
from collections import deque

class ReaderWriterLock:
    def __init__(self):
        self.readers = 0
        self.writers = 0
        self.lock = asyncio.Lock()
        self.write_queue = deque()
        self.write_requested = False
        self.readersConditions = threading.Condition(self.lock)
        self.writersConditions = threading.Condition(self.lock)

    def acquire_read(self):
        with self.lock:
            while self.writers > 0 or self.write_requested:
                self.readersConditions.wait()
            self.readers += 1

    def release_read(self):
        with self.lock:
            self.readers -= 1
            if self.readers == 0:
                self.writersConditions.notify()
    
    def acquire_write(self):
        with self.lock:
            self.write_queue.append(threading.get_ident())
            self.write_requested = True
            while self.writers > 0 or self.readers > 0 or self.write_queue[0] != threading.get_ident():
                self.writersConditions.wait()
            self.writers += 1

    def release_write(self):
        with self.lock: 
            self.writers -= 1
            if self.writers == 0:
                self.write_queue.popleft()
                self.write_requested = len(self.write_queue) > 0
                self.writersConditions.notify_all()
                self.readersConditions.notify_all()
            
            
            