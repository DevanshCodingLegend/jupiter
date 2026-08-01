import asyncio
import threading
import time
import warnings
warnings.filterwarnings("ignore")

_browser = None
_page = None
_playwright = None
_loop = None
_thread = None

def _run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def get_loop():
    global _loop, _thread
    if _loop is None or not _loop.is_running():
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(target=_run_loop, args=(_loop,), daemon=True)
        _thread.start()
    return _loop

def run_async(coro):
    loop = get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)

async def _launch_browser():
    global _browser, _page, _playwright
    from playwright.async_api import async_playwright
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.connect_over_cdp("http://localhost:9222")
    contexts = _browser.contexts
    if contexts:
        pages = contexts[0].pages
        _page = pages[0] if pages else await contexts[0].new_page()
    return True

async def _get_page():
    global _page, _browser
    if _browser is None:
        return None
    try:
        contexts = _browser.contexts
        if contexts:
            pages = contexts[0].pages
            if pages:
                return pages[0]
    except:
        pass
    return _page

async def _navigate(url):
    page = await _get_page()
    if page:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Navigated to {url}"
    return "Browser not connected"

async def _click_tab_with_title(title):
    global _page
    if _browser is None:
        return "Browser not connected"
    for context in _browser.contexts:
        for page in context.pages:
            t = await page.title()
            if title.lower() in t.lower():
                await page.bring_to_front()
                _page = page
                return f"Switched to tab: {t}"
    return f"No tab found matching '{title}'"

async def _get_all_tabs():
    tabs = []
    if _browser is None:
        return tabs
    for context in _browser.contexts:
        for page in context.pages:
            try:
                title = await page.title()
                url = page.url
                tabs.append({"title": title, "url": url})
            except:
                pass
    return tabs

async def _click_element(selector_or_text):
    page = await _get_page()
    if not page:
        return "No page active"
    try:
        await page.click(f"text={selector_or_text}", timeout=5000)
        return f"Clicked: {selector_or_text}"
    except:
        try:
            await page.click(selector_or_text, timeout=5000)
            return f"Clicked element"
        except Exception as e:
            return f"Could not click: {e}"

async def _type_in_browser(text, press_enter=False):
    page = await _get_page()
    if not page:
        return "No page active"
    await page.keyboard.type(text)
    if press_enter:
        await page.keyboard.press("Enter")
    return f"Typed: {text}"

async def _get_page_content():
    page = await _get_page()
    if not page:
        return ""
    try:
        content = await page.inner_text("body")
        return content[:3000]
    except:
        return ""

async def _scroll(direction="down"):
    page = await _get_page()
    if not page:
        return "No page"
    if direction == "down":
        await page.keyboard.press("PageDown")
    elif direction == "up":
        await page.keyboard.press("PageUp")
    elif direction == "top":
        await page.keyboard.press("Control+Home")
    elif direction == "bottom":
        await page.keyboard.press("Control+End")
    return f"Scrolled {direction}"

async def _new_tab(url=""):
    if _browser is None:
        return "Browser not connected"
    context = _browser.contexts[0] if _browser.contexts else None
    if context:
        page = await context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        global _page
        _page = page
        return f"New tab opened{': ' + url if url else ''}"
    return "Could not open tab"

async def _close_current_tab():
    page = await _get_page()
    if page:
        await page.close()
        return "Tab closed"
    return "No tab to close"

async def _search_on_page(query):
    page = await _get_page()
    if not page:
        return "No page"
    await page.keyboard.press("Control+f")
    await asyncio.sleep(0.3)
    await page.keyboard.type(query)
    return f"Searching page for: {query}"

# Public API
def connect_browser():
    try:
        return run_async(_launch_browser())
    except Exception as e:
        return f"Browser connect failed: {e}"

def navigate(url):
    if not url.startswith("http"):
        url = f"https://{url}" if "." in url else f"https://www.google.com/search?q={url.replace(' ', '+')}"
    return run_async(_navigate(url))

def switch_to_tab(title):
    return run_async(_click_tab_with_title(title))

def get_all_tabs():
    return run_async(_get_all_tabs())

def click(text_or_selector):
    return run_async(_click_element(text_or_selector))

def type_text_browser(text, press_enter=False):
    return run_async(_type_in_browser(text, press_enter))

def scroll(direction="down"):
    return run_async(_scroll(direction))

def new_tab(url=""):
    return run_async(_new_tab(url))

def close_tab():
    return run_async(_close_current_tab())

def get_page_content():
    return run_async(_get_page_content())

def search_on_page(query):
    return run_async(_search_on_page(query))

def launch_chrome_debug():
    import subprocess
    import os
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            subprocess.Popen([
                path,
                "--remote-debugging-port=9222",
                "--user-data-dir=C:\\ChromeDebug"
            ])
            time.sleep(2)
            return connect_browser()
    return "Chrome not found"

if __name__ == "__main__":
    print("Launching Chrome with debug port...")
    result = launch_chrome_debug()
    print(f"Connected: {result}")
    
    tabs = get_all_tabs()
    print(f"Open tabs: {tabs}")
    
    result = navigate("https://claude.ai")
    print(result)