import os
import asyncio
import jiter


async def load_json(file_name):
    def _load_json_sync():
        if not os.path.exists(file_name):
            return None
        # Read file as bytes for jiter (faster than text mode)
        with open(file_name, "rb") as f:
            return jiter.from_json(f.read())
    
    return await asyncio.to_thread(_load_json_sync)