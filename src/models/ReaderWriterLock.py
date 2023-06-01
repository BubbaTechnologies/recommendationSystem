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

    async def acquire_read(self):
        await self.lock.acquire()
        while self.writers > 0 or self.write_requested:
            self.readersConditions.wait()
        self.readers += 1
        await self.lock.release()
        

    async def release_read(self):
        await self.lock.acquire()
        self.readers -= 1
        if self.readers == 0:
            self.writersConditions.notify()
        await self.lock.release()
    
    async def acquire_write(self):
        await self.lock.acquire()
        self.write_queue.append(threading.get_ident())
        self.write_requested = True
        while self.writers > 0 or self.readers > 0 or self.write_queue[0] != threading.get_ident():
            self.writersConditions.wait()
        self.writers += 1
        await self.lock.release()
        

    async def release_write(self):
        await self.lock.acquire()
        self.writers -= 1
        if self.writers == 0:
            self.write_queue.popleft()
            self.write_requested = len(self.write_queue) > 0
            self.writersConditions.notify_all()
            self.readersConditions.notify_all()
        await self.lock.release()
            
            
            