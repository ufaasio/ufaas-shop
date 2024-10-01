import logging
from io import BytesIO

import aiofiles
import aiohttp


async def aio_request(*, method: str = "get", url: str = None, **kwargs) -> dict:
    async with aiohttp.ClientSession() as session:
        return await aio_request_session(session, method=method, url=url, **kwargs)


async def aio_request_session(
    session: aiohttp.ClientSession,
    *,
    method: str = "get",
    url: str = None,
    **kwargs,
) -> dict:
    if url is None:
        raise ValueError("url is required")
    if not url.startswith("http"):
        url = f"https://{url}"

    raise_exception = kwargs.pop("raise_exception", True)

    async with session.request(method, url, **kwargs) as response:
        if not response.ok:
            logging.error(
                f"Error in aio_request {url} {kwargs.get('data', 'None')[:100]}: "
                + f"{response.status} {await response.text()}"
            )
        if raise_exception:
            response.raise_for_status()
        return await response.json()


async def aio_request_binary(
    *, method: str = "get", url: str = None, **kwargs
) -> BytesIO:
    async with aiohttp.ClientSession() as session:
        return await aio_request_binary_session(
            session, method=method, url=url, **kwargs
        )


async def aio_request_binary_session(
    session: aiohttp.ClientSession,
    *,
    method: str = "get",
    url: str = None,
    **kwargs,
) -> BytesIO:
    if url is None:
        raise ValueError("url is required")
    if not url.startswith("http"):
        url = f"https://{url}"

    raise_exception = kwargs.pop("raise_exception", True)

    async with session.request(method, url, **kwargs) as response:
        if raise_exception:
            response.raise_for_status()
        resp_bytes = BytesIO(await response.read())
        resp_bytes.seek(0)
        return resp_bytes


async def aio_download(url: str, filename: str, **kwargs):
    async with aiohttp.ClientSession() as session:
        return await aio_download_session(session, url, filename, **kwargs)


async def aio_download_session(
    session: aiohttp.ClientSession, url: str, filename: str, **kwargs
):
    if url is None:
        raise ValueError("url is required")
    if not url.startswith("http"):
        url = f"https://{url}"

    raise_exception = kwargs.pop("raise_exception", True)

    async with session.get(url, **kwargs) as response:
        if raise_exception:
            response.raise_for_status()

        async with aiofiles.open(filename, "wb") as f:
            while True:
                chunk = await response.content.read(1024)
                if not chunk:
                    break
                await f.write(chunk)
