import asyncio
import json
import os
import random
import websockets

DISPOSITIVOS = {}
DESTINOS_ACTIVOS = {} # Mapea quién le manda video a quién

async def manejar_conexion(websocket):
    dispositivo_id = None
    try:
        async for mensaje in websocket:
            # Si el mensaje es binario (video puro), lo reenviamos directo al destino sin pasar por JSON
            if isinstance(mensaje, bytes):
                if dispositivo_id in DESTINOS_ACTIVOS:
                    id_destino = DESTINOS_ACTIVOS[dispositivo_id]
                    if id_destino in DISPOSITIVOS:
                        await DISPOSITIVOS[id_destino].send(mensaje)
                continue

            # Si es texto, procesamos el JSON de control normal
            datos = json.loads(mensaje)
            accion = datos.get("accion")

            if accion == "REGISTRAR":
                id_solicitado = datos.get("id_fijo")
                if id_solicitado and str(id_solicitado) not in DISPOSITIVOS:
                    dispositivo_id = str(id_solicitado)
                else:
                    dispositivo_id = str(random.randint(100000000, 999999999))

                DISPOSITIVOS[dispositivo_id] = websocket
                await websocket.send(json.dumps({"tipo": "REGISTRO_EXITOSO", "id": dispositivo_id}))

            elif accion in ("CONECTAR", "SOLICITAR_CONEXION"):
                id_objetivo = str(datos.get("id_objetivo") or datos.get("destino") or datos.get("para_id"))
                if id_objetivo in DISPOSITIVOS:
                    # Establecemos enlace directo de video
                    DESTINOS_ACTIVOS[dispositivo_id] = id_objetivo
                    await DISPOSITIVOS[id_objetivo].send(json.dumps({
                        "tipo": "PETICION_CONEXION",
                        "de_id": dispositivo_id,
                        "password": datos.get("password")
                    }))

            elif accion == "RESPUESTA_CONEXION":
                id_solicitante = str(datos.get("id_objetivo") or datos.get("para_id"))
                if id_solicitante in DISPOSITIVOS:
                    # Si aceptó la conexión, el solicitante también apunta su video al host
                    DESTINOS_ACTIVOS[id_solicitante] = dispositivo_id
                    await DISPOSITIVOS[id_solicitante].send(json.dumps({
                        "tipo": "RESPUESTA_CONEXION",
                        "estado": datos.get("estado")
                    }))

            elif accion == "RELAY":
                # Para eventos de mouse y teclado (JSON)
                id_destino = str(datos.get("id_objetivo") or datos.get("para_id") or datos.get("destino"))
                if id_destino in DISPOSITIVOS:
                    await DISPOSITIVOS[id_destino].send(json.dumps({
                        "tipo": "EVENTO_INPUT",
                        "sub_tipo": datos.get("sub_tipo"),
                        "x": datos.get("x"),
                        "y": datos.get("y"),
                        "boton": datos.get("boton"),
                        "key": datos.get("key")
                    }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if dispositivo_id:
            if dispositivo_id in DISPOSITIVOS:
                del DISPOSITIVOS[dispositivo_id]
            # Limpiar rutas activas
            keys_to_del = [k for k, v in DESTINOS_ACTIVOS.items() if k == dispositivo_id or v == dispositivo_id]
            for k in keys_to_del:
                del DESTINOS_ACTIVOS[k]

async def main():
    puerto = int(os.environ.get("PORT", 8080))
    async with websockets.serve(
        manejar_conexion, 
        "0.0.0.0", 
        puerto, 
        ping_interval=30, 
        ping_timeout=30,
        max_size=None,
        max_queue=64,
        write_limit=10485760 # 10MB de búfer libre gracias a tu plan de pago
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
