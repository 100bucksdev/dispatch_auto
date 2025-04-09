import re
import random
import json
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
        login_url = 'https://id.centraldispatch.com/Account/Login'
        if self.page:
            self.page.goto(url, wait_until='networkidle' if wait_until_full_load else None)
            if self.page.url == url:
                print("Page loaded successfully.")
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



def process_json(input_text: str) -> dict:
    def fix_json_format(text: str) -> str:
        """
        Функция исправляет формат JSON-строки, добавляя кавычки вокруг ключей.
        """
        # Ищем случаи вида {key: или , key:
        pattern = r'([{,]\s*)([A-Za-z0-9_.\-\$]+)\s*:'
        fixed = re.sub(pattern, r'\1"\2":', text)
        return fixed

    def process_json(input_text: str) -> dict:
        """
        Функция пытается преобразовать строку с ошибками в корректный JSON.
        Если в некоторых значениях есть строка, представляющая JSON-объект,
        производится дополнительное преобразование.
        """
        # Сначала исправляем исходный текст
        fixed_text = fix_json_format(input_text)

        # Пытаемся распарсить исправленную строку
        try:
            data = json.loads(fixed_text)
        except Exception as e:
            print("Ошибка при парсинге JSON:", e)
            raise

        # Если значение какого-либо ключа является строкой и содержит фигурные скобки,
        # пробуем преобразовать его в JSON-объект.
        for key, value in data.items():
            if isinstance(value, str) and value.strip().startswith("{") and value.strip().endswith("}"):
                try:
                    data[key] = json.loads(fix_json_format(value))
                except Exception:
                    # Если не удалось распарсить — оставляем исходное значение
                    pass
        return data

    result = process_json(input_text)

    formatted_json = json.dumps(result, indent=2, ensure_ascii=False)
    return json.loads(formatted_json)