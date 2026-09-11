import sys
import trace

def ejecutar():
    import socket
    import threading
    import struct
    import io
    import tkinter as tk
    from PIL import Image, ImageTk

    SERVER_IP = '127.0.0.1' 
    PORT_VIDEO = 9999
    PORT_CONTROL = 9998

    class ControlCliente:
        def __init__(self, root):
            self.root = root
            self.root.title("Control Remoto - Visor")
            self.root.geometry("1280x720")

            self.label = tk.Label(root, bg="black")
            self.label.pack(fill=tk.BOTH, expand=True)

            print("[+] Conectando al servidor...")
            self.sock_video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_video.connect((SERVER_IP, PORT_VIDEO))

            self.sock_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_control.connect((SERVER_IP, PORT_CONTROL))
            print("[!] Conexión establecida con éxito.")

            self.label.bind("<Motion>", self.al_mover_mouse)
            self.label.bind("<Button-1>", self.al_hacer_clic)

            threading.Thread(target=self.recibir_video, daemon=True).start()

        def al_mover_mouse(self, event):
            w = self.label.winfo_width()
            h = self.label.winfo_height()
            if w > 0 and h > 0:
                rx = event.x / w
                ry = event.y / h
                msg = f"MOVE,{rx},{ry}"
                try:
                    self.sock_control.sendall(msg.encode('utf-8'))
                except:
                    pass

        def al_hacer_clic(self, event):
            w = self.label.winfo_width()
            h = self.label.winfo_height()
            if w > 0 and h > 0:
                rx = event.x / w
                ry = event.y / h
                msg = f"CLICK,{rx},{ry}"
                try:
                    self.sock_control.sendall(msg.encode('utf-8'))
                except:
                    pass

        def recibir_video(self):
            payload_size = struct.calcsize('>I')
            data = b""

            while True:
                try:
                    while len(data) < payload_size:
                        packet = self.sock_video.recv(4096)
                        if not packet:
                            return
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

                except Exception as e:
                    print(f"[-] Conexión cerrada: {e}")
                    break

    root = tk.Tk()
    app = ControlCliente(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        ejecutar()
    except Exception as e:
        print("\n--- ERROR DETECTADO ---")
        import traceback
        traceback.print_exc()
        print("-----------------------\n")