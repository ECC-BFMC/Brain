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

import re
import subprocess

class IPManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def get_ip_address(self):
        """Retrieve the current IP address of the machine."""
        try:
            ip_output = subprocess.check_output("hostname -I", shell=True)
            ip_address = ip_output.decode('utf-8').strip().split()[0]
            return ip_address
        except subprocess.CalledProcessError:
            print("Could not retrieve IP address.")
            return None

    def replace_ip_in_file(self):
        """Replace the IP address in the specified file if it differs from the current IP."""
        new_ip = self.get_ip_address()
        if not new_ip:
            print("Failed to retrieve IP address.")
            return

        # Regular expression pattern to match IP addresses
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'

        # Read the file content
        try:
            with open(self.file_path, 'r') as file:
                content = file.read()
        except FileNotFoundError:
            print(f"File {self.file_path} not found.")
            return

        # Search for the current IP address in the file
        current_ip_match = re.search(ip_pattern, content)
        
        if current_ip_match:
            current_ip = current_ip_match.group()
            
            # Check if the current IP is different from the new IP
            if current_ip == new_ip:
                print(f"The IP address in {self.file_path} is already {new_ip}. No changes made.")
                return
            else:
                # Replace the old IP address with the new one
                updated_content = re.sub(ip_pattern, new_ip, content)
                
                # Write the updated content back to the file
                with open(self.file_path, 'w') as file:
                    file.write(updated_content)
                
                print(f"Replaced IP address in {self.file_path} with {new_ip}")
        else:
            print(f"No IP address found in {self.file_path}.")


