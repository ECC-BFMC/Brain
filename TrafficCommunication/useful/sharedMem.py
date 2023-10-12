# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
from multiprocessing import RawArray, Lock
import numpy as np


class sharedMem:
    def __init__(self, mem_size=20):
        self.lock = Lock()
        shared_memory_shape = np.dtype(
            [
                ("Command", "U12"),
                ("value1", np.float16),
                ("value2", np.float16),
                ("value3", np.float16),
                ("finishflag", np.bool_),
            ]
        )
        array = RawArray("c", mem_size * shared_memory_shape.itemsize)
        shared_memory = np.frombuffer(array, dtype=shared_memory_shape)

        self.shared_memory = shared_memory.reshape(mem_size)

        self.mem_size = mem_size
        self.lastMem = 0

        for mem in self.shared_memory:
            with self.lock:  # Acquire the lock using get_lock()
                mem["Command"] = "Command_"
                mem["value1"] = -99.9
                mem["value2"] = -99.9
                mem["value3"] = -99.9
                mem["finishflag"] = False

    def insert(self, msg, values):
        with self.lock:
            self.shared_memory[self.lastMem]["Command"] = msg
            if len(values) > 0:
                self.shared_memory[self.lastMem]["value1"] = values[0]
            if len(values) > 1:
                self.shared_memory[self.lastMem]["value2"] = values[1]
            if len(values) > 2:
                self.shared_memory[self.lastMem]["value3"] = values[2]
            self.shared_memory[self.lastMem]["finishflag"] = True
        self.lastMem += 1
        if self.lastMem == self.mem_size:
            self.lastMem = 0

    def get(self):
        vals = []
        with self.lock:
            for mem in self.shared_memory:
                if mem["finishflag"]:
                    msg = {"reqORinfo": "info", "type": mem["Command"]}
                    if mem["value1"] != 99.9:
                        msg["value1"] = float(mem["value1"])
                    if mem["value2"] != 99.9:
                        msg["value2"] = float(mem["value2"])
                    if mem["value3"] != 99.9:
                        msg["value3"] = float(mem["value3"])
                    mem["finishflag"] = False
                    vals.append(msg)
        return vals
