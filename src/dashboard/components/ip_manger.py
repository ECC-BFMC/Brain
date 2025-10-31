import subprocess
import re

class IpManager:
    @staticmethod
    def get_ip_address():
        """Retrieve the current IP address of the machine."""
        try:
            ip_output = subprocess.check_output("hostname -I", shell=True)
            ip_address = ip_output.decode('utf-8').strip().split()[0]
            return ip_address
        except subprocess.CalledProcessError:
            print("\033[1;97m[ Dashboard ] :\033[0m \033[1;93mWARNING\033[0m - Could not retrieve IP address.")
            return None


    @staticmethod
    def replace_ip_in_file(file_path="./src/dashboard/frontend/src/app/webSocket/web-socket.service.ts"):
        """Replace the IP address in the specified file if it differs from the current IP.
        
        Args:
            file_path (str): The path to the file to replace the IP address in.
        """
        new_ip = IpManager.get_ip_address()
        if not new_ip:
            print("\033[1;97m[ Dashboard ] :\033[0m \033[1;93mWARNING\033[0m - Failed to retrieve IP address.")
            return

        # regular expression pattern to match IP addresses
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'

        # read the file content
        try:
            with open(file_path, 'r') as file:
                content = file.read()
        except FileNotFoundError:
            print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;93mWARNING\033[0m - File {file_path} not found.")
            return

        # search for the current IP address in the file
        current_ip_match = re.search(ip_pattern, content)
        
        if current_ip_match:
            current_ip = current_ip_match.group()
            
            # check if the current IP is different from the new IP
            if current_ip == new_ip:
                print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;92mINFO\033[0m - IP already \033[94m{new_ip}\033[0m")
                return
            else:
                # replace the old IP address with the new one
                updated_content = re.sub(ip_pattern, new_ip, content)
                
                # write the updated content back to the file
                with open(file_path, 'w') as file:
                    file.write(updated_content)
                
                print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;92mINFO\033[0m - Updated to \033[94m{new_ip}\033[0m")
        else:
            print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;92mINFO\033[0m - No IP found")