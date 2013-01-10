import functools
import threading
import Queue as queue

from PyQt4 import QtCore


class ThreadPool(object):
    
    def __init__(self, max_workers=4, lifo=False):
        self._max_workers = max_workers
        self._workers = []
        self._worker_lock = threading.Lock()
        self._queue = queue.LifoQueue() if lifo else queue.Queue()
        self._running = True
    
    def __del__(self):
        self._running = False
    
    def submit(self, func, *args, **kwargs):
        self._queue.put((func, args, kwargs))
        with self._worker_lock:
            if len(self._workers) < self._max_workers:
                worker = QtCore.QThread()
                worker.run = functools.partial(self._target, worker)
                worker.start()
                self._workers.append(worker)
    
    def _target(self, thread):
        while self._running:
            try:
                func, args, kwargs = self._queue.get(True, 1.0) # 1s block
            except queue.Empty:
                with self._worker_lock:
                    self._workers.remove(thread)
                return
            func(*args, **kwargs)

