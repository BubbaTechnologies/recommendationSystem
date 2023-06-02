import asyncio
from collections import deque

class ReaderWriterLock:
    def __init__(self):
        self._readers = 0
        self._writers = 0
        self._lock = asyncio.Lock()
        self._write_queue = deque()
        self._readersConditions = asyncio.Condition(self._lock)
        self._writersConditions = asyncio.Condition(self._lock)

    async def acquire_read(self):
        await self._lock.acquire()
        try:
            while self._writers > 1 or len(self._write_queue) > 0:
                self._readersConditions.wait()
            self._readers += 1
        finally:
            self._lock.release()

    async def release_read(self):
        await self._lock.acquire()
        try:
            self._readers -= 1
            if self._readers == 0:
                self._writersConditions.notify_all()
        finally:
            self._lock.release()
       
    async def acquire_write(self, context):
        await self._lock.acquire()
        try:
            self._write_queue.append(context)
            while (self._readers > 0 or self._writers > 0) and self._write_queue[0] == context:
                self._writersConditions.wait()
            self._writers += 1
            self._write_queue.popleft()
        finally:
            self._lock.release()

    async def release_write(self):
        await self._lock.acquire()
        try:
            self._writers -= 1
            self._writersConditions.notify_all()
            if len(self._write_queue) <= 0:
                self._readersConditions.notify_all()
        finally:
            self._lock.release()
