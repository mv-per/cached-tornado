import asyncio
from tornado.web import Application, RequestHandler
from functools import wraps


class CacheManager:
    cached = {}

    def set(self, key: str, value: str) -> None:
        self.cached[key] = value

    def get(self, key: str) -> str | None:
        if key in self.cached.keys():
            return self.cached[key]
        return None

    def remove(self, key: str) -> None:
        if key in self.cached.keys():
            del self.cached[key]

    def clean(self) -> None:
        self.cached = {}

    def list_keys(self) -> list[str]:
        return list(self.cached.keys())


def cache_response(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        request_url = self.request.uri
        manager = self.settings["settings"].get("cache_manager")

        if manager is None:
            raise RuntimeError(
                "cache_manager setting must be defined on cache response"
            )

        # Check if the response is already cached
        response = manager.get(request_url)
        if response is not None:
            return self.write(response)

        # If not cached, call the original function and cache its response
        return await func(self, *args, **kwargs)

    return wrapper


def clean_cached_response(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        request_url = self.request.uri
        manager = self.settings["settings"].get("cache_manager")

        if manager is None:
            raise RuntimeError(
                "cache_manager setting must be defined on cache response"
            )

        # removes response if already cached
        manager.remove(request_url)

        # call the original function
        return await func(self, *args, **kwargs)

    return wrapper


class CachedRequestHandler(RequestHandler):
    cached_methods = ["GET"]

    def write(self, chunk) -> None:
        if self.request.method in self.cached_methods:
            manager = self.settings["settings"].get("cache_manager")
            request_url = self.request.uri
            manager.set(request_url, chunk)
        return super().write(chunk)

    @cache_response
    async def get(self):
        return self.write({"data": "data"})

    @clean_cached_response
    async def put(self):
        raise NotImplementedError()

    @clean_cached_response
    async def patch(self):
        raise NotImplementedError()


def create_app() -> Application:
    cache_manager = CacheManager()

    return Application(
        [(r"/test/\d+/?", CachedRequestHandler)],
        settings={"cache_manager": cache_manager},
    )


async def main():
    app = create_app()
    app.listen(8888)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
