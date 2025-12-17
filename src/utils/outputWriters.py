class QueueWriter:
    def __init__(self, queue):
        self.queue = queue

    def write(self, msg):
        # Only add non-empty messages to avoid clutter
        if msg.strip():
            self.queue.put(msg)

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
