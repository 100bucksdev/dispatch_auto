import json
import os
import time
import random
from datetime import timedelta, datetime

from browser.browser_control import Browser
from exeption import CustomBadRequestWithDetail

BASE_URL = 'https://app.centraldispatch.com/'


class Listing:

    _LISTING_URL = 'https://app.centraldispatch.com/listing-editor'


    _DEFAULT_TEXT_VEHICLE_INFO = '''Please pick up the TITLE and Keys !Please take some PHOTOS around the car AT PICK UP and DROP OFF  send it to 954-703-4009 or  logisticsTauto@gmail.com !
I’m paying on delivery by ZELLE'''


    def __init__(self, order: dict, local_storage: str, headless: bool = True):
        self.browser = Browser(headless=headless)
        self.order = order
        self.loca_storage = local_storage

    def get_processed_terminal(self):
        terminals = ['SAVANNAH', 'NEW YORK', 'MIAMI']
        terminal = self.order.get('terminal')
        if terminal.upper() not in terminals:
            raise CustomBadRequestWithDetail(f"invalid_terminal_in_order")

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
            raise CustomBadRequestWithDetail(f"invalid_location_in_order")
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
            raise CustomBadRequestWithDetail(f"invalid_vin_in_order")
        return vin



    def set_local_storage(self):
        while True:
            try:
                self.browser.navigate(self._LISTING_URL, False)
                loader_selector = '.root-loader.root-interstitial-panel'
                self.browser.page.wait_for_selector(
                    loader_selector,
                    state='visible',
                    timeout=30000
                )
                self.browser.set_offline_mode(True)
                self.browser.set_local_storage_from_string(fr'{self.loca_storage}')
                self.browser.set_offline_mode(False)
                self.browser.navigate(self._LISTING_URL)
                break
            except TimeoutError:
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
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.fill_string_field_by_id('delivery-location-name', self.get_processed_terminal())
        time.sleep(0.6)
        self.browser.page.wait_for_selector('#ids-search-input-listbox-delivery-location-name')
        time.sleep(0.2)
        self.browser.page.locator('#ids-search-input-listbox-delivery-location-name li').first.click()
        time.sleep(0.2)
        self.fill_string_field_by_id('ids-combo-box-input-delivery-location-type', 'Terminal')
        time.sleep(0.2)
        self.browser.page.wait_for_selector('#listbox-item-Terminal')
        time.sleep(0.2)
        self.browser.page.locator('#listbox-item-Terminal').click()

    def fill_vehicle_info(self):
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.browser.page.locator('[data-testid="listings_editor_vin_input_0"]').fill(self.get_vin())
        time.sleep(0.2)
        self.browser.page.locator('[name="vehicle-detail-text-area-row"]').fill(self._DEFAULT_TEXT_VEHICLE_INFO)
        time.sleep(0.2)

    def fill_delivery_details(self):
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        price = self.get_price_for_delivery()

        date_pickup_field = self.browser.page.locator("#listings_editor_date-available-to-ship")
        date_delivery_field = self.browser.page.locator("#listings_editor_desired-delivery-date")

        current_date = datetime.now()
        future_date = current_date + timedelta(days=3)
        current_date_str = current_date.strftime("%m/%d/%Y")
        future_date_str = future_date.strftime("%m/%d/%Y")
        date_pickup_field.fill(current_date_str)
        time.sleep(0.2)
        date_delivery_field.fill(future_date_str)
        time.sleep(0.2)
        self.browser.page.locator('#amount-to-pay-carrier').fill(price)
        time.sleep(0.2)
        self.browser.page.locator('#cod-amount').fill(price)
        time.sleep(1)

        self.browser.page.locator('#cod-payment-method').click()
        self.browser.page.wait_for_selector('#listbox-item-Cash\\/CertifiedFunds')
        self.browser.page.locator('#listbox-item-Cash\\/CertifiedFunds').first.click()
        time.sleep(0.2)
        self.browser.page.locator('#cod-location').click()
        time.sleep(0.2)
        self.browser.page.wait_for_selector('#listbox-item-Delivery')
        self.browser.page.locator('#listbox-item-Delivery').first.click()
        time.sleep(0.2)

    def fill_additional_info(self):
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)
        self.browser.page.locator('#addtional-info-loadid').fill(f'{self.get_vin()[-6:]} TITLE MUST BE PICKED UP')
        time.sleep(0.2)
        self.browser.page.locator('#addtional-info-terms').fill('Forklift on/off **Pick Up TITLE!** Zelle/wire payment')
        time.sleep(0.2)
        self.browser.page.locator('.interstate-checkbox-input').click()

    def fill_all_fields(self):
        if self.browser.page.url != self._LISTING_URL:
            self.browser.navigate(self._LISTING_URL)

        self.fill_pickup_info()
        self.fill_delivery_info()
        self.fill_vehicle_info()
        self.fill_delivery_details()
        self.fill_additional_info()

    def get_screenshots(self):
        self.browser.page.evaluate("window.scrollTo(0, 0)")
        screenshot_path = 'pickup_location.png'
        self.browser.page.screenshot(path=screenshot_path)
        with open(screenshot_path, 'rb') as f:
            image_data = f.read()
        return image_data

    def delete_screenshots(self):
        if os.path.exists('pickup_location.png'):
            os.remove('pickup_location.png')
        self.browser.close()



    def post_listing(self):
        self.browser.page.locator('#post-listing-btn').click()
        time.sleep(2)
        self.browser.close()

    def fill_string_field_by_id(self, field_id: str, value: str, delay=0.0):
        field = self.browser.page.locator(f'#{field_id}')
        if delay == 0.0:
            field.fill(value)
            return
        field.click()
        for char in value:
            field.type(char)
            time.sleep(random.uniform(0.1, delay))

    def fill_one_char_in_field_by_id(self, field_id: str, value: str):
        field = self.browser.page.locator(f'#{field_id}')
        field.click()
        field.type(value)

    def fill_listing_info(self):
        self.fill_string_field_by_id('pickup-location-name', self.vehicle['location'])

    def get_price_for_delivery(self):
        self.browser.page.locator('.check-price-button').click()
        self.browser.page.wait_for_selector('table tbody tr')

        first_data_row = self.browser.page.locator('table tbody tr').first

        self.browser.page.wait_for_selector('label:has-text("Status")')

        column = first_data_row.locator('td.ant-table-cell.column-listed-price')
        price = column.locator('div').first.inner_text().strip()

        self.browser.page.locator('#ids-slideout-close-button').click()

        return price.replace('$', '')

