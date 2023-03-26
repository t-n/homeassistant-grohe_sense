import aiohttp
import asyncio

from ..oauth_session import OauthSession


async def test():
    session = aiohttp.ClientSession()

    client = OauthSession(
        session=session,
        username="tn@t-n.nu",
        password="5&*ez3Q7EyJmV3@9t^qB",
    )

    print(await client.async_get_devices())

    print(await client.async_get_data())

    await client.fetch_refresh_token()

    print(await client.async_get_devices())

    print(await client.async_get_data())


asyncio.get_event_loop().run_until_complete(test())
