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
from twisted.internet import task


class periodicTask(task.LoopingCall):
    def __init__(self, interval, shrd_mem, tcp_factory):
        super().__init__(self.periodicCheck)
        self.interval = interval
        self.shrd_mem = shrd_mem
        self.tcp_factory = tcp_factory

    def start(self):
        super().start(self.interval)

    def stop(self):
        if self.running:
            super().stop()

    def periodicCheck(self):
        # Will create one of the following structures:
        # {"reqORinfo": "req",  "type":"locsysDevice"}
        # {"reqORinfo": "info", "type":"devicePos", "value1":x, "value2":y}
        # {"reqORinfo": "info", "type":"deviceRot", "value1": theta}
        # {"reqORinfo": "info", "type":"deviceSpeed", "value1":km/h}
        # {"reqORinfo": "info", "type":"historyData", "value1":id, "value2":x, "value3":y}

        if self.tcp_factory.isConnected():
            tosend = self.shrd_mem.get()
            for mem in tosend:
                self.tcp_factory.send_data_to_server(mem)
