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
        self.reactor.listenUDP(self.listenPort, self.udp_factory)
        self.tcp_factory.stopListening()

    def serverFound(self, address, port):
        """If the server was found we stop the factory listening and we connect the reactor and we start the periodic task"""
        self.reactor.connectTCP(address, port, self.tcp_factory)
        self.udp_factory.stopListening()
        self.period_task.start()

    def locsysConnect(self, deviceID, IPandPORT):
        """In this method we get the port and ip and we connect the reactor"""
        ip, port = IPandPORT.split(":")
        print(ip, port, deviceID)
        self.tcp_factory_locsys = tcpLocsys(id, self.queue)
        self.reactor.connectTCP(ip, int(port), self.tcp_factory_locsys)

    # ======================================= RUN ==========================================
    def run(self):
        self.reactor.run(installSignalHandlers=False)

    # ====================================== STOP ==========================================
    def stop(self):
        self.reactor.stop()
        super(threadTrafficCommunication, self).stop()
