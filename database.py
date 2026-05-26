import sqlite3
import datetime
import json
import os

DATABASE_FILE = os.environ.get("DATABASE_PATH", "data/torque_data.db")

def init_db():
    # Pastikan direktori tempat database berada sudah dibuat
    dir_name = os.path.dirname(DATABASE_FILE)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    # Trips Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            session_id TEXT PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            device_id TEXT
        )
    ''')
    
    # Telemetry Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            rpm REAL,
            speed REAL,
            load REAL,
            coolant REAL,
            throttle REAL,
            fuel REAL,
            latitude REAL,
            longitude REAL,
            raw_data TEXT,
            FOREIGN KEY (session_id) REFERENCES trips (session_id)
        )
    ''')
    conn.commit()
    conn.close()

def save_telemetry(session_id, device_id, log_data, parsed_vals):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    now_str = log_data["timestamp_server"]
    
    # 1. Upsert trip session
    c.execute("SELECT session_id FROM trips WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO trips (session_id, start_time, end_time, device_id) VALUES (?, ?, ?, ?)",
                  (session_id, now_str, now_str, device_id))
    else:
        c.execute("UPDATE trips SET end_time = ? WHERE session_id = ?", (now_str, session_id))
        
    # 2. Insert telemetry point
    c.execute('''
        INSERT INTO telemetry (
            session_id, timestamp, rpm, speed, load, coolant, throttle, fuel, latitude, longitude, raw_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        now_str,
        parsed_vals.get('rpm'),
        parsed_vals.get('speed'),
        parsed_vals.get('load'),
        parsed_vals.get('coolant'),
        parsed_vals.get('throttle'),
        parsed_vals.get('fuel'),
        parsed_vals.get('latitude'),
        parsed_vals.get('longitude'),
        json.dumps(log_data)
    ))
    conn.commit()
    conn.close()

def get_all_trips():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT 
            t.session_id,
            t.start_time,
            t.end_time,
            t.device_id,
            COUNT(m.id) as record_count,
            MAX(m.speed) as max_speed,
            AVG(m.speed) as avg_speed,
            MAX(m.rpm) as max_rpm,
            AVG(m.rpm) as avg_rpm
        FROM trips t
        LEFT JOIN telemetry m ON t.session_id = m.session_id
        GROUP BY t.session_id
        ORDER BY t.start_time DESC
    ''')
    rows = c.fetchall()
    conn.close()
    
    trips = []
    for r in rows:
        trips.append({
            "session_id": r[0],
            "start_time": r[1],
            "end_time": r[2],
            "device_id": r[3],
            "record_count": r[4],
            "max_speed": round(r[5], 1) if r[5] is not None else 0,
            "avg_speed": round(r[6], 1) if r[6] is not None else 0,
            "max_rpm": round(r[7], 1) if r[7] is not None else 0,
            "avg_rpm": round(r[8], 1) if r[8] is not None else 0
        })
    return trips

def get_trip_details(session_id):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, rpm, speed, load, coolant, throttle, fuel, latitude, longitude
        FROM telemetry
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (session_id,))
    rows = c.fetchall()
    conn.close()
    
    points = []
    for r in rows:
        points.append({
            "timestamp": r[0],
            "rpm": r[1],
            "speed": r[2],
            "load": r[3],
            "coolant": r[4],
            "throttle": r[5],
            "fuel": r[6],
            "latitude": r[7],
            "longitude": r[8]
        })
    return points

def prune_old_data(days=30):
    """Deletes trips and telemetry older than a certain number of days."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        
        # Calculate the cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # First, find session_ids that ended before the cutoff date
        c.execute("SELECT session_id FROM trips WHERE end_time < ?", (cutoff_str,))
        old_sessions = c.fetchall()
        
        if old_sessions:
            session_ids = [s[0] for s in old_sessions]
            
            # Use chunks if many sessions
            placeholders = ', '.join('?' * len(session_ids))
            
            # Delete telemetry for old sessions
            c.execute(f"DELETE FROM telemetry WHERE session_id IN ({placeholders})", session_ids)
            deleted_telemetry = c.rowcount
            
            # Delete old sessions
            c.execute(f"DELETE FROM trips WHERE session_id IN ({placeholders})", session_ids)
            deleted_trips = c.rowcount
            
            conn.commit()
            print(f"[Prune] Cleaned up {deleted_trips} old trips and {deleted_telemetry} telemetry points (older than {days} days).")
        else:
            print(f"[Prune] No data older than {days} days found.")
            
        conn.close()
    except Exception as e:
        print(f"Error during data pruning: {e}")
