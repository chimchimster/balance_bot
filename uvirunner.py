import sys
import uvicorn


async def main():

    try:
        config = uvicorn.Config(
            app='app:app',
            host='0.0.0.0',
            port=8000,
            log_level='info',
            reload=True,
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
