import time

def get_cpu_temperature():
    # Read the temperature from the system file
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
    # Convert the temperature to Celsius
    return float(temp) / 1000.0

try:
    while True:
        temp = get_cpu_temperature()
        print(f"CPU Temperature: {temp:.2f}°C")
        time.sleep(1)  # Wait for 1 second before reading the temperature again
except KeyboardInterrupt:
    print("Temperature monitoring stopped.")
