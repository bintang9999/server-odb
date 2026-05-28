import urllib.request
import urllib.parse
import time
import random

# Target ngrok URL
URL = "https://acellular-bulbously-agnus.ngrok-free.dev"

# Generate unique session ID for this run
session_id = str(int(time.time() * 1000))
device_id = "dummy_device_123"

print(f"Starting dummy data sender to: {URL}")
print(f"Session ID: {session_id}")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        # Generate random dummy telemetry values
        data = {
            "session": session_id,
            "id": device_id,
            "k0c": str(random.randint(800, 3000)),      # RPM (Engine speed)
            "k0d": str(random.randint(0, 110)),        # Speed (km/h)
            "k04": str(random.randint(15, 75)),        # Engine Load (%)
            "k05": str(random.randint(80, 96)),        # Coolant Temp (C)
            "k11": str(random.randint(5, 50)),         # Throttle Position (%)
            "k2f": "65.5",                             # Fuel Level (%)
            "kff1005": str(-6.2000 + random.uniform(-0.005, 0.005)),  # Latitude (Simulated coordinates)
            "kff1006": str(106.8160 + random.uniform(-0.005, 0.005))  # Longitude
        }
        
        # Build query params and full URL
        query_string = urllib.parse.urlencode(data)
        full_url = f"{URL}?{query_string}"
        
        try:
            # Make the HTTP GET request
            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                response_text = response.read().decode('utf-8')
                print(f"[{time.strftime('%H:%M:%S')}] Data Sent! Response: {response_text} (RPM: {data['k0c']}, Speed: {data['k0d']} km/h)")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to send data: {e}")
            
        time.sleep(2)  # Send every 2 seconds
except KeyboardInterrupt:
    print("\nStopped sender.")
