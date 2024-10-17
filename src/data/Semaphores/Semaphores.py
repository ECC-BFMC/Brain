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

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")

from src.templates.workerprocess import WorkerProcess
from src.data.Semaphores.threads.threadSemaphores import (
    threadSemaphores,
)

class processSemaphores(WorkerProcess):
    """This process will receive the location of the other cars and the location and the state of the semaphores.
    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
    """

    # ====================================== INIT ==========================================
    def __init__(self, queueList, logging, debugging = False):
        self.queuesList = queueList
        self.logging = logging
        self.debugging = debugging
        super(processSemaphores, self).__init__(self.queuesList)

    # ===================================== STOP ==========================================
    def stop(self):
        """Function for stopping threads and the process."""

        for thread in self.threads:
            thread.stop()
            thread.join()
        super(processSemaphores, self).stop()

    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializing methods and start the threads."""

        super(processSemaphores, self).run()

    # ===================================== INIT TH ======================================
    def _init_threads(self):
        """Create the thread and add to the list of threads."""

        CarsSemTh = threadSemaphores(self.queuesList, self.logging, self.debugging)
        self.threads.append(CarsSemTh)


# =================================== EXAMPLE =========================================

if __name__ == "__main__":
    from multiprocessing import Queue

    queueList = {
        "Critical": Queue(),  # Queue for critical messages
        "Warning": Queue(),  # Queue for warning messages
        "General": Queue(),  # Queue for general messages
        "Config": Queue(),  # Queue for configuration messages
    }

    allProcesses = list()
    process = processSemaphores(queueList)
    process.start()

    x = range(6)
    for n in x:
        print(queueList["General"].get())  # Print general messages

    process.stop()