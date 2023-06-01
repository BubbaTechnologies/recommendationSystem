import threading
import asyncio

class ReaderWriterLock:
    def __init__(self):
        self.read_lock = threading.Lock()
        self.write_lock = asyncio.Lock()
        self.reader_count = 0

    async def acquire_read(self):
        async with self.read_lock:
            self.reader_count += 1
            if self.reader_count == 1:
                await self.write_lock.acquire()
                print("Acquired")

    def release_read(self):
        with self.read_lock:
            self.reader_count -= 1
            if self.reader_count == 0:
                self.write_lock.release()
                print("Release")

    async def acquire_write(self):
        await self.write_lock.acquire()

    def release_write(self):
        self.write_lock.release()