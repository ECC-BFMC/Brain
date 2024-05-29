# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
from twisted.internet import reactor
from src.templates.threadwithstop import ThreadWithStop
from src.data.TrafficCommunication.threads.udpListener import udpListener
from src.data.TrafficCommunication.threads.tcpClient import tcpClient
from src.data.TrafficCommunication.threads.tcpLocsys import tcpLocsys
from src.data.TrafficCommunication.useful.periodicTask import periodicTask


class threadTrafficCommunication(ThreadWithStop):
    """Thread which will handle processTrafficCommunication functionalities

    Args:
        shrd_mem (sharedMem): A space in memory for mwhere we will get and update data.
        queuesList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        deviceID (int): The id of the device.
        decrypt_key (String): A path to the decription key.
    """

    # ====================================== INIT ==========================================
    def __init__(self, shrd_mem, queueslist, deviceID, decrypt_key):
        super(threadTrafficCommunication, self).__init__()
        self.listenPort = 9000
        self.tcp_factory = tcpClient(
            self.serverDisconnect, self.locsysConnect, deviceID
        )
        self.udp_factory = udpListener(decrypt_key, self.serverFound)
        self.queue = queueslist["General"]
        self.period_task = periodicTask(1, shrd_mem, self.tcp_factory)
        self.reactor = reactor
        self.reactor.listenUDP(self.listenPort, self.udp_factory)

    # =================================== CONNECTION =======================================
    def serverDisconnect(self):
        """If the server discconects we stop the factory listening and we start the reactor listening"""
        # self.reactor.listenUDP(self.listenPort, self.udp_factory)
        self.tcp_factory.stopListening()

    def serverFound(self, address, port):
        """If the server was found we stop the factory listening and we connect the reactor and we start the periodic task"""
        self.reactor.connectTCP(address, port, self.tcp_factory)
        # self.udp_factory.stopListening()
        self.period_task.start()

    def locsysConnect(self, deviceID, IPandPORT):
        """In this method we get the port and ip and we connect the reactor"""
        ip, port = IPandPORT.split(":")
        print(ip, port, deviceID)
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> e52a7757083565575dca9ee39896d3895fd38e29
>>>>>>> fe38f2896e92ca1a7a143585e198e8ce5f2b8b18
>>>>>>> 484bad0f91d4d3232a8d2db53e6a790eaa9c4390
>>>>>>> 9f158333fbaa1f1a3abf903cd8b87f40c81ac184
>>>>>>> 6519bd656912fa5fc5037b5c6894e84434d19d19
>>>>>>> ee658f9826666bf894b22c061e0d7a2460a2119e
>>>>>>> 2fccfd2e5502feeadfff5d9f47456b6423f12bcf
>>>>>>> 1424611625d94ad1049aade0d1d2ead4ed862766
>>>>>>> ad26c60c210984dd6d64cb937825189314c7296a
>>>>>>> e869ca624bad2ca0f6ddf41b74f20542d35b8ebb
        self.tcp_factory_locsys = tcpLocsys(id, self.queue)
=======
        # self.tcp_factory_locsys = tcpLocsys(id, self.queue)
        self.tcp_factory_locsys = tcpLocsys(deviceID, self.queue)
>>>>>>> 7f0d8187eee98a81dd404308b4f7846168b19f09
        self.reactor.connectTCP(ip, int(port), self.tcp_factory_locsys)

    # ======================================= RUN ==========================================
    def run(self):
        self.reactor.run(installSignalHandlers=False)

    # ====================================== STOP ==========================================
    def stop(self):
        self.reactor.stop()
        super(threadTrafficCommunication, self).stop()
