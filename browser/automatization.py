import os
import time
import random
from datetime import timedelta, datetime

from browser.browser_control import Browser
from exeption import CustomBadRequestWithDetail

BASE_URL = 'https://app.centraldispatch.com/'


class Listing:
    _LISTING_URL = 'https://app.centraldispatch.com/listing-editor'

    _DEFAULT_TEXT_VEHICLE_INFO = '''Please pick up the TITLE and Keys !Please take some PHOTOS around the car AT PICK UP and DROP OFF  send it to 954-703-4009 or  logisticsTauto@gmail.com !\nI’m paying on delivery by ZELLE'''

    def __init__(self, order: dict, local_storage: str, headless: bool = True):
        self.browser = Browser(headless=headless)
        self.order = order
        self.loca_storage = local_storage

    def get_processed_terminal(self):
        terminals = ['SAVANNAH', 'NEW YORK', 'MIAMI']
        terminal = self.order.get('terminal')
        if terminal.upper() not in terminals:
            raise CustomBadRequestWithDetail("invalid_terminal_in_order")

        terminals = {
            'SAVANNAH': 'JAX AUTO SHIPPING INC NEW!!!',
            'NEW YORK': 'SOTBY Transatlantic Line NEW',
            'MIAMI': 'SEAWORLD SHIPPING INC'
        }
        return terminals[terminal.upper()]

    def get_location(self):
        location = self.order.get('auction_city').get('location')
        if location:
            location = ''.join(char for char in location if not char.isdigit())
            while '(' in location and ')' in location:
                start = location.index('(')
                end = location.index(')') + 1
                location = location[:start] + location[end:]

        if not location:
            raise CustomBadRequestWithDetail("invalid_location_in_order")
        return location.strip()

    def get_auction(self):
        auctions = ['IAAI', 'COPART']
        auction = self.order.get('auction_name')
        if auction.upper() not in auctions:
            raise CustomBadRequestWithDetail(f"Invalid auction: {auction}")
        return auction

    def get_vin(self):
        vin = self.order.get('vin')
        if not vin:
            raise CustomBadRequestWithDetail("invalid_vin_in_order")
        return vin

    def set_local_storage(self):
        while True:
            try:
                print("[INFO] Навигация на страницу для установки local storage")
                self.browser.navigate(self._LISTING_URL, False)
                loader_selector = '.root-loader.root-interstitial-panel'
                print("[INFO] Ожидание загрузки лоадера")
                self.browser.page.wait_for_selector(loader_selector, state='visible', timeout=30000)

                print("[INFO] Включение offline режима и установка local storage")
                self.browser.set_offline_mode(True)
                self.browser.set_local_storage_from_string(fr'{self.loca_storage}')
                self.browser.set_offline_mode(False)

                print("[INFO] Повторная навигация после установки local storage")
                self.browser.navigate(self._LISTING_URL)
                break
            except TimeoutError:
                print("[ERROR] Timeout при установке local storage")
                return 'new_local_storage_needed'

    def fill_pickup_info(self):
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            try:
                # Формируем исходную строку
                original_string = f'{self.get_auction()} {self.get_location()}'.upper()

                strings_to_try = [original_string]
                if '-' in original_string:
                    strings_to_try.append(original_string.replace('-', ' '))

                success = False

                for current_string in strings_to_try:
                    if success:
                        break

                    self.fill_string_field_by_id('pickup-location-name', '')
                    time.sleep(0.5)

                    for char in current_string:
                        self.fill_one_char_in_field_by_id('pickup-location-name', char)
                        time.sleep(random.uniform(0.2, 0.6))

                        try:

                            self.browser.page.wait_for_selector('#ids-search-input-listbox-pickup-location-name',
                                                                timeout=3000)

                            list_items = self.browser.page.locator('#ids-search-input-listbox-pickup-location-name li')
                            if list_items.first.inner_text().upper() == current_string:
                                # Если первый элемент совпадает с искомым, кликаем по нему
                                time.sleep(0.4)
                                list_items.first.click()
                                success = True
                                break
                            item_count = list_items.count()
                            if item_count == 1:
                                time.sleep(0.4)
                                list_items.first.click()
                                success = True
                                break
                        except Exception as e:

                            continue

                    if success:
                        break

                if success:
                    # Если успешно выбрали локацию, переходим к выбору типа
                    time.sleep(0.2)
                    self.fill_string_field_by_id('ids-combo-box-input-pickup-location-type', 'Auction')
                    time.sleep(0.2)
                    self.browser.page.wait_for_selector('#listbox-item-Auction')
                    time.sleep(0.2)
                    self.browser.page.locator('#listbox-item-Auction').click()
                    return
                else:
                    # Если не удалось выбрать локацию, увеличиваем счетчик попыток
                    attempt += 1
                    time.sleep(1)
            except Exception as e:
                attempt += 1
                time.sleep(1)

        if attempt >= max_attempts:
            self.browser.close()
            raise CustomBadRequestWithDetail('maximal_attempts_reached_while_filling_pickup_location')

    def fill_delivery_info(self):
        print("[INFO] Заполнение Delivery Info")
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.fill_string_field_by_id('delivery-location-name', self.get_processed_terminal())
        self.browser.page.wait_for_selector('#ids-search-input-listbox-delivery-location-name')
        self.browser.page.locator('#ids-search-input-listbox-delivery-location-name li').first.click()
        self.fill_string_field_by_id('ids-combo-box-input-delivery-location-type', 'Terminal')
        self.browser.page.wait_for_selector('#listbox-item-Terminal')
        self.browser.page.locator('#listbox-item-Terminal').click()
        print("[INFO] Delivery Info заполнено")

    def fill_vehicle_info(self):
        print("[INFO] Заполнение Vehicle Info")
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.browser.page.locator('[data-testid="listings_editor_vin_input_0"]').fill(self.get_vin())
        self.browser.page.locator('[name="vehicle-detail-text-area-row"]').fill(self._DEFAULT_TEXT_VEHICLE_INFO)

    def fill_delivery_details(self):
        print("[INFO] Заполнение Delivery Details")
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        price = self.get_price_for_delivery()
        print(f"[DEBUG] Получена цена доставки: {price}")

        current_date = datetime.now()
        future_date = current_date + timedelta(days=3)
        self.browser.page.locator("#listings_editor_date-available-to-ship").fill(current_date.strftime("%m/%d/%Y"))
        self.browser.page.locator("#listings_editor_desired-delivery-date").fill(future_date.strftime("%m/%d/%Y"))
        self.browser.page.locator('#amount-to-pay-carrier').fill(price)
        self.browser.page.locator('#cod-amount').fill(price)
        self.browser.page.locator('#cod-payment-method').click()
        self.browser.page.wait_for_selector('#listbox-item-Cash\\/CertifiedFunds')
        self.browser.page.locator('#listbox-item-Cash\\/CertifiedFunds').click()
        self.browser.page.locator('#cod-location').click()
        self.browser.page.wait_for_selector('#listbox-item-Delivery')
        self.browser.page.locator('#listbox-item-Delivery').click()

    def fill_additional_info(self):
        print("[INFO] Заполнение Additional Info")
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.browser.page.locator('#addtional-info-loadid').fill(f'{self.get_vin()[-6:]} TITLE MUST BE PICKED UP')
        self.browser.page.locator('#addtional-info-terms').fill('Forklift on/off **Pick Up TITLE!** Zelle/wire payment')
        self.browser.page.locator('.interstate-checkbox-input').click()

    def fill_all_fields(self):
        print("[INFO] Начало заполнения всех полей")
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.fill_pickup_info()
        self.fill_delivery_info()
        self.fill_vehicle_info()
        self.fill_delivery_details()
        self.fill_additional_info()
        print("[INFO] Все поля успешно заполнены")

    def get_screenshots(self):
        self.browser.page.evaluate("window.scrollTo(0, 0)")
        screenshot_path = 'pickup_location.png'
        self.browser.page.screenshot(path=screenshot_path)
        with open(screenshot_path, 'rb') as f:
            return f.read()

    def delete_screenshots(self):
        if os.path.exists('pickup_location.png'):
            os.remove('pickup_location.png')
        self.browser.close()

    def post_listing(self):
        print("[INFO] Публикация листинга")
        self.browser.page.locator('#post-listing-btn').click()
        time.sleep(2)
        self.browser.close()
        print("[INFO] Листинг опубликован и браузер закрыт")

    def fill_string_field_by_id(self, field_id: str, value: str, delay=0.0):
        field = self.browser.page.locator(f'#{field_id}')
        if delay == 0.0:
            field.fill(value)
        else:
            field.click()
            for char in value:
                field.type(char)
                time.sleep(random.uniform(0.1, delay))

    def fill_one_char_in_field_by_id(self, field_id: str, value: str):
        field = self.browser.page.locator(f'#{field_id}')
        field.click()
        field.type(value)

    def get_price_for_delivery(self):
        print("[INFO] Получение цены доставки")
        self.browser.page.locator('.check-price-button').click()
        self.browser.page.wait_for_selector('table tbody tr')
        self.browser.page.wait_for_selector('label:has-text("Status")')
        price = self.browser.page.locator('table tbody tr td.ant-table-cell.column-listed-price div').first.inner_text().strip()
        self.browser.page.locator('#ids-slideout-close-button').click()
        return price.replace('$', '')
