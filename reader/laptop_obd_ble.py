import asyncio
import time
from bleak import BleakScanner, BleakClient

# Library Bleak digunakan untuk komunikasi Bluetooth Low Energy (BLE) di Python
# Anda mungkin perlu menginstalnya dulu via terminal: pip install bleak

async def main():
    print("Mencari perangkat BLE OBD2 di sekitar (Mohon tunggu beberapa detik)...")
    
    # Scan semua perangkat BLE yang nyala di sekitar laptop
    devices = await BleakScanner.discover()
    
    obd_device = None
    print("\n--- Daftar Perangkat BLE Ditemukan ---")
    for d in devices:
        if d.name:
            print(f" - {d.name} [{d.address}]")
            # Nama OBD2 BLE biasanya mengandung kata-kata ini:
            if any(keyword in d.name.upper() for keyword in ["OBD", "V-LINK", "BLE", "IOS", "ELM"]):
                obd_device = d
                
    if not obd_device:
        print("\nERROR: Tidak menemukan perangkat yang dicurigai sebagai OBD2 BLE.")
        print("Pastikan dongle menyala (tertancap di mobil) dan tidak sedang terhubung ke HP Anda!")
        return

    print(f"\nTarget Ditemukan! Mencoba terhubung ke: {obd_device.name} [{obd_device.address}]")
    
    try:
        # Melakukan koneksi GATT (Protokol khusus BLE)
        async with BleakClient(obd_device) as client:
            print("BINGO! Berhasil Terhubung ke Dongle BLE!\n")
            
            rx_char = None  # Jalur untuk mengirim (Write)
            tx_char = None  # Jalur untuk membaca (Notify/Read)
            
            # Dongle BLE mengelompokkan data dalam "Services" dan "Characteristics"
            # Kita cari jalur mana yang bisa ditulis (RX) dan bisa memberi notifikasi (TX)
            print("Mencari jalur komunikasi (Karakteristik UART)...")
            for service in client.services:
                for char in service.characteristics:
                    if "notify" in char.properties or "read" in char.properties:
                        # Prioritaskan UUID yang umum dipakai chip Tiongkok (FFE1 / FFF1)
                        if tx_char is None or "ffe1" in char.uuid.lower() or "fff1" in char.uuid.lower():
                            tx_char = char
                    if "write" in char.properties or "write-without-response" in char.properties:
                        if rx_char is None or "ffe1" in char.uuid.lower() or "fff2" in char.uuid.lower():
                            rx_char = char
                            
            if not tx_char or not rx_char:
                print("Gagal menemukan jalur komunikasi UART di dongle ini.")
                return
                
            print(f"[OK] Jalur Kirim (RX): {rx_char.uuid}")
            print(f"[OK] Jalur Baca  (TX): {tx_char.uuid}\n")
            
            # Fungsi ini akan dipanggil otomatis setiap kali mesin mobil membalas pesan
            def notification_handler(sender, data):
                text = data.decode('ascii', errors='ignore').replace('\r', '\n').strip()
                if text:
                    print(f"<<< Balasan: {text}")

            # Nyalakan keran notifikasi agar balasan masuk ke fungsi notification_handler
            await client.start_notify(tx_char, notification_handler)
            
            # Fungsi pembantu untuk mengirim perintah heksadesimal/AT Command
            async def send_cmd(cmd):
                print(f"\n>>> Mengirim: {cmd}")
                payload = (cmd + '\r').encode('ascii')
                # Kirim data sebagai raw bytes
                if "write-without-response" in rx_char.properties:
                    await client.write_gatt_char(rx_char, payload, response=False)
                else:
                    await client.write_gatt_char(rx_char, payload, response=True)
                await asyncio.sleep(1) # Tunggu balasan masuk

            # ---------------------------------------------------------
            # TAHAP 1: INISIALISASI DONGLE
            # ---------------------------------------------------------
            print("--- Memulai Inisialisasi ELM327 ---")
            await send_cmd("ATZ")      # Reset alat
            await asyncio.sleep(1)     # Butuh waktu ekstra untuk reset
            await send_cmd("ATE0")     # Matikan fungsi membeo (Echo off)
            await send_cmd("ATL0")     # Matikan Linefeeds
            await send_cmd("ATSP0")    # Cari protokol mobil otomatis
            
            print("\n--- Meminta Data ECU ---")
            await asyncio.sleep(2)     # Beri waktu nyari protokol

            # ---------------------------------------------------------
            # TAHAP 2: BACA RPM DAN KECEPATAN BERKALI-KALI
            # ---------------------------------------------------------
            for i in range(5):
                await send_cmd("010C") # Minta RPM
                await send_cmd("010D") # Minta Kecepatan
                await asyncio.sleep(1)
                
            # Matikan notifikasi sebelum keluar
            await client.stop_notify(tx_char)
            print("\nSelesai. Memutus koneksi...")
            
    except Exception as e:
        print(f"\nError saat berkomunikasi: {e}")

if __name__ == "__main__":
    # Jalankan program asinkron
    asyncio.run(main())
