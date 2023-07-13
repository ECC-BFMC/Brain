from twisted.internet import  protocol
import json
import time

# The server itself. Creates a new Protocol for each new connection and has the info for all of them.
class tcpClient(protocol.ClientFactory):
    def __init__(self, connectionBrokenCllbck, locsysConnectCllbck, locsysID):
        self.connection = None
        self.isConnected = False
        self.retry_delay = 1
        self.connectionBrokenCllbck = connectionBrokenCllbck
        self.locsysConnectCllbck = locsysConnectCllbck
        self.locsysID = locsysID

    def clientConnectionLost(self, connector, reason):
        print("Connection lost with server ", self.connectiondata, " Retrying in ", self.retry_delay, " seconds... (Check password match, IP or server availability)")
        self.connectiondata = None
        self.connected = False
        self.connectionBrokenCllbck()
    
    def clientConnectionFailed(self, connector, reason):
        print("Connection failed. Retrying in", self.retry_delay, "seconds... Possible server down or incorrect IP:port match")
        time.sleep(self.retry_delay)
        connector.connect()

    def buildProtocol(self, addr):
        conn = SingleConnection()
        conn.factory = self
        return conn
    
    def stopListening(self):
        super().stopListening()

    def send_data_to_server(self, message):
        # if self.isConnected == True:
        #     self.connection.send_data(message)
        #     return True
        # else:
        #     return False
        return True
    
    def receive_data_from_server(self, message):
        msg = json.loads(message)
        if msg["reqORinfo"] == "request":
            if msg["type"] == "locsysDevice":
                if "response" in msg:
                    self.locsysConnectCllbck(msg["response"])
                else:
                    print(msg["error"])
            else:
                self.send_data_to_client("Message not recognized, 'type' miss-match")
        else:
            self.send_data_to_client("Message not recognized, 'reqORinfo' missing")
        print("Received data from ", message)


# One class is generated for each new connection
class SingleConnection(protocol.Protocol):
    def connectionMade(self):
        peer = self.transport.getPeer()
        self.connectiondata = peer.host + ":" + str(peer.port)
        self.factory.connection = self
        msg = {"reqORinfo": "request", "type":"locsysDevice", "DeviceID":self.factory.locsysID}
        self.send_data(msg)
        print("Connection with server established : ", self.connectiondata)

    def dataReceived(self, data):
        self.factory.receive_data_from_server(data.decode())

    def send_data(self, message):
        self.transport.write(message.encode())