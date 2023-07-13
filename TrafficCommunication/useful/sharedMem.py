from multiprocessing        import RawArray, RLock
import numpy                as np

class sharedMem():
    def __init__(self, mem_size = 20):
        self.lock = RLock()
        shared_memory_shape = np.dtype([('Command', 'U12'), ('value1', np.float16), ('value2', np.float16), ('value3', np.float16), ('finishflag', np.bool)])
        array = RawArray('c',mem_size * shared_memory_shape.itemsize)
        shared_memory = np.frombuffer(array, dtype=shared_memory_shape)

        self.shared_memory = shared_memory.reshape(mem_size)

        self.mem_size = mem_size
        self.lastMem = 0
        
        # By acquiring the lock, you can put the values into the shared memory. The periodictask will run through them periodically and check
        
        for mem in self.shared_memory:
            with self.lock:  # Acquire the lock using get_lock()
                mem['Command'] = "Command_"
                mem['value1'] = -99.9
                mem['value2'] = -99.9
                mem['value3'] = -99.9
                mem['finishflag'] = False

    def insert(self, msg, values):
        with self.lock:
            self.shared_memory[self.lastMem]['Command'] = msg
            if len(values) > 0: self.shared_memory[self.lastMem]['value1'] = values[0]
            if len(values) > 1: self.shared_memory[self.lastMem]['value2'] = values[1]
            if len(values) > 2: self.shared_memory[self.lastMem]['value3'] = values[2]
            self.shared_memory[self.lastMem]['finishflag'] = True
        self.lastMem += 1
        if self.lastMem == self.mem_size: self.lastMem = 0
    
    def get(self):
        vals = []
        with self.lock:
            for mem in self.shared_memory:
                if mem['finishflag']:
                    vals.append(mem)
                    # msg = {"reqORinfo": "info", "type":mem['Command']}
                    # if mem['value1'] != 99.9: msg["value1"] = mem['value1']
                    # if mem['value2'] != 99.9: msg["value2"] = mem['value2']
                    # if mem['value3'] != 99.9: msg["value3"] = mem['value3']
                    # print(msg)
                    # res = self.tcp_factory.send_data_to_server(msg)
        return vals
