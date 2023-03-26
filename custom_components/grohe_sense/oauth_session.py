
import asyncio
import re
from lxml import html

from .const import BASE_URL, GROHE_BASE_URL, LOGGER

_refresh_token = None


class OauthException(Exception):
    def __init__(self, error_code, reason):
        self.error_code = error_code
        self.reason = reason


class TokenExpiredError(Exception):
    def __init__(self, reason):
        self.reason = reason


class OauthSession:
    def __init__(self, session, data, username, password):
        self._session = session
        self._access_token = None
        self._fetching_new_token = None
        self._username = username
        self._password = password
        self._data = data

    @property
    def session(self):
        return self._session

    async def get_locations(self):
        return await self.get(BASE_URL + f'locations')

    async def get_rooms(self, locationId):
        return await self.get(BASE_URL + f'locations/{locationId}/rooms')

    async def get_appliances(self, locationId, roomId):
        return await self.get(BASE_URL + f'locations/{locationId}/rooms/{roomId}/appliances')

    async def get_measurements_response(self, locationId, roomId, applianceId, poll_from):
        return await self.get(BASE_URL + f'locations/{locationId}/rooms/{roomId}/appliances/{applianceId}/data?from={poll_from}')

    async def get(self, url, **kwargs):
        return await self._http_request(url, auth_token=self, **kwargs)

    async def post(self, url, _json, **kwargs):
        return await self._http_request(url, method='post', auth_token=self, json=_json, **kwargs)

    async def _http_request(self, url, method='get', auth_token=None, headers=None, **kwargs):
        LOGGER.debug('Making http %s request to %s, headers %s', method, url, headers)
        headers = headers.copy() if headers is not None else {}
        tries = 0

        while True:
            if auth_token is not None:
                # Cache token so we know which token was used for this request,
                # so we know if we need to invalidate.
                token = await auth_token.token()
                headers['Authorization'] = token

            try:
                async with self._session.request(method, url, headers=headers, **kwargs) as response:
                    LOGGER.debug('Http %s request to %s got response %d', method, url, response.status)
                    if response.status in (200, 201):
                        return await response.json()
                    elif response.status == 401:
                        if auth_token is not None:
                            LOGGER.debug('Request to %s returned status %d, refreshing auth token', url, response.status)
                            token = await auth_token.token(token)
                        else:
                            LOGGER.error('Grohe sense refresh token is invalid (or expired), please update your configuration with a new refresh token')
                            self._clear_refresh_token()
                            raise TokenExpiredError(await response.text())
                    else:
                        LOGGER.debug('Request to %s returned status %d, %s', url, response.status, await response.text())
            except OauthException:
                raise
            except Exception as e:
                LOGGER.debug('Exception for http %s request to %s: %s', method, url, e)

            tries += 1
            await asyncio.sleep(min(600, 2**tries))

    async def token(self, old_token=None):
        """ Returns an authorization header. If one is supplied as old_token, invalidate that one """

        if self._access_token not in (None, old_token):
            return self._access_token

        if self._fetching_new_token is not None:
            await self._fetching_new_token.wait()
            return self._access_token

        self._access_token = None
        self._fetching_new_token = asyncio.Event()

        try:
            _refresh_token = await self.fetch_refresh_token()
            LOGGER.error('refresh token %s',  _refresh_token)
        except Exception as e:
            LOGGER.error('Exception when fetching refresh token: %s', e)
            raise OauthException(500, 'Error when fetching refresh token')

        data = {'refresh_token': _refresh_token}
        headers = {'Content-Type': 'application/json'}

        refresh_response = await self._http_request(BASE_URL + 'oidc/refresh', 'post', headers=headers, json=data)
        if not 'access_token' in refresh_response:
            LOGGER.warning('OAuth token refresh did not yield access token! Got back %s', refresh_response)
        else:
            self._access_token = 'Bearer ' + refresh_response['access_token']

        self._fetching_new_token.set()
        self._fetching_new_token = None

        return self._access_token

    async def _clear_refresh_token(self):
        global _refresh_token
        _refresh_token = None

    async def fetch_refresh_token(self):
        """ Fetch refresh token """
        global _refresh_token

        if _refresh_token is None:
            LOGGER.debug('No refresh token found, fetching refresh token')
            _refresh_token = await self._get_refresh_token(self._username, self._password)

        return _refresh_token

    async def _get_refresh_token(self, username, password):
        _cookie = None
        _json = None
        _ondus_url = None

        async with self._session.request('get', BASE_URL + 'oidc/login') as response:
            _cookie = response.cookies
            _text = await response.text()
            tree = html.fromstring(_text)
            _name = tree.xpath("//html/body/div/div/div/div/div/div/div/form")
            _action = _name[0].action

        _payload = {'username': username,
                    'password': password,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'origin': GROHE_BASE_URL,
                    'referer': BASE_URL + 'oidc/login',
                    'X-Requested-With': 'XMLHttpRequest'}

        async with self._session.request('post', url=_action, data=_payload, cookies=_cookie, allow_redirects=False) as response:
            _ondus_url = response.headers['location'].replace('ondus', 'https')

        async with self._session.request('get', _ondus_url, cookies=_cookie) as response:
            _json = await response.json()

        return _json['refresh_token']
