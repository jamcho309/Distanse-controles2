import socket
import threading
import struct
import io
import time
import sys
from mss import mss
from PIL import Image
import pyautogui

pyautogui.FAILSAFE = False

HOST = '0.0.0.0'
PORT_VIDEO = 9999
PORT_CONTROL = 9998

def stream_pantalla():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT_VIDEO))
    s.listen(1)
    print(f"[+] Servidor de Video listo en el puerto {PORT_VIDEO}", flush=True)
    conn, addr = s.accept()
    print(f"[!] Cliente conectado para video: {addr}", flush=True)

    with mss() as sct:
        monitor = sct.monitors[1]
        while True:
            try:
                sct_img = sct.grab(monitor)
                img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                img = img.resize((1920, 1080))

                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=50)
                data = buffer.getvalue()

                size = len(data)
                conn.sendall(struct.pack('>I', size) + data)
            except Exception:
                break

def recibir_controles():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT_CONTROL))
    s.listen(1)
    print(f"[+] Servidor de Control listo en el puerto {PORT_CONTROL}", flush=True)
    conn, addr = s.accept()
    print(f"[!] Cliente conectado para controles: {addr}", flush=True)
    
    sw, sh = pyautogui.size()

    while True:
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            
            partes = data.split(',')
            accion = partes[0]
            rx, ry = float(partes[1]), float(partes[2])
            x, y = int(rx * sw), int(ry * sh)

            if accion == "MOVE":
                pyautogui.moveTo(x, y)
            elif accion == "CLICK":
                pyautogui.click(x, y)

        except Exception:
            break

if __name__ == "__main__":
    print("Iniciando hilos del servidor...", flush=True)
    
    t1 = threading.Thread(target=stream_pantalla, daemon=True)
    t2 = threading.Thread(target=recibir_controles, daemon=True)
    
    t1.start()
    t2.start()

    print("=== SERVIDOR ACTIVO Y ESCUCHANDO ===", flush=True)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nServidor detenido.")