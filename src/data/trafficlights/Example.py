#
#  ******************************************************************************
#  * @file     Example.py
#  * @author   RBRO/PJ-IU
#  * @version  V0.0.1
#  * @date     14-01-2020 GMOIS
#  * @brief    This file contains an example for gettting semaphore states.
#  ******************************************************************************
#

# Module imports
import time
# Module required for getting semaphore broadcast messages
import Listener

## Method for running the listener example.
#  @param none
def runListener():

    # Semaphore colors list
    colors = ['red','yellow','green']   

    # Get time stamp when starting tester
    start_time = time.time()
    # Create listener object
    Semaphores = Listener.listener()
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
        time.sleep(0.5)
    # Stop the listener
    Semaphores.stop()

if __name__ == "__main__":
    runListener()
