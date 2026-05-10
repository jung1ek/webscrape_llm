import json

from playwright.async_api import async_playwright

from utils.helper import clean_cookies

_pw = None
_browser = None

_page_no_cookie = None
_page_with_cookie = None


async def get_page(with_cookie: bool = False):
    global _pw, _browser
    global _page_no_cookie, _page_with_cookie

    # start playwright/browser once
    if _pw is None:
        _pw = await async_playwright().start()

    if _browser is None:
        _browser = await _pw.chromium.launch(headless=True)

    # WITH LOGIN COOKIE
    if with_cookie:

        # if already created, reuse it
        if _page_with_cookie is not None:
            return _page_with_cookie

        context = await _browser.new_context()

        # load cookies
        with open("auth.json", "r") as f:
            data = json.load(f)

        data = clean_cookies(data)

        await context.add_cookies(data)

        _page_with_cookie = await context.new_page()

        return _page_with_cookie

    # WITHOUT COOKIE
    else:

        # if already created, reuse it
        if _page_no_cookie is not None:
            return _page_no_cookie

        context = await _browser.new_context()

        _page_no_cookie = await context.new_page()

        return _page_no_cookie


async def close_browser():
    global _pw, _browser, _page

    if _browser: await _browser.close()
    if _pw: await _pw.stop()
    _pw = _browser = _page = None