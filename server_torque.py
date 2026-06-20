import http.server
import socketserver
import urllib.parse
import json
import datetime
import queue
import threading
import os
import csv
import io

from database import init_db, save_telemetry, get_all_trips, get_trip_details, delete_trip, delete_all_trips, prune_old_data

# Timezone WIB (UTC+7)
WIB = datetime.timezone(datetime.timedelta(hours=7))

PORT = 8080
LOG_FILE = os.environ.get("LOG_PATH", "data/torque_log.txt")

# ==============================================================================
# SSE Broker Setup
# ==============================================================================
sse_clients = []
sse_lock = threading.Lock()

def add_client():
    q = queue.Queue()
    with sse_lock:
        sse_clients.append(q)
    return q

def remove_client(q):
    with sse_lock:
        if q in sse_clients:
            sse_clients.remove(q)

def broadcast(data):
    msg = f"data: {json.dumps(data)}\n\n"
    with sse_lock:
        for q in sse_clients:
            q.put(msg)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

# ==============================================================================
# HTTP Server Handler
# ==============================================================================
class TorqueHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute logging to make console log clean
        pass

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        # 1. Handling Torque uploads / custom HTTP GET requests
        if query_params:
            log_data = {k: v[0] for k, v in query_params.items()}
            log_data["timestamp_server"] = str(datetime.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"))
            
            # Parse parameters for SQLite insertion
            def safe_float(key_list):
                for key in key_list:
                    if key in log_data:
                        try:
                            return float(log_data[key])
                        except ValueError:
                            pass
                return None

            parsed_vals = {
                "rpm": safe_float(['k0c', 'kc']),
                "speed": safe_float(['k0d', 'kd', 'kff1001']),
                "load": safe_float(['k04', 'k4']),
                "coolant": safe_float(['k05', 'k5']),
                "throttle": safe_float(['k11']),
                "fuel": safe_float(['k2f']),
                "latitude": safe_float(['kff1006']),
                "longitude": safe_float(['kff1005'])
            }

            session_id = log_data.get('session', 'default_session')
            device_id = log_data.get('id', 'default_device')
            
            # Print to stdout
            rpm_str = log_data.get('k0c', log_data.get('kc', 'N/A'))
            speed_str = log_data.get('k0d', log_data.get('kd', 'N/A'))
            print(f"[{log_data['timestamp_server']}] Data Received: {len(log_data)} params (RPM: {rpm_str}, Speed: {speed_str})")
            
            # Save telemetry to SQLite
            try:
                save_telemetry(session_id, device_id, log_data, parsed_vals)
            except Exception as e:
                print(f"Error saving to SQLite: {e}")
                
            # Write to raw text log file as secondary backup
            try:
                log_dir = os.path.dirname(LOG_FILE)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(json.dumps(log_data) + "\n")
            except Exception as e:
                pass
            
            # Broadcast to SSE clients
            broadcast(log_data)
            
            # Respond to Torque
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK!")
            return

        # 2. Serving Real-time SSE Stream
        elif path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            q = add_client()
            try:
                while True:
                    try:
                        msg = q.get(timeout=10)
                        self.wfile.write(msg.encode('utf-8'))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (ConnectionResetError, BrokenPipeError):
                pass
            finally:
                remove_client(q)
            return

        # 3. GET /api/trips (List all trips)
        elif path == '/api/trips':
            try:
                trips = get_all_trips()
                payload = json.dumps(trips).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_error(500, f"Database error: {e}")
            return
            
        # 4. GET /api/trips/<session_id>/csv (Export Trip to CSV)
        elif path.startswith('/api/trips/') and path.endswith('/csv'):
            session_id = path.split('/')[3]
            try:
                details = get_trip_details(session_id)
                if not details:
                    self.send_error(404, "Trip not found")
                    return
                
                # Generate CSV
                output = io.StringIO()
                writer = csv.writer(output)
                # Header
                writer.writerow(['Timestamp', 'RPM', 'Speed (km/h)', 'Engine Load (%)', 'Coolant Temp (C)', 'Throttle Position (%)', 'Fuel Level (%)', 'Latitude', 'Longitude'])
                # Data rows
                for row in details:
                    writer.writerow([
                        row['timestamp'], row['rpm'], row['speed'], row['load'], 
                        row['coolant'], row['throttle'], row['fuel'], 
                        row['latitude'], row['longitude']
                    ])
                
                csv_data = output.getvalue().encode('utf-8')
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv')
                self.send_header('Content-Disposition', f'attachment; filename="trip_{session_id}.csv"')
                self.send_header('Content-Length', str(len(csv_data)))
                self.end_headers()
                self.wfile.write(csv_data)
            except Exception as e:
                self.send_error(500, f"Database error generating CSV: {e}")
            return

        # 5. GET /api/trips/<session_id> (Get trip details JSON)
        elif path.startswith('/api/trips/'):
            session_id = path.replace('/api/trips/', '')
            try:
                details = get_trip_details(session_id)
                payload = json.dumps(details).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_error(500, f"Database error: {e}")
            return

        # 6. Serving Dashboard Home
        elif path in ('/', '/index.html'):
            try:
                template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
                with open(template_path, 'rb') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.send_header("Content-Length", str(len(html_content)))
                self.end_headers()
                self.wfile.write(html_content)
            except FileNotFoundError:
                self.send_error(404, "Template index.html not found!")
            return
            
        # Default fallback
        else:
            super().do_GET()

    def do_DELETE(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # DELETE /api/trips (Delete ALL trips)
        if path == '/api/trips':
            try:
                result = delete_all_trips()
                if result:
                    payload = json.dumps({"status": "ok", "message": "All trips deleted", **result}).encode('utf-8')
                    self.send_response(200)
                else:
                    payload = json.dumps({"status": "error", "message": "Failed to delete"}).encode('utf-8')
                    self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_error(500, f"Error: {e}")
            return

        # DELETE /api/trips/<session_id> (Delete single trip)
        elif path.startswith('/api/trips/'):
            session_id = path.replace('/api/trips/', '')
            try:
                result = delete_trip(session_id)
                if result:
                    payload = json.dumps({"status": "ok", "message": f"Trip {session_id} deleted", **result}).encode('utf-8')
                    self.send_response(200)
                else:
                    payload = json.dumps({"status": "error", "message": "Failed to delete"}).encode('utf-8')
                    self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_error(500, f"Error: {e}")
            return

        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        """Handle CORS preflight for DELETE requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# ==============================================================================
# Running Server
# ==============================================================================
if __name__ == '__main__':
    # Initialize SQLite database and prune old data
    try:
        init_db()
        print("SQLite database initialized successfully.")
        prune_old_data(days=30)
    except Exception as e:
        print(f"CRITICAL: Failed to initialize database: {e}")
        
    with ThreadedTCPServer(("", PORT), TorqueHandler) as httpd:
        print(f"==================================================")
        print(f"OBD2 Server with SQLite Log running on port {PORT}...")
        print(f"Open http://localhost:{PORT} in your web browser")
        print(f"==================================================")
        print("Waiting for Torque uploads & web connections...")
        print("Press Ctrl+C to terminate the server.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer terminated by user.")
