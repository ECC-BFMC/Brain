from twisted.internet import protocol
import useful.keyDealer as keyDealer

class udpListener(protocol.DatagramProtocol):
    def __init__(self, decrypt_key, serverfound):
        decrypt_key = decrypt_key
        self.key = keyDealer.load_public_key(decrypt_key)
        self.servergoundCllback = serverfound     

    def startProtocol(self):
        print("Looking for server")

    def datagramReceived(self, datagram, address):
        # Handle received datagram
        try:
            dat = datagram.split(b"(-.-)")
            if len(dat) != 2:
                raise Exception('Plaintext or signature not present')
            a = keyDealer.verify_data(self.pub_key,dat[1],dat[0])
            if not a:
                raise Exception('signature not valid')
            msg = dat[1].decode().split(":")
            port= int(msg[1])
            self.servergoundCllback(address.host, port)
        except Exception as e:
            print(e)
        
    def stopListening(self):
        super().stopListening()