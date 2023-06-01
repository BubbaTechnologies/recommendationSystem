import threading
import asyncio

class ReaderWriterLock:
    def __init__(self):
        self.lock = threading.RLock()
        self.writer_lock = asyncio.Lock()
        self.reader_count = 0

    async def acquire_read(self):
        with self.lock:
            self.reader_count += 1
            if self.reader_count == 1:
                self.writer_lock.acquire()

    def release_read(self):
        with self.lock:
            self.reader_count -= 1
            if self.reader_count == 0:
                self.writer_lock.release()

    async def acquire_write(self):
        self.writer_lock.acquire()

    def release_write(self):
        self.writer_lock.release()