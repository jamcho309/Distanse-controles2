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

            # 1. REGISTRO
            if accion == "REGISTRAR":
                id_solicitado = datos.get("id_fijo")
                if id_solicitado and str(id_solicitado) not in DISPOSITIVOS:
                    dispositivo_id = str(id_solicitado)
                else:
                    dispositivo_id = generar_id_unico()

                DISPOSITIVOS[dispositivo_id] = websocket
                print(f"[+] Dispositivo en línea: {dispositivo_id}", flush=True)
                await websocket.send(json.dumps({"tipo": "REGISTRO_EXITOSO", "id": dispositivo_id}))

            # 2. SOLICITUD DE CONEXIÓN
            elif accion in ("CONECTAR", "SOLICITAR_CONEXION"):
                id_objetivo = str(datos.get("id_objetivo") or datos.get("destino"))
                if id_objetivo in DISPOSITIVOS:
                    await DISPOSITIVOS[id_objetivo].send(json.dumps({
                        "tipo": "PETICION_CONEXION",
                        "de_id": dispositivo_id,
                        "password": datos.get("password")
                    }))
                else:
                    await websocket.send(json.dumps({
                        "tipo": "RESPUESTA_CONEXION",
                        "estado": "DENEGADO",
                        "mensaje": "ID fuera de línea."
                    }))

            # 3. RESPUESTA A SOLICITUD
            elif accion == "RESPUESTA_CONEXION":
                id_solicitante = str(datos.get("id_objetivo") or datos.get("para_id"))
                if id_solicitante in DISPOSITIVOS:
                    await DISPOSITIVOS[id_solicitante].send(json.dumps({
                        "tipo": "RESPUESTA_CONEXION",
                        "estado": datos.get("estado")
                    }))

            # 4. RETRANSMISIÓN ULTRA RÁPIDA (RELAY A 60 FPS)
            elif accion == "RELAY":
                id_destino = str(datos.get("destino") or datos.get("id_objetivo"))
                if id_destino in DISPOSITIVOS:
                    # Retransmisión directa sin demoras de procesamiento
                    await DISPOSITIVOS[id_destino].send(json.dumps({
                        "tipo": "DATA",
                        "contenido": datos.get("contenido")
                    }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if dispositivo_id and dispositivo_id in DISPOSITIVOS:
            del DISPOSITIVOS[dispositivo_id]
            print(f"[-] Dispositivo desconectado: {dispositivo_id}", flush=True)

async def main():
    puerto = int(os.environ.get("PORT", 8080))
    print(f"=== SERVIDOR CENTRAL 60 FPS EN PUERTO {puerto} ===", flush=True)
    
    # Parámetros ajustados para 60 FPS:
    # - max_size=None: Elimina el límite de peso de los paquetes.
    # - write_limit=1048576 (1MB): Buffer de salida amplio para evitar cuellos de botella de red.
    async with websockets.serve(
        manejar_conexion, 
        "0.0.0.0", 
        puerto, 
        ping_interval=10, 
        ping_timeout=10,
        max_size=None,
        write_limit=1048576
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
