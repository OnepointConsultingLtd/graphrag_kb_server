import asyncio
import socketio

sio = socketio.AsyncClient()


async def document_trendiness_test():
    await sio.connect("http://127.0.0.1:9999")
    params = [
        "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJnaWxfZmVybmFuZGVzIiwibmFtZSI6ImdpbF9mZXJuYW5kZXMiLCJpYXQiOjE3NTAzMzQ3OTMsImVtYWlsIjoiZ2lsLmZlcm5hbmRlc0BnbWFpbC5jb20iLCJwZXJtaXNzaW9ucyI6WyJyZWFkIl19.yo6cmq-iCRkEIVtCrRKtlqs5_3o_VSQI6io_Os4HTFxbK8wh8-FlyDCcoKVzLrFab3wJLlHn6s6_OAW_GdYtDw",
        "clustre_full",
        "C:/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full_3/input/Clustre Materials/Articles and PoVs/AI_or_Die_-_Generic.txt",
        30,
    ]
    await sio.emit("document_trendiness", (params[0], params[1], params[2], params[3]))
    await sio.wait()


if __name__ == "__main__":
    asyncio.run(document_trendiness_test())
