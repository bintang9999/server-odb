import socket
import time

# CARA PENGGUNAAN DI LINUX:
# 1. Buka terminal, ketik: bluetoothctl
# 2. Ketik: scan on (tunggu sampai nama OBD2 / ELM327 muncul)
# 3. Copy MAC Address-nya (formatnya XX:XX:XX:XX:XX:XX)
# 4. Ketik: pair XX:XX:XX:XX:XX:XX (masukkan pin 1234 atau 0000 jika diminta)
# 5. Ganti variabel OBD2_MAC_ADDRESS di bawah ini dengan MAC Address tersebut.

OBD2_MAC_ADDRESS = "00:11:22:33:44:55"  # <--- GANTI INI DENGAN MAC ADDRESS OBD ANDA
RFCOMM_CHANNEL = 1  # Kita meniru trik rahasia Torque: langsung tembak Channel 1

def send_command(sock, cmd):
    print(f">>> Mengirim: {cmd}")
    # ELM327 WAJIB menerima karakter Carriage Return (\r) di akhir setiap perintah
    sock.send((cmd + '\r').encode('ascii'))
    
    # Beri waktu sedikit untuk dongle berpikir dan membalas
    time.sleep(0.5)
    
    # Baca balasannya
    try:
        response = sock.recv(1024).decode('ascii', errors='ignore')
        # ELM327 membalas dengan prompt '>' di akhir, kita bersihkan tampilannya
        clean_response = response.replace('\r', '\n').strip()
        print(f"<<< Balasan :\n{clean_response}\n")
        return clean_response
    except Exception as e:
        print(f"Error membaca balasan: {e}")
        return ""

def main():
    if OBD2_MAC_ADDRESS == "00:11:22:33:44:55":
        print("ERROR: Harap edit script ini dan masukkan MAC Address Bluetooth OBD2 Anda terlebih dahulu!")
        return

    print(f"Mencoba terhubung langsung ke {OBD2_MAC_ADDRESS} (Channel {RFCOMM_CHANNEL})...")
    
    # Membuat socket Bluetooth khusus RFCOMM (persis seperti yang dilakukan Torque di Java)
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        sock.connect((OBD2_MAC_ADDRESS, RFCOMM_CHANNEL))
        print("BINGO! Berhasil Terhubung ke OBD2!\n")

        # ---------------------------------------------------------
        # TAHAP 1: INISIALISASI (Meniru cara Torque menyetel Dongle)
        # ---------------------------------------------------------
        send_command(sock, "ATZ")     # Reset seluruh sistem dongle
        time.sleep(1)                 # Reset butuh waktu lebih lama
        send_command(sock, "ATE0")    # Echo Off (jangan ulangi kata-kata saya)
        send_command(sock, "ATL0")    # Linefeeds Off (matikan spasi enter berlebih)
        send_command(sock, "ATSP0")   # Auto Protocol (Cari bahasa mobil secara otomatis)

        print("--- Inisialisasi Selesai, Mulai Membaca Data Mesin ---")
        time.sleep(2) # Beri waktu dongle mencari protokol mobil

        # ---------------------------------------------------------
        # TAHAP 2: MEMINTA DATA SENSOR DARI MOBIL (Looping)
        # ---------------------------------------------------------
        for i in range(10): # Kita coba baca 10 kali
            print(f"--- Pembacaan ke-{i+1} ---")
            
            # Minta RPM (Mode 01, PID 0C)
            send_command(sock, "010C") 
            
            # Minta Kecepatan Mobil (Mode 01, PID 0D)
            send_command(sock, "010D")
            
            time.sleep(1)

    except Exception as e:
        print(f"\nGagal terhubung atau terputus: {e}")
        print("Pastikan OBD2 sudah dipairing dengan laptop dan mesin mobil dalam keadaan menyala (ON).")
    finally:
        print("Menutup koneksi...")
        sock.close()

if __name__ == '__main__':
    main()
