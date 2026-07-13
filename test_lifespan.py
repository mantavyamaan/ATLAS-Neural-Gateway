import asyncio
from app.main import app

async def test():
    async with app.router.lifespan_context(app):
        print('LIFESPAN OK')

asyncio.run(test())
