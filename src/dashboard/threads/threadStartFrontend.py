# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC orginazers
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
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")

import subprocess
import os
from src.templates.threadwithstop import ThreadWithStop

class ThreadStartFrontend(ThreadWithStop):

    # ================================ INIT ===============================================

    def __init__(self, logger, project_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")):
        """Thread for managing an Angular development server.
        
        Args:
            project_path (str): The file path to the Angular project directory.
        """
        
        self.project_path = project_path
        self.logger= logger
        super().__init__()
    
    # ================================= RUN ===============================================

    def run(self):
        """Overrides the Thread.run. Starts the Angular server and monitors the _running flag."""

        try:
            subprocess.run(f"cd {self.project_path} && npm start", shell=True, check=True)
            self.logger.info("Angular server started successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to start the Angular development server: {e}")

    # ================================ STOP ===============================================

    def stop(self):
        """Stops the Angular development server if running."""

        self.logger.warning("Angular server stopped.")

# ================================= EXAMPLE ===============================================

if __name__ == "__main__":
    # Replace '../frontend/' with the actual path to your Angular project
    angular_thread = ThreadStartFrontend("../frontend/")
    angular_thread.start()
    input("Press Enter to stop the server...")
    angular_thread.stop()
    angular_thread.join()
