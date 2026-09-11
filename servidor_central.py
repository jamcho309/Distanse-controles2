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

            # 1. REGISTRO DE DISPOSITIVO
            if accion == "REGISTRAR":
                id_solicitado = datos.get("id_fijo")
                
                if id_solicitado and id_solicitado not in DISPOSITIVOS:
                    dispositivo_id = str(id_solicitado)
                else:
                    dispositivo_id = generar_id_unico()

                DISPOSITIVOS[dispositivo_id] = websocket
                print(f"[+] Dispositivo registrado con ID: {dispositivo_id}", flush=True)
                
                await websocket.send(json.dumps({
                    "tipo": "REGISTRO_EXITOSO",
                    "id": dispositivo_id
                }))

            # 2. SOLICITUD DE CONEXIÓN
            elif accion in ("CONECTAR", "SOLICITAR_CONEXION"):
                id_objetivo = str(datos.get("id_objetivo") or datos.get("destino"))
                password_enviado = datos.get("password")

                if id_objetivo in DISPOSITIVOS:
                    host_ws = DISPOSITIVOS[id_objetivo]
                    
                    # Notificar a la PC destino sobre la petición incluyendo el ID real del solicitante
                    await host_ws.send(json.dumps({
                        "tipo": "PETICION_CONEXION",
                        "de_id": dispositivo_id,
                        "password": password_enviado
                    }))
                else:
                    await websocket.send(json.dumps({
                        "tipo": "RESPUESTA_CONEXION",
                        "estado": "DENEGADO",
                        "mensaje": "ID no encontrado o fuera de línea."
                    }))

            # 3. RESPUESTA A LA SOLICITUD (Aceptar/Rechazar)
            elif accion == "RESPUESTA_CONEXION":
                id_solicitante = str(datos.get("id_objetivo") or datos.get("para_id"))
                estado = datos.get("estado")

                if id_solicitante in DISPOSITIVOS:
                    await DISPOSITIVOS[id_solicitante].send(json.dumps({
                        "tipo": "RESPUESTA_CONEXION",
                        "estado": estado
                    }))

            # 4. TRANSMISIÓN DE PANTALLA Y DATOS (RELAY)
            elif accion == "RELAY":
                id_destino = str(datos.get("destino") or datos.get("id_objetivo"))
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
    
    # max_size=None permite recibir capturas de pantalla de alto peso sin desconectar
    async with websockets.serve(
        manejar_conexion, 
        "0.0.0.0", 
        puerto, 
        ping_interval=20, 
        ping_timeout=20,
        max_size=None
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
