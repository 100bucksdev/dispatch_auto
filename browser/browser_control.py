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
        print("[INFO] Инициализация браузера...")
        self.headless = headless
        self.user_agent = random.choice(self.USER_AGENTS)
        self.viewport = random.choice(self.VIEWPORT_SIZES)
        print(f"[DEBUG] User-Agent: {self.user_agent}")
        print(f"[DEBUG] Viewport: {self.viewport}")

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
        print("[INFO] Браузер успешно запущен")

    def set_offline_mode(self, offline: bool = True):
        self.context.set_offline(offline)
        print(f"[INFO] Установлен оффлайн режим: {offline}")

    def navigate(self, url: str, wait_until_full_load: bool = True):
        if self.page:
            print(f"[INFO] Переход по ссылке: {url}")
            self.page.goto(url, wait_until='networkidle' if wait_until_full_load else None)

            if wait_until_full_load:
                self.page.wait_for_load_state('networkidle')

            if self.page.url == url:
                print("[SUCCESS] Страница загружена успешно.")
                if wait_until_full_load:
                    time.sleep(3)
                    content = self.page.content()
                    if "SIGN IN" in content:
                        print("[ERROR] Обнаружено окно входа. Требуется обновление localStorage.")
                        self.browser.close()
                        raise CustomBadRequestWithDetail('update_local_storage')
            else:
                print("[ERROR] Не удалось загрузить страницу.")
                self.browser.close()
                raise CustomBadRequestWithDetail('update_local_storage')

    def get_cookies(self):
        print("[INFO] Получение cookies из контекста")
        return self.context.cookies()

    def open_new_tab(self, url: str):
        print(f"[INFO] Открытие новой вкладки с URL: {url}")
        self.page = self.context.new_page()
        self.page.goto(url)

    def set_local_storage_from_string(self, local_storage: str):
        data = json.loads(local_storage)
        print(f"[INFO] Установка localStorage: {data}")
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
        print("[INFO] Блокировка редиректов включена")
        def intercept(route, request):
            if 300 <= request.response().status < 400:
                route.abort()
            else:
                route.continue_()
        self.page.route("**/*", intercept)

    def unblock_redirects(self):
        print("[INFO] Блокировка редиректов отключена")
        self.page.unroute("**/*")

    def set_cookies_from_string(self, cookies: str):
        jsoned_cookies = json.loads(cookies)
        print(f"[INFO] Установка cookies: {jsoned_cookies}")
        for cookie in jsoned_cookies:
            if "sameSite" in cookie:
                cookie["sameSite"] = cookie["sameSite"].capitalize()
        self.context.add_cookies(jsoned_cookies)

    def close(self):
        print("[INFO] Закрытие браузера...")
        if self.browser:
            self.browser.close()
            print("[INFO] Браузер закрыт")
