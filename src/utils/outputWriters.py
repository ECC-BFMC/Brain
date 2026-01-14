import threading

class QueueWriter:
    def __init__(self, queue):
        self.queue = queue
        # _local will be created on demand to support pickling

    @property
    def local(self):
        if not hasattr(self, '_local'):
            self._local = threading.local()
        return self._local

    def __getstate__(self):
        state = self.__dict__.copy()
        if '_local' in state:
            del state['_local']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def write(self, msg):
        if not hasattr(self.local, 'buffer'):
            self.local.buffer = ""
        
        self.local.buffer += msg
        
        while "\n" in self.local.buffer:
            line, self.local.buffer = self.local.buffer.split("\n", 1)
            # Only add non-empty messages to avoid clutter
            if line.strip():
                self.queue.put(line)

    def flush(self):
        pass  # Needed for file-like interface

class MultiWriter:
    def __init__(self, *writers):
        self.writers = writers

    def write(self, msg):
        for w in self.writers:
            w.write(msg)

    def flush(self):
        for w in self.writers:
            w.flush()
