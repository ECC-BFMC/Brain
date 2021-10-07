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

# Module imports
import time
# Module required for getting semaphore broadcast messages
import trafficlights

## Method for running the listener example.
#  @param none
def runListener():

    # Semaphore colors list
    colors = ['red','yellow','green']   

    # Get time stamp when starting tester
    start_time = time.time()
    # Create listener object
    Semaphores = trafficlights.trafficlights()
    # Start the listener
    Semaphores.start()
    # Wait until 60 seconds passed
    while (time.time()-start_time < 60):
        # Clear the screen
        print("\033c")
        print("Example program that gets the states of each\nsemaphore from their broadcast messages\n")
        # Print each semaphore's data
        print("S1 color " + colors[Semaphores.s1_state] + ", code " + str(Semaphores.s1_state) + ".")
        print("S2 color " + colors[Semaphores.s2_state] + ", code " + str(Semaphores.s2_state) + ".")
        print("S3 color " + colors[Semaphores.s3_state] + ", code " + str(Semaphores.s3_state) + ".")
        print("S4 color " + colors[Semaphores.s4_state] + ", code " + str(Semaphores.s4_state) + ".")
        time.sleep(0.5)
    # Stop the listener
    Semaphores.stop()

if __name__ == "__main__":
    runListener()
