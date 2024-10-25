import re
import subprocess

def get_ip_address():
    try:
        ip_output = subprocess.check_output("hostname -I", shell=True)
        ip_address = ip_output.decode('utf-8').strip().split()[0]
        return ip_address
    except subprocess.CalledProcessError:
        print("Could not retrieve IP address.")
        return None

def replace_ip_in_file(file_path, new_ip):
    # Regular expression pattern to match IP addresses
    ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'

    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Replace the old IP address with the new one
    updated_content = re.sub(ip_pattern, new_ip, content)

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.write(updated_content)

    print(f"Replaced IP address in {file_path} with {new_ip}")

# Usage
file_path = './src/dashboard/frontend/src/app/webSocket/web-socket.service.ts'  # Replace with the path to your file
new_ip = get_ip_address()

if new_ip:
    replace_ip_in_file(file_path, new_ip)
else:
    print("Failed to retrieve IP address.")
