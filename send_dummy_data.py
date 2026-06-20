import urllib.request
import urllib.parse
import time
import random
import math

# Target ngrok URL
URL = "https://acellular-bulbously-agnus.ngrok-free.dev"

# Generate unique session ID for this run
session_id = str(int(time.time() * 1000))
device_id = "dummy_device_123"

# ============================================================
# Simulated GPS Route (Jawa Tengah area)
# Starting point: ~Yogyakarta
# ============================================================
start_lat = -7.7956       # Latitude awal
start_lon = 110.3695      # Longitude awal
current_lat = start_lat
current_lon = start_lon
heading = random.uniform(0, 360)  # Arah awal (derajat)

def simulate_driving(speed_kmh):
    """Simulasi pergerakan GPS berdasarkan kecepatan dan heading."""
    global current_lat, current_lon, heading

    # Ubah heading sedikit (belok halus)
    heading += random.uniform(-15, 15)
    heading = heading % 360

    # Konversi speed ke perpindahan koordinat per detik
    # 1 derajat lat ~= 111km, 1 derajat lon ~= 111km * cos(lat)
    speed_ms = speed_kmh / 3.6  # m/s
    interval = 2  # detik antara pengiriman

    distance_m = speed_ms * interval
    delta_lat = (distance_m * math.cos(math.radians(heading))) / 111000
    delta_lon = (distance_m * math.sin(math.radians(heading))) / (111000 * math.cos(math.radians(current_lat)))

    current_lat += delta_lat
    current_lon += delta_lon

    return heading


print(f"Starting dummy data sender to: {URL}")
print(f"Session ID: {session_id}")
print(f"Start GPS: {start_lat}, {start_lon}")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        # Simulasi kecepatan realistis (0-80 km/h, kadang berhenti)
        speed = random.choices(
            [0, random.randint(5, 30), random.randint(30, 60), random.randint(60, 90)],
            weights=[10, 30, 40, 20],  # 10% diam, 30% pelan, 40% sedang, 20% cepat
            k=1
        )[0]

        # RPM berkorelasi dengan speed
        if speed == 0:
            rpm = random.randint(700, 900)  # idle
            engine_load = random.uniform(10, 20)
            throttle = random.uniform(0, 5)
        elif speed < 30:
            rpm = random.randint(1000, 1800)
            engine_load = random.uniform(15, 35)
            throttle = random.uniform(5, 20)
        elif speed < 60:
            rpm = random.randint(1500, 2500)
            engine_load = random.uniform(25, 50)
            throttle = random.uniform(15, 35)
        else:
            rpm = random.randint(2200, 3500)
            engine_load = random.uniform(40, 75)
            throttle = random.uniform(30, 60)

        # Update GPS position
        bearing = simulate_driving(speed)

        # Coolant temp (naik perlahan, stabil di 85-95)
        coolant = random.uniform(82, 96)

        # Build data matching real Torque format
        data = {
            "v": "9",
            "session": session_id,
            "id": device_id,
            "time": str(int(time.time() * 1000)),
            "kff1005": f"{current_lon:.8f}",          # Longitude
            "kff1006": f"{current_lat:.8f}",          # Latitude
            "kff1001": f"{speed:.1f}",                # GPS Speed (km/h)
            "kff1007": f"{bearing:.2f}",              # GPS Bearing
            "k5": f"{coolant:.1f}",                   # Coolant Temp (C)
            "k4": f"{engine_load:.1f}",               # Engine Load (%)
            "kc": f"{rpm:.1f}",                       # RPM
            "kff1239": f"{random.uniform(1.5, 5.0):.2f}",  # GPS Accuracy (m)
            "kff1010": f"{random.uniform(95, 120):.1f}",    # GPS Altitude (m)
            "kff123b": f"{bearing:.2f}",              # GPS Bearing (duplicate)
            "kff123a": f"{random.randint(8, 28)}.0",  # GPS Satellites
            "k11": f"{throttle:.2f}",                 # Throttle Position (%)
            "kff1206": f"{random.uniform(10, 35):.2f}",  # Trip Average KPL
        }

        # Build query params and full URL (same as Torque sends via HTTP GET)
        query_string = urllib.parse.urlencode(data)
        full_url = f"{URL}?{query_string}"

        try:
            req = urllib.request.Request(full_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                result = response.read().decode('utf-8')
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] RPM: {rpm:4d} | Speed: {speed:3d} km/h | GPS: {current_lat:.5f}, {current_lon:.5f} | Bearing: {bearing:.0f}° | {result}")
        except Exception as e:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Failed: {e}")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped sender.")
