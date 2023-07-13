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
        tosend = self.shrd_mem.get()
        for mem in tosend:
            if mem['finishflag']:
                msg = {"reqORinfo": "info", "type":mem['Command']}
                if mem['value1'] != 99.9: msg["value1"] = mem['value1']
                if mem['value2'] != 99.9: msg["value2"] = mem['value2']
                if mem['value3'] != 99.9: msg["value3"] = mem['value3']
                print(msg)
                res = self.tcp_factory.send_data_to_server(msg)
                if res:
                    mem['Command'] = "Command_"
                    mem['value1'] = 99.9
                    mem['value2'] = 99.9
                    mem['value3'] = 99.9
                    mem['finishflag'] = False
                else: break
