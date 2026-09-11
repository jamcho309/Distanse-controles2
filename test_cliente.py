import asyncio
import json
import websockets

async def probar_registro():
    # Cambia 'localhost' por la IP pública o dominio cuando lo subas a la nube
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Solicitar registro
        await websocket.send(json.dumps({"accion": "REGISTRAR"}))
        
        # Recibir respuesta del servidor
        respuesta = await websocket.recv()
        datos = json.loads(respuesta)
        
        print(f"TU ID DE ANYDESK ES: {datos['id']}")
        
        # Mantener conexión viva
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(probar_registro())
    