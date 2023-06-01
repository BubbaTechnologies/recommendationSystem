import threading

class ReaderWriterLock:
    def __init__(self):
        self.lock = threading.RLock()
        self.reader_count = 0

    def acquire_read(self):
        with self.lock:
            self.reader_count += 1
            if self.reader_count == 1:
                self.lock.acquire()

    def release_read(self):
        with self.lock:
            self.reader_count -= 1
            if self.reader_count == 0:
                self.lock.release()

    def acquire_write(self):
        self.lock.acquire()

    def release_write(self):
        self.lock.release()