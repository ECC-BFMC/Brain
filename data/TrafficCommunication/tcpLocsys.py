from twisted.internet import  protocol
import json
import time

# The server itself. Creates a new Protocol for each new connection and has the info for all of them.
class tcpLocsys(protocol.ClientFactory):
    def __init__(self, sendPipe):
        self.connection = None
        self.retry_delay = 1
        self.sendPipe = sendPipe

    def clientConnectionLost(self, connector, reason):
        print("Connection lost with server ", self.connectiondata, " Retrying in ", self.retry_delay, " seconds... (Check password match, IP or server availability)")
        self.connectiondata = None
    
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
    
    def receive_data_from_server(self, message):
        self.sendPipe.send(message)
        print("Received data from ", message)


# One class is generated for each new connection
class SingleConnection(protocol.Protocol):
    def connectionMade(self):
        peer = self.transport.getPeer()
        self.connectiondata = peer.host + ":" + str(peer.port)
        self.factory.connection = self
        print("Connection with server established : ", self.connectiondata)

    def dataReceived(self, data):
        self.factory.receive_data_from_server(data.decode())
