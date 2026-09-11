import socket
import threading
import struct
import io
import time
import sys
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from mss import mss
import pyautogui

pyautogui.FAILSAFE = False

PORT_VIDEO = 9999
PORT_CONTROL = 9998

# ==============================================================================
# OBTENER IP LOCAL DE ESTE EQUIPO
# ==============================================================================
def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ==============================================================================
# LÓGICA DEL SERVIDOR (PC CONTROLADA)
# ==============================================================================
class ServidorRemoto:
    def __init__(self, status_label):
        self.status_label = status_label
        self.activo = True

    def iniciar(self):
        threading.Thread(target=self._stream_pantalla, daemon=True).start()
        threading.Thread(target=self._recibir_controles, daemon=True).start()

    def _stream_pantalla(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', PORT_VIDEO))
        s.listen(1)
        
        while self.activo:
            try:
                conn, addr = s.accept()
                self.status_label.config(text=f"Estado: Conectado con {addr[0]}", foreground="green")

                with mss() as sct:
                    monitor = sct.monitors[1]
                    while self.activo:
                        sct_img = sct.grab(monitor)
                        img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                        img = img.resize((1600, 900))  # Calidad HD equilibrada

                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=80)
                        data = buffer.getvalue()

                        size = len(data)
                        conn.sendall(struct.pack('>I', size) + data)
                        time.sleep(0.03)  # ~30 FPS
            except Exception:
                self.status_label.config(text="Estado: Esperando conexión...", foreground="orange")

    def _recibir_controles(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', PORT_CONTROL))
        s.listen(1)

        sw, sh = pyautogui.size()

        while self.activo:
            try:
                conn, addr = s.accept()
                while self.activo:
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
                pass

# ==============================================================================
# LÓGICA DEL CLIENTE (VISOR)
# ==============================================================================
class VentanaCliente:
    def __init__(self, ip_destino):
        self.ip_destino = ip_destino
        self.top = tk.Toplevel()
        self.top.title(f"Controlando PC: {ip_destino}")
        self.top.geometry("1280x720")

        self.label = tk.Label(self.top, bg="black")
        self.label.pack(fill=tk.BOTH, expand=True)

        try:
            self.sock_video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_video.connect((self.ip_destino, PORT_VIDEO))

            self.sock_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_control.connect((self.ip_destino, PORT_CONTROL))
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar a {ip_destino}\n\nDetalle: {e}")
            self.top.destroy()
            return

        self.label.bind("<Motion>", self._al_mover_mouse)
        self.label.bind("<Button-1>", self._al_hacer_clic)

        threading.Thread(target=self._recibir_video, daemon=True).start()

    def _al_mover_mouse(self, event):
        w = self.label.winfo_width()
        h = self.label.winfo_height()
        if w > 0 and h > 0:
            rx, ry = event.x / w, event.y / h
            try:
                self.sock_control.sendall(f"MOVE,{rx},{ry}".encode('utf-8'))
            except:
                pass

    def _al_hacer_clic(self, event):
        w = self.label.winfo_width()
        h = self.label.winfo_height()
        if w > 0 and h > 0:
            rx, ry = event.x / w, event.y / h
            try:
                self.sock_control.sendall(f"CLICK,{rx},{ry}".encode('utf-8'))
            except:
                pass

    def _recibir_video(self):
        payload_size = struct.calcsize('>I')
        data = b""

        while True:
            try:
                while len(data) < payload_size:
                    packet = self.sock_video.recv(4096)
                    if not packet: return
                    data += packet

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack('>I', packed_msg_size)[0]

                while len(data) < msg_size:
                    data += self.sock_video.recv(4096)

                frame_data = data[:msg_size]
                data = data[msg_size:]

                image = Image.open(io.BytesIO(frame_data))
                photo = ImageTk.PhotoImage(image)
                self.label.config(image=photo)
                self.label.image = photo
            except Exception:
                break

# ==============================================================================
# INTERFAZ GRÁFICA PRINCIPAL (MENU DE SELECCIÓN)
# ==============================================================================
class AppPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de Control Remoto")
        self.root.geometry("450x380")
        self.root.resizable(False, False)

        ip_local = obtener_ip_local()

        # Estilos UI
        style = ttk.Style()
        style.theme_use('clam')

        # Contenedor Mi IP
        frame_ip = ttk.LabelFrame(root, text=" Tu Identificador Local ", padding=15)
        frame_ip.pack(fill="x", padx=20, pady=10)

        ttk.Label(frame_ip, text="Comparte esta IP para que controlen tu PC:", font=("Arial", 9)).pack(anchor="w")
        entry_my_ip = ttk.Entry(frame_ip, font=("Consolas", 12, "bold"), justify="center")
        entry_my_ip.insert(0, ip_local)
        entry_my_ip.config(state="readonly")
        entry_my_ip.pack(fill="x", pady=5)

        self.lbl_estado = ttk.Label(frame_ip, text="Estado: Servidor inactivo", foreground="gray", font=("Arial", 9, "italic"))
        self.lbl_estado.pack(anchor="w")

        btn_servidor = ttk.Button(frame_ip, text="Permitir Control (Iniciar Servidor)", command=self.iniciar_servidor)
        btn_servidor.pack(fill="x", pady=5)

        # Contenedor Conectarse
        frame_remote = ttk.LabelFrame(root, text=" Controlar otro equipo ", padding=15)
        frame_remote.pack(fill="x", padx=20, pady=10)

        ttk.Label(frame_remote, text="Ingresa la IP de la PC a controlar:", font=("Arial", 9)).pack(anchor="w")
        self.txt_ip_remota = ttk.Entry(frame_remote, font=("Consolas", 11))
        self.txt_ip_remota.insert(0, "127.0.0.1")
        self.txt_ip_remota.pack(fill="x", pady=5)

        btn_conectar = ttk.Button(frame_remote, text="Conectar a PC Remota", command=self.conectar_remoto)
        btn_conectar.pack(fill="x", pady=5)

    def iniciar_servidor(self):
        self.servidor = ServidorRemoto(self.lbl_estado)
        self.servidor.iniciar()
        self.lbl_estado.config(text="Estado: Esperando conexión...", foreground="orange")
        messagebox.showinfo("Servidor Activo", "Tu equipo ahora está listo para recibir conexiones en la red local.")

    def conectar_remoto(self):
        ip_destino = self.txt_ip_remota.get().strip()
        if not ip_destino:
            messagebox.showwarning("Campo Vacío", "Por favor ingresa una dirección IP válida.")
            return
        VentanaCliente(ip_destino)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppPanel(root)
    root.mainloop()
    