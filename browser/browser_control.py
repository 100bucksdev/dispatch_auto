import random
import json
import time

from playwright.sync_api import sync_playwright

from exeption import CustomBadRequestWithDetail


class Browser:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    ]

    VIEWPORT_SIZES = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
    ]

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.user_agent = random.choice(self.USER_AGENTS)
        self.viewport = random.choice(self.VIEWPORT_SIZES)
        self.browser = sync_playwright().start().chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent=self.user_agent,
            locale="en-US",
            timezone_id="UTC",

        )
        self.context.add_init_script(script="Object.defineProperty(navigator, 'webdriver', {get: () => false})")
        self.page = self.context.new_page()

        self.context.clear_cookies()
        self.context.clear_permissions()

    def set_offline_mode(self, offline: bool = True):
        self.context.set_offline(offline)

    def navigate(self, url: str, wait_until_full_load: bool = True):
        if self.page:
            # Navigate to the URL
            self.page.goto(url, wait_until='networkidle' if wait_until_full_load else None)

            if wait_until_full_load:
                self.page.wait_for_load_state('networkidle')

            if self.page.url == url:
                print("Page loaded successfully.")
                if wait_until_full_load:
                    time.sleep(3)
                    content = self.page.content()
                    if "SIGN IN" in content:
                        self.browser.close()
                        raise CustomBadRequestWithDetail('update_local_storage')
            else:
                print("Page failed to load.")
                self.browser.close()
                raise CustomBadRequestWithDetail('update_local_storage')



    def get_cookies(self):
        return self.context.cookies()

    def open_new_tab(self, url: str):
        self.page = self.context.new_page()
        self.page.goto(url)

    def set_local_storage_from_string(self, local_storage: str):
        data = json.loads(local_storage)
        print(data)
        self.page.evaluate("""
            (data) => {
                localStorage.clear();
                for (const [key, value] of Object.entries(data)) {
                    console.log(key, value);
                    localStorage.setItem(key, value);
                }
            }
        """, data)


    def block_redirects(self):
        def intercept(route, request):
            if 300 <= request.response().status < 400:
                route.abort()
            else:
                route.continue_()

        self.page.route("**/*", intercept)

    def unblock_redirects(self):
        self.page.unroute("**/*")


    def set_cookies_from_string(self, cookies: str):
        jsoned_cookies = json.loads(cookies)
        for cookie in jsoned_cookies:
            if "sameSite" in cookie:
                cookie["sameSite"] = cookie["sameSite"].capitalize()
        self.context.add_cookies(jsoned_cookies)

    def close(self):
        if self.browser:
            self.browser.close()

