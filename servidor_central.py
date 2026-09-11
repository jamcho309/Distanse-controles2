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
                if id_solicitado and str(id_solicitado) not in DISPOSITIVOS:
                    dispositivo_id = str(id_solicitado)
                else:
                    dispositivo_id = generar_id_unico()

                DISPOSITIVOS[dispositivo_id] = websocket
                print(f"[+] Dispositivo registrado: {dispositivo_id}", flush=True)
                await websocket.send(json.dumps({"tipo": "REGISTRO_EXITOSO", "id": dispositivo_id}))

            elif accion in ("CONECTAR", "SOLICITAR_CONEXION"):
                id_objetivo = str(datos.get("id_objetivo") or datos.get("destino") or datos.get("para_id"))
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

            elif accion == "RESPUESTA_CONEXION":
                id_solicitante = str(datos.get("id_objetivo") or datos.get("para_id"))
                if id_solicitante in DISPOSITIVOS:
                    await DISPOSITIVOS[id_solicitante].send(json.dumps({
                        "tipo": "RESPUESTA_CONEXION",
                        "estado": datos.get("estado")
                    }))

            elif accion == "RELAY":
                id_destino = str(datos.get("id_objetivo") or datos.get("para_id") or datos.get("destino"))
                sub_tipo = datos.get("tipo")

                if id_destino in DISPOSITIVOS:
                    # Si es un evento de entrada (mouse/teclado)
                    if sub_tipo == "EVENTO_INPUT":
                        await DISPOSITIVOS[id_destino].send(json.dumps({
                            "tipo": "EVENTO_INPUT",
                            "sub_tipo": datos.get("sub_tipo"),
                            "x": datos.get("x"),
                            "y": datos.get("y"),
                            "boton": datos.get("boton"),
                            "key": datos.get("key")
                        }))
                    else:
                        # Si es un frame de pantalla normal
                        await DISPOSITIVOS[id_destino].send(json.dumps({
                            "tipo": "DATA",
                            "contenido": datos.get("contenido") or datos.get("data")
                        }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if dispositivo_id and dispositivo_id in DISPOSITIVOS:
            del DISPOSITIVOS[dispositivo_id]

async def main():
    puerto = int(os.environ.get("PORT", 8080))
    async with websockets.serve(
        manejar_conexion, 
        "0.0.0.0", 
        puerto, 
        ping_interval=30,      # Aumentado para evitar desconexiones por tráfico pesado
        ping_timeout=30,       # Aumentado para evitar timeout por frames de video
        max_size=None,
        max_queue=32,          # Cola más grande para soportar el flujo constante
        write_limit=2097152    # Límite de escritura ampliado a 2MB
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
