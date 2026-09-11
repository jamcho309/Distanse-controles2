import asyncio
import json
import os
import random
import websockets

DISPOSITIVOS = {}

def generar_id_unico():
    while True:
        nuevo_id = str(random.randint(100000000, 999999999))
        if nuevo_id not in DISPOSITIVOS:
            return nuevo_id

async def manejar_conexion(websocket):
    dispositivo_id = None
    try:
        async for mensaje in websocket:
            datos = json.loads(mensaje)
            accion = datos.get("accion")

            if accion == "REGISTRAR":
                id_solicitado = datos.get("id_fijo")
                
                # Si el equipo envía un ID guardado y no está ocupado, se lo asignamos
                if id_solicitado and id_solicitado not in DISPOSITIVOS:
                    dispositivo_id = id_solicitado
                else:
                    dispositivo_id = generar_id_unico()

                DISPOSITIVOS[dispositivo_id] = websocket
                print(f"[+] Dispositivo registrado con ID: {dispositivo_id}", flush=True)
                
                await websocket.send(json.dumps({
                    "tipo": "REGISTRO_EXITOSO",
                    "id": dispositivo_id
                }))

            elif accion == "CONECTAR":
                id_objetivo = datos.get("id_objetivo")
                if id_objetivo in DISPOSITIVOS:
                    host_ws = DISPOSITIVOS[id_objetivo]
                    
                    await host_ws.send(json.dumps({
                        "tipo": "PETICION_CONEXION",
                        "cliente_id": id(websocket)
                    }))
                    
                    await websocket.send(json.dumps({
                        "tipo": "ESTADO_CONEXION",
                        "exito": True,
                        "mensaje": "Conectado al dispositivo."
                    }))
                else:
                    await websocket.send(json.dumps({
                        "tipo": "ESTADO_CONEXION",
                        "exito": False,
                        "mensaje": "ID no encontrado o desconectado."
                    }))

            elif accion == "RELAY":
                id_destino = datos.get("destino")
                if id_destino in DISPOSITIVOS:
                    await DISPOSITIVOS[id_destino].send(json.dumps({
                        "tipo": "DATA",
                        "contenido": datos.get("contenido")
                    }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if dispositivo_id and dispositivo_id in DISPOSITIVOS:
            del DISPOSITIVOS[dispositivo_id]
            print(f"[-] Dispositivo {dispositivo_id} desconectado.", flush=True)

async def main():
    puerto = int(os.environ.get("PORT", 8080))
    print(f"=== SERVIDOR CENTRAL INICIANDO EN PUERTO {puerto} ===", flush=True)
    
    async with websockets.serve(
        manejar_conexion, 
        "0.0.0.0", 
        puerto, 
        ping_interval=20, 
        ping_timeout=20
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
if __name__ == "__main__":
    asyncio.run(main())
