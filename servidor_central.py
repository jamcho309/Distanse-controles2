import asyncio
import json
import random
import websockets

# Diccionario para almacenar los equipos registrados {ID_9_DIGITOS: websocket}
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

            # 1. Registrar una PC para ser controlada
            if accion == "REGISTRAR":
                dispositivo_id = generar_id_unico()
                DISPOSITIVOS[dispositivo_id] = websocket
                print(f"[+] Nuevo dispositivo registrado con ID: {dispositivo_id}")
                
                # Devolver el ID generado al host
                await websocket.send(json.dumps({
                    "tipo": "REGISTRO_EXITOSO",
                    "id": dispositivo_id
                }))

            # 2. Conectar un Cliente a un ID objetivo
            elif accion == "CONECTAR":
                id_objetivo = datos.get("id_objetivo")
                if id_objetivo in DISPOSITIVOS:
                    host_ws = DISPOSITIVOS[id_objetivo]
                    
                    # Notificar al host que un cliente se quiere conectar
                    await host_ws.send(json.dumps({
                        "tipo": "PETICION_CONEXION",
                        "cliente_id": id(websocket)
                    }))
                    
                    await websocket.send(json.dumps({
                        "tipo": "ESTADO_CONEXION",
                        "exito": True,
                        "mensaje": "Conectado al dispositivo objetivo."
                    }))
                else:
                    await websocket.send(json.dumps({
                        "tipo": "ESTADO_CONEXION",
                        "exito": False,
                        "mensaje": "El ID ingresado no existe o está desconectado."
                    }))

            # 3. Retransmitir datos (Video o Controles) entre pares
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
        # Limpiar registro al desconectar
        if dispositivo_id and dispositivo_id in DISPOSITIVOS:
            del DISPOSITIVOS[dispositivo_id]
            print(f"[-] Dispositivo {dispositivo_id} desconectado.")

async def main():
    # Servidor escuchando en el puerto 8765
    async with websockets.serve(manejar_conexion, "0.0.0.0", 8765):
        print("=== SERVIDOR CENTRAL DE SEÑALIZACIÓN ACTIVO (Puerto 8765) ===")
        await asyncio.Future()  # Mantener corriendo

if __name__ == "__main__":
    asyncio.run(main())
    