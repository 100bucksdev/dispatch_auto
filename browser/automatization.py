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


    def __init__(self, order: dict, local_storage: str, headless: bool = False):
        self.browser = Browser(headless=headless)
        if type(order) == str:
            order = json.loads(order)
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
                            print('first_element' + list_items.first.inner_text())
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












if __name__ == '__main__':


    order = ('{"id":1101,'
             '"auction_city":{"id":139,"location":"Pittsburgh-North 15044","city":"Gibsonia","state":"PA","postal_code":"15044","savannah":0,"nj":450,"houston":0,"miami":0,"chicago":0,"email":null},'
             '"auction_image":[],'
             '"container":{"destination":null,"ship_line":"","vessel":"","container_key":""},'
             '"user":{"id":673,"delivery_info":{"id":76,"country":"Lithuania",'
             '"state":"Vilnius City Municipality",'
             '"zip_code":6326,"city":"Vilnius","address":"Mykolo Slezeviciaus g. 7"},'
             '"is_superuser":false,"first_name":"UAB Aftersales supervision",'
             '"last_name":"306228615",'
             '"is_staff":false,'
             '"email":"edvinas.turka@gmail.com",'
             '"phone_number":"+37060007971","is_email_confirmed":true,"is_phone_confirmed":true,"country":"LT"},"delivery_status":"pending_payment","appeal":null,"assigned_vehicle":null,"depth_video":{"is_depth_video":false,"is_video_attached":false,"depth_video_url":null},"items":{"2017 SUBARU FORESTER (JF2SJGEC0HH404755)":3200,"Auction Fee":505,"Title Mailing Fee":20,"Broker Fee":275,"Environmental Fee":15,"Premium Vehicle Report":15,"Auction Service Fee":95,"Ocean Transportation":775,"Local Transportation":450,"Internet Bid Fee":110},"created_at":"2025-04-04T00:00:00Z","updated_at":"2025-04-04T10:52:28.169772Z","auction_name":"IAAI","lot_id":41456874,"from_dealer":false,"terminal":"NEW YORK","car_value":3200,"extra_fee":[{"name":"","amount":0}],"invoice_type":"t_autologistics_invoice","vehicle_type":"CAR","vin":"JF2SJGEC0HH404755","vehicle_name":"2017 SUBARU FORESTER","keys":true,"damage":true,"color":"Blue","auto_generated":false,"fee_type":"non_clean_title_fee"}')
    order = json.loads(order)



    local_storage = r'{"tcUntilDate":"null","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$contextual_mab":"{}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$layer_map":"{}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$variation_map":"{}","oidc.5f3949a31c744b8aa9132fd79942f9f3":"{\"id\":\"5f3949a31c744b8aa9132fd79942f9f3\",\"created\":1744204339,\"request_type\":\"si:s\",\"code_verifier\":\"0ffc96a295194c6487b8d0968454ab6e35b3a422612e46e3bb1a611707d7ab72550706dc5bf54907925a7efc781a5de1\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","supportedCADYears":"{\"data\":[1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026],\"timestamp\":1744195748681}","oidc.0800b04b027347628cceb0520422d28c":"{\"id\":\"0800b04b027347628cceb0520422d28c\",\"created\":1743768672,\"request_type\":\"si:s\",\"code_verifier\":\"a055413447214edcb438bd8dd9768ea0ca761d00c9da4451be36c27450737047d096a49502d747438a4cfb620f02144a\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.4a07eff6defe4da6afc7c6bc02a5b9cd":"{\"id\":\"4a07eff6defe4da6afc7c6bc02a5b9cd\",\"created\":1744120069,\"request_type\":\"si:s\",\"code_verifier\":\"ced00b9610f648deba707ced074864ca83ffbf95ae054518b953b9596564893b6d5f1c3e73f148b3ac24d16a047c4b88\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.2f2502419c8940f8a486dd4443ac45b3":"{\"id\":\"2f2502419c8940f8a486dd4443ac45b3\",\"created\":1744120069,\"request_type\":\"si:s\",\"code_verifier\":\"340aae8994cc4f8eabf3a1cf9dfafffeae20f7f2b4b344428660e4c1a00e666a385c5766116c450fa4cde2917cfa89cc\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.fea674aa9e2845f8b10944b073178823":"{\"id\":\"fea674aa9e2845f8b10944b073178823\",\"created\":1744142007,\"request_type\":\"si:s\",\"code_verifier\":\"db606f82d4424a3ea8a579633bcb8f8231ac87507dbe45bc8ac8d4ff07106fd3a9097c3755674b438a6c4af112353ff8\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","NavBffKey":"eyJhbGciOiJSUzI1NiIsImtpZCI6IjFFODM0OTZCMjNCQzM4MTIzREM2NEU4M0UyMTg1RjdEIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDQyMTgzMTQsImlhdCI6MTc0NDIxODMxNCwiZXhwIjoxNzQ0MjIwMTE0LCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJ0YXV0dmlzbCIsImF1dGhfdGltZSI6MTc0MzQxOTI2MSwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6InRhdXR2aXNsIiwidGllckdyb3VwIjoiQnJva2VyIiwiY29tcGFueU5hbWUiOiJUIEF1dG8gTG9naXN0aWNzIExMQyIsImN1c3RvbWVySWQiOiIwNzI2MThkNi1kYzJlLTQ5MDYtYjVmNi01OTQxMGFhM2E1OTIiLCJhY3RpdmF0aW9uRGF0ZSI6IjIwMjAtMTEtMTkgMDY6NDE6NDYiLCJhY2NvdW50U3RhdHVzIjoiQWN0aXZlIiwiaXNBY3RpdmUiOnRydWUsInVzZXJJZCI6IjVjMjU4N2UyLTc0MTgtNDFjZS1hZjI2LWVjNGZjMzQ4ZDRlYSIsInJvbGVzIjpbIk9XTkVSIl0sIm1hcmtldFBsYWNlSWRzIjpbMTAwMDBdLCJtYXJrZXRwbGFjZXMiOlt7Ik1hcmtldHBsYWNlSWQiOjEwMDAwLCJBY3RpdmUiOnRydWUsIlJlYXNvbkNvZGUiOiJDT01QTEVURV9BQ1RJVkFURUQifV0sIm51bWJlck9mQWNjb3VudHMiOiIxIiwibG9naW5Vc2VybmFtZSI6InRhdXR2aXNsIiwiZmlyc3ROYW1lIjoiVGF1dHZ5ZGFzIiwibGFzdE5hbWUiOiJMdWthdXNrYXMiLCJlbWFpbCI6ImxvZ2lzdGljc3RhdXRvQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI1ZTZmNzY3Ny0xNjNkLTRlOTItYWUwZC1iNWJhN2VkN2UwYmMiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9LHsiUHJvZHVjdElkIjoiZWE5MDAzNWYtNTU2Ni00YmYwLTljMzgtYTIzZTBkYWY0YWYzIiwiTWFya2V0cGxhY2VJZCI6MTAwMDAsIlByb2R1Y3RTdGF0dXNLZXkiOiJhY3RpdmUifV0sIm1mYUV4cGlyYXRpb24iOiIxNzQzNDIyODYxIiwicGFydG5lcklkIjoiIiwic2lkIjoiQzNCQzgxNzJDMTU5QkNDOEEzMTgwQjkwQzMzNjAxNjkifQ.V2x3dCyOcb8Y5EjEdKSCGvZh0yVlM-qyOy4_q3GYoxgzwxm7FYVDp_zNABpZBpNtrzLxbNDokUyBF5ejDpJmOCO7Eb0WHWF0KGluAXpz096Rg7OPcfg5QJjg6DilU1PH9UzJbPpSJ_OuxceO0ugNjSi4TQeLvnLLpmeUxKFzvckg2uFu0OimWGfGzKpmkInQo98DInLFC3YruRiroE0LBP2QGCVbIQR4GgGlyCHanHkXKx_ONV5jHcpJaUY-q2TwTyKK2uJvgmD1-htOXA0Gn6ZCqMF6DcciqlAcFWxqZpCXHK8hWNzXKjIIPxhe1r64rxUjZO4ghxw66LDNqOpwHQ","oidc.621bd8742e3d4c2c933e9886294694e6":"{\"id\":\"621bd8742e3d4c2c933e9886294694e6\",\"created\":1743512404,\"request_type\":\"si:s\",\"code_verifier\":\"1e9b3a9936fc41a4b0e35325d59f511cd85bd4a5c7944e91a894273604e55000187cf41d33eb4526903d579d0e16a410\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","showTCBanner":"false","optimizely_data$$pending_events":"{\"07b7fed2-4cdd-484a-9a97-55f7d6fa4044\":{\"id\":\"07b7fed2-4cdd-484a-9a97-55f7d6fa4044\",\"timeStamp\":1744218613468,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.221.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"460\",\"visitors\":[{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1744218286969,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"38424dda-9628-4d70-ad50-afd1a7940b96\",\"t\":1744210422833}]}]},{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1744218286969,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"1d724173-a019-426c-b7dd-1bb25316cd0e\",\"t\":1744211325810}]}]},{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1744218286969,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"6ae9e5e7-17e0-40c8-a1cb-2d638eb00dff\",\"t\":1744218287542}]}]}]}},\"retryCount\":3},\"7adec4d5-7265-43ec-8042-fc41de1b73df\":{\"id\":\"7adec4d5-7265-43ec-8042-fc41de1b73df\",\"timeStamp\":1744218613469,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.221.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"466\",\"visitors\":[{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1744218311849,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"90b848a8-08a2-4759-893c-a88db6ce1e2e\",\"t\":1744218311947}]}]}]}},\"retryCount\":2},\"453b0a15-b630-4364-86b0-f6644d68c030\":{\"id\":\"453b0a15-b630-4364-86b0-f6644d68c030\",\"timeStamp\":1744218614501,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.221.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"466\",\"visitors\":[{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1744218613473,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"8a6cf254-087c-43ad-95e3-92f6131fad83\",\"t\":1744218613489}]}]}]}},\"retryCount\":1}}","oidc.7623d3cd33a14f1b9163393d3256ff52":"{\"id\":\"7623d3cd33a14f1b9163393d3256ff52\",\"created\":1744204339,\"request_type\":\"si:s\",\"code_verifier\":\"91aa5b629e6a4e09812e31a66e423025907e90376afb43f0b1738751d90282db352360004a08436ea97061811a76802e\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$session_state":"{\"lastSessionTimestamp\":1744218613480,\"sessionId\":\"e3166f15-2ca0-4aa6-adbc-6c28153da0c4\"}","oidc.f681f521d87c49cb88cc0585ce3c601a":"{\"id\":\"f681f521d87c49cb88cc0585ce3c601a\",\"created\":1743768672,\"request_type\":\"si:s\",\"code_verifier\":\"fa549262ab514a3dba475a07fdcf475f87dd3acd64374a72b0bed1cb824ba17dc04937c0a26d45e4948596b1a6cce62c\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","DBLayout":"{\"lg\":[{\"i\":\"quickLinks\",\"x\":0,\"y\":0,\"w\":6,\"h\":192,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"savedSearch\",\"x\":0,\"y\":384,\"w\":6,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"offers\",\"x\":3,\"y\":192,\"w\":3,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"totalTransports\",\"x\":0,\"y\":654,\"w\":6,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"readyDispatch\",\"x\":6,\"y\":0,\"w\":6,\"h\":652,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"ratings\",\"x\":0,\"y\":192,\"w\":3,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false}],\"md\":[{\"i\":\"quickLinks\",\"x\":0,\"y\":0,\"w\":12,\"h\":184,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"savedSearch\",\"x\":0,\"y\":575,\"w\":12,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"offers\",\"x\":0,\"y\":384,\"w\":12,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"totalTransports\",\"x\":0,\"y\":844,\"w\":12,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"readyDispatch\",\"x\":0,\"y\":1113,\"w\":12,\"h\":651,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"ratings\",\"x\":0,\"y\":185,\"w\":12,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false}]}","oidc.fc13e29a5661434eb900f2364453be1d":"{\"id\":\"fc13e29a5661434eb900f2364453be1d\",\"created\":1743602089,\"request_type\":\"si:s\",\"code_verifier\":\"b92a39db533043249472ba6a672ab116639550038b364a249ce434517a7f5f0a332fa79de9d04d18ae82935b9827424d\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.5e1c9bc553e3420481003683cc7f0203":"{\"id\":\"5e1c9bc553e3420481003683cc7f0203\",\"created\":1744029216,\"request_type\":\"si:s\",\"code_verifier\":\"cc77d9bb399f46c3b2d312616cf6d6f9ae9fc45deec041fdb1fe27c7b3caefbd8f3d0008da394afd81f4675b032141b3\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.d6b7f245e47e4e7fa34b00e110d24ef2":"{\"id\":\"d6b7f245e47e4e7fa34b00e110d24ef2\",\"created\":1744064586,\"request_type\":\"si:s\",\"code_verifier\":\"0097a004d2eb4d8cab4cbd8503c1d1a3ff5749598f874d1da855f6c6b4d888d2ae9b80e4022a4491bb2ffbeb822fd69e\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$tracker_optimizely":"{}","oidc.c7328ec7cc0d43238a29e004b1595946":"{\"id\":\"c7328ec7cc0d43238a29e004b1595946\",\"created\":1744138091,\"request_type\":\"si:s\",\"code_verifier\":\"a68d9113649647deb685b1615fe17fe8d86e95324e5a444c88d44ffaefb2e1dafe07a928bd5a429282954f5cc64d8d74\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$visitor_profile":"{\"profile\":{\"visitorId\":\"oeu1743351239841r0.4479015369262427\",\"customBehavior\":{},\"first_session\":true,\"browserId\":\"gc\",\"browserVersion\":\"135.0.0.0\",\"device\":\"desktop\",\"device_type\":\"desktop_laptop\",\"referrer\":\"https://app.centraldispatch.com/\",\"source_type\":\"referral\"},\"metadata\":{\"visitorId\":{},\"events\":{},\"customBehavior\":{},\"first_session\":{},\"browserId\":{},\"browserVersion\":{},\"device\":{},\"device_type\":{},\"referrer\":{},\"source_type\":{}}}","tcCheckTime":"04/10/2025, 12:49","oidc.b01606714f9f470ab5a7b7de7131e89f":"{\"id\":\"b01606714f9f470ab5a7b7de7131e89f\",\"created\":1743587482,\"request_type\":\"si:s\",\"code_verifier\":\"9069fb8dea50445d9de22c124a310104954e255264904773b707fe32ad3bdc88bc3db288a0ed45989f7ef74c6919a3a6\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.bab206fe4617426ca357e50ec6433515":"{\"id\":\"bab206fe4617426ca357e50ec6433515\",\"created\":1744201434,\"request_type\":\"si:s\",\"code_verifier\":\"7d4683dd20404cfbb3bff5d09bea769bbcef0c145cc74a498e4b1f9b5e09c8498777cd8b2ab142f29dc997daac3bf170\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.5e07f60a2c034fbc85a0c8999c1bc53b":"{\"id\":\"5e07f60a2c034fbc85a0c8999c1bc53b\",\"created\":1743689476,\"request_type\":\"si:s\",\"code_verifier\":\"0951c09bcd29432c82638c24ec42686e6d149fa8fba34b36940bce3b7defb136e5d7a324860f4f23a229c013455d89e4\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$layer_states":"[]","supportedCADMakes_2017":"{\"data\":[\"Acura\",\"Alfa Romeo\",\"Aston Martin\",\"Audi\",\"Bentley\",\"BMW\",\"Buick\",\"Cadillac\",\"Chevrolet\",\"Chrysler\",\"Dodge\",\"Ferrari\",\"FIAT\",\"Ford\",\"Freightliner\",\"Genesis\",\"GMC\",\"Honda\",\"Hyundai\",\"INFINITI\",\"Jaguar\",\"Jeep\",\"Kia\",\"Lamborghini\",\"Land Rover\",\"Lexus\",\"Lincoln\",\"Lotus\",\"Maserati\",\"MAZDA\",\"McLaren\",\"Mercedes-Benz\",\"MINI\",\"Mitsubishi\",\"Nissan\",\"Porsche\",\"Ram\",\"Rolls-Royce\",\"smart\",\"Subaru\",\"Tesla\",\"Toyota\",\"Volkswagen\",\"Volvo\"],\"timestamp\":1744117926744}","oidc.9ba8c1dc78854ab897b45d5da70f6198":"{\"id\":\"9ba8c1dc78854ab897b45d5da70f6198\",\"created\":1743587482,\"request_type\":\"si:s\",\"code_verifier\":\"cdddb5651c5d4e61832be7f59eca13c97cc8ae3d08be4f9692818832299cdf877193e704c79b45b5ab96d90e86951f6f\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","supportedCADModels_2017_Subaru":"{\"data\":[\"BRZ\",\"Crosstrek\",\"Forester\",\"Impreza 5-Door\",\"Impreza Sedan\",\"Legacy\",\"Outback\",\"WRX\",\"WRX STi\"],\"timestamp\":1744117926515}","optimizely-vuid":"vuid_e1c0c3c6158f46a5bff28bf57d9","DBAppKey":"\"oidc.user:https://id.centraldispatch.com:single_spa_prod_client\"","oidc.16049d22f09f4fdb8f764b4ab0500c02":"{\"id\":\"16049d22f09f4fdb8f764b4ab0500c02\",\"created\":1743602089,\"request_type\":\"si:s\",\"code_verifier\":\"11a4e96a7c1943e293cdfab425d13645d5f68b4ec1974b049f4ecde4dea24a0cd6dec20f681147a292021bac7bee44dc\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.e98f51c534cd4bc091af6bf897693f59":"{\"id\":\"e98f51c534cd4bc091af6bf897693f59\",\"created\":1743763058,\"request_type\":\"si:s\",\"code_verifier\":\"c9e7bb1ff6c24f4abab6b745e6cdc741ccb34fcd11b349dda826d5e4b7f9966d7056fe7ba4ef4a7d875aa2a80a6a2e43\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.5f6fef2015324d55989d66ecf84dd7b7":"{\"id\":\"5f6fef2015324d55989d66ecf84dd7b7\",\"created\":1743512404,\"request_type\":\"si:s\",\"code_verifier\":\"ea81c36b4d644acdb0b0f6a558ee9431b22ed987b6bf4c89a8ab02db4210192a3ca1da11bdb0495a8024c89df25289f6\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","oidc.user:https://id.centraldispatch.com:single_spa_prod_client":"{\"id_token\":\"eyJhbGciOiJSUzI1NiIsImtpZCI6IjFFODM0OTZCMjNCQzM4MTIzREM2NEU4M0UyMTg1RjdEIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDQyMTgzMTQsImlhdCI6MTc0NDIxODMxNCwiZXhwIjoxNzQ0MjE4NjE0LCJhdWQiOiJzaW5nbGVfc3BhX3Byb2RfY2xpZW50IiwiYW1yIjpbInB3ZCJdLCJhdF9oYXNoIjoiRG9NZWN3cHRfR2owdFB3TWJtNFB1ZyIsInNpZCI6IkMzQkM4MTcyQzE1OUJDQzhBMzE4MEI5MEMzMzYwMTY5Iiwic3ViIjoidGF1dHZpc2wiLCJhdXRoX3RpbWUiOjE3NDM0MTkyNjEsImlkcCI6ImxvY2FsIn0.qp-6e5424B_LtcdiPZ-4-xKb4NJEXeWx5Y0ggsjfjIE3na11y7shbEClyxdtBWooavMzIDLoBl6eJgwCsWF-1lnP_iGrhutnMIRruU0Di4f8th-QTb9fP6z_dB2d3zFMsdYGLzqEzCaMLSbBiqzB9wP3feU0fM2jrSKUOs4Vh6SyMo-iHFFDvOd2IBDs7P2BUGieEUGKF7joZVzKnJlA5Em7-grDTt_dR2htBOFt2cPDBOroQw4BDR9I_COKDW0nxdUpGGlfVWaw4ezfKaVfxk1hCNvOoxATbfy-Jk0-eEIGyXjblZOhvVRE1vGle_vNff7GUg5bdTfRCtqggRog8w\",\"session_state\":\"_1Yb_MS56E4au7s7A1dxcNr0OHjOEH0XXvbsmuh-I_s.043EC5A6F3F4D214938F9EF8465053EA\",\"access_token\":\"eyJhbGciOiJSUzI1NiIsImtpZCI6IjFFODM0OTZCMjNCQzM4MTIzREM2NEU4M0UyMTg1RjdEIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDQyMTgzMTQsImlhdCI6MTc0NDIxODMxNCwiZXhwIjoxNzQ0MjIwMTE0LCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJ0YXV0dmlzbCIsImF1dGhfdGltZSI6MTc0MzQxOTI2MSwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6InRhdXR2aXNsIiwidGllckdyb3VwIjoiQnJva2VyIiwiY29tcGFueU5hbWUiOiJUIEF1dG8gTG9naXN0aWNzIExMQyIsImN1c3RvbWVySWQiOiIwNzI2MThkNi1kYzJlLTQ5MDYtYjVmNi01OTQxMGFhM2E1OTIiLCJhY3RpdmF0aW9uRGF0ZSI6IjIwMjAtMTEtMTkgMDY6NDE6NDYiLCJhY2NvdW50U3RhdHVzIjoiQWN0aXZlIiwiaXNBY3RpdmUiOnRydWUsInVzZXJJZCI6IjVjMjU4N2UyLTc0MTgtNDFjZS1hZjI2LWVjNGZjMzQ4ZDRlYSIsInJvbGVzIjpbIk9XTkVSIl0sIm1hcmtldFBsYWNlSWRzIjpbMTAwMDBdLCJtYXJrZXRwbGFjZXMiOlt7Ik1hcmtldHBsYWNlSWQiOjEwMDAwLCJBY3RpdmUiOnRydWUsIlJlYXNvbkNvZGUiOiJDT01QTEVURV9BQ1RJVkFURUQifV0sIm51bWJlck9mQWNjb3VudHMiOiIxIiwibG9naW5Vc2VybmFtZSI6InRhdXR2aXNsIiwiZmlyc3ROYW1lIjoiVGF1dHZ5ZGFzIiwibGFzdE5hbWUiOiJMdWthdXNrYXMiLCJlbWFpbCI6ImxvZ2lzdGljc3RhdXRvQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI1ZTZmNzY3Ny0xNjNkLTRlOTItYWUwZC1iNWJhN2VkN2UwYmMiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9LHsiUHJvZHVjdElkIjoiZWE5MDAzNWYtNTU2Ni00YmYwLTljMzgtYTIzZTBkYWY0YWYzIiwiTWFya2V0cGxhY2VJZCI6MTAwMDAsIlByb2R1Y3RTdGF0dXNLZXkiOiJhY3RpdmUifV0sIm1mYUV4cGlyYXRpb24iOiIxNzQzNDIyODYxIiwicGFydG5lcklkIjoiIiwic2lkIjoiQzNCQzgxNzJDMTU5QkNDOEEzMTgwQjkwQzMzNjAxNjkifQ.V2x3dCyOcb8Y5EjEdKSCGvZh0yVlM-qyOy4_q3GYoxgzwxm7FYVDp_zNABpZBpNtrzLxbNDokUyBF5ejDpJmOCO7Eb0WHWF0KGluAXpz096Rg7OPcfg5QJjg6DilU1PH9UzJbPpSJ_OuxceO0ugNjSi4TQeLvnLLpmeUxKFzvckg2uFu0OimWGfGzKpmkInQo98DInLFC3YruRiroE0LBP2QGCVbIQR4GgGlyCHanHkXKx_ONV5jHcpJaUY-q2TwTyKK2uJvgmD1-htOXA0Gn6ZCqMF6DcciqlAcFWxqZpCXHK8hWNzXKjIIPxhe1r64rxUjZO4ghxw66LDNqOpwHQ\",\"token_type\":\"Bearer\",\"scope\":\"openid listings_search user_management_bff\",\"profile\":{\"amr\":[\"pwd\"],\"sid\":\"C3BC8172C159BCC8A3180B90C3360169\",\"sub\":\"tautvisl\",\"auth_time\":1743419261,\"idp\":\"local\",\"username\":\"tautvisl\",\"tierGroup\":\"Broker\",\"companyName\":\"T Auto Logistics LLC\",\"customerId\":\"072618d6-dc2e-4906-b5f6-59410aa3a592\",\"activationDate\":\"2020-11-19 06:41:46\",\"accountStatus\":\"Active\",\"isActive\":true,\"userId\":\"5c2587e2-7418-41ce-af26-ec4fc348d4ea\",\"roles\":\"OWNER\",\"marketPlaceIds\":10000,\"marketplaces\":{\"MarketplaceId\":10000,\"Active\":true,\"ReasonCode\":\"COMPLETE_ACTIVATED\"},\"numberOfAccounts\":\"1\",\"loginUsername\":\"tautvisl\",\"firstName\":\"Tautvydas\",\"lastName\":\"Lukauskas\",\"email\":\"logisticstauto@gmail.com\",\"products\":[{\"ProductId\":\"5e6f7677-163d-4e92-ae0d-b5ba7ed7e0bc\",\"MarketplaceId\":10000,\"ProductStatusKey\":\"active\"},{\"ProductId\":\"ea90035f-5566-4bf0-9c38-a23e0daf4af3\",\"MarketplaceId\":10000,\"ProductStatusKey\":\"active\"}],\"mfaExpiration\":\"1743422861\",\"partnerId\":\"\"},\"expires_at\":1744220114}"}'
    listing = Listing(headless=False, local_storage=local_storage, order=order)
    listing.set_local_storage()
    listing.fill_all_fields()
    listing.get_screenshots()


    # local_storage = '''{"tcUntilDate":"null","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$tracker_optimizely":"{}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$contextual_mab":"{}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$layer_map":"{}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$variation_map":"{}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$visitor_profile":"{\"profile\":{\"visitorId\":\"oeu1743351239841r0.4479015369262427\",\"customBehavior\":{},\"first_session\":true,\"browserId\":\"gc\",\"browserVersion\":\"134.0.0.0\",\"device\":\"desktop\",\"device_type\":\"desktop_laptop\",\"referrer\":\"https://app.centraldispatch.com/\",\"source_type\":\"referral\"},\"metadata\":{\"visitorId\":{},\"events\":{},\"customBehavior\":{},\"first_session\":{},\"browserId\":{},\"browserVersion\":{},\"device\":{},\"device_type\":{},\"referrer\":{},\"source_type\":{}}}","tcCheckTime":"04/01/2025, 13:07","supportedCADYears":"{\"years\":[1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026],\"timestamp\":\"Mon Mar 31 2025\"}","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$layer_states":"[]","NavBffKey":"eyJhbGciOiJSUzI1NiIsImtpZCI6IjFFODM0OTZCMjNCQzM4MTIzREM2NEU4M0UyMTg1RjdEIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDM0MTkyNjYsImlhdCI6MTc0MzQxOTI2NiwiZXhwIjoxNzQzNDIxMDY2LCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJ0YXV0dmlzbCIsImF1dGhfdGltZSI6MTc0MzQxOTI2MSwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6InRhdXR2aXNsIiwidGllckdyb3VwIjoiQnJva2VyIiwiY29tcGFueU5hbWUiOiJUIEF1dG8gTG9naXN0aWNzIExMQyIsImN1c3RvbWVySWQiOiIwNzI2MThkNi1kYzJlLTQ5MDYtYjVmNi01OTQxMGFhM2E1OTIiLCJhY3RpdmF0aW9uRGF0ZSI6IjIwMjAtMTEtMTkgMDY6NDE6NDYiLCJhY2NvdW50U3RhdHVzIjoiQWN0aXZlIiwiaXNBY3RpdmUiOnRydWUsInVzZXJJZCI6IjVjMjU4N2UyLTc0MTgtNDFjZS1hZjI2LWVjNGZjMzQ4ZDRlYSIsInJvbGVzIjpbIk9XTkVSIl0sIm1hcmtldFBsYWNlSWRzIjpbMTAwMDBdLCJtYXJrZXRwbGFjZXMiOlt7Ik1hcmtldHBsYWNlSWQiOjEwMDAwLCJBY3RpdmUiOnRydWUsIlJlYXNvbkNvZGUiOiJDT01QTEVURV9BQ1RJVkFURUQifV0sIm51bWJlck9mQWNjb3VudHMiOiIxIiwibG9naW5Vc2VybmFtZSI6InRhdXR2aXNsIiwiZmlyc3ROYW1lIjoiVGF1dHZ5ZGFzIiwibGFzdE5hbWUiOiJMdWthdXNrYXMiLCJlbWFpbCI6ImxvZ2lzdGljc3RhdXRvQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI1ZTZmNzY3Ny0xNjNkLTRlOTItYWUwZC1iNWJhN2VkN2UwYmMiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9LHsiUHJvZHVjdElkIjoiZWE5MDAzNWYtNTU2Ni00YmYwLTljMzgtYTIzZTBkYWY0YWYzIiwiTWFya2V0cGxhY2VJZCI6MTAwMDAsIlByb2R1Y3RTdGF0dXNLZXkiOiJhY3RpdmUifV0sIm1mYUV4cGlyYXRpb24iOiIxNzQzNDIyODYxIiwicGFydG5lcklkIjoiIiwic2lkIjoiQzNCQzgxNzJDMTU5QkNDOEEzMTgwQjkwQzMzNjAxNjkifQ.WqAqI90VFZbxRmWFqo-AP1YK7N8IKxmNJLYz3PUeqAnua_FIYZVnaxJ5sdkXM2FO2usvPf3-nSgHuXtPHXC3vUH2M_OAAtitp9N_eXHsFJjVkSGddymuHIwln6PoYLGUkgAYlgJhbBetpCrQMQoZ5XegQC87e8rl3HftGAlVqIzkqasKdIyRjQ2P_vq9jWXHqr6D5tDjo-ToU0_17FOLjPq5PSnqvHYZmecdyPG9ikqwCOZv8exla0BL8r1IM7MtXmAhKFCCfGIy_MSYHYGFaqmVn09WNFfYiIPPE63-YUnEWZsN9sPnJcjciPWANJZos47woiUsmg-VeHCh3Pmikw","showTCBanner":"false","optimizely_data$$pending_events":"{\"c5d47d0c-b0e7-4509-99aa-6bcfb3963223\":{\"id\":\"c5d47d0c-b0e7-4509-99aa-6bcfb3963223\",\"timeStamp\":1743419262980,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.221.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"394\",\"visitors\":[{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"direct\"}],\"snapshots\":[{\"activationTimestamp\":1743351261051,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"167d87c8-bc18-41f3-ae55-44e019dc9a49\",\"t\":1743351261053}]}]}]}},\"retryCount\":2},\"f40caf6c-3afe-49c8-a1de-21b3a4ceb18c\":{\"id\":\"f40caf6c-3afe-49c8-a1de-21b3a4ceb18c\",\"timeStamp\":1743419263998,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.221.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"394\",\"visitors\":[{\"visitor_id\":\"oeu1743351239841r0.4479015369262427\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://app.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1743419262983,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"b2e1c927-c26e-4b0d-a183-d99a03540d57\",\"t\":1743419262995}]}]}]}},\"retryCount\":1}}","optimizely-vuid":"vuid_e1c0c3c6158f46a5bff28bf57d9","optimizely_data$$oeu1743351239841r0.4479015369262427$$22031524578$$session_state":"{\"lastSessionTimestamp\":1743419262987,\"sessionId\":\"7f482aee-23e5-4c07-99a7-558f91bdc3ee\"}","oidc.user:https://id.centraldispatch.com:single_spa_prod_client":"{\"id_token\":\"eyJhbGciOiJSUzI1NiIsImtpZCI6IjFFODM0OTZCMjNCQzM4MTIzREM2NEU4M0UyMTg1RjdEIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDM0MTkyNjYsImlhdCI6MTc0MzQxOTI2NiwiZXhwIjoxNzQzNDE5NTY2LCJhdWQiOiJzaW5nbGVfc3BhX3Byb2RfY2xpZW50IiwiYW1yIjpbInB3ZCJdLCJhdF9oYXNoIjoiZ3NIdTBRSWZqN3Z1ZFV1c1pxVndfUSIsInNpZCI6IkMzQkM4MTcyQzE1OUJDQzhBMzE4MEI5MEMzMzYwMTY5Iiwic3ViIjoidGF1dHZpc2wiLCJhdXRoX3RpbWUiOjE3NDM0MTkyNjEsImlkcCI6ImxvY2FsIn0.eV3ro5tpOF6X6p8fzMfZ49j6j0MOx8bXOm2cQgGeDeIt4RjUzsXomnCt8qVlM9QIal9ptukRcs5-4VgsKkTJX38gw5cIRaeTM5gv6r_kRvXM_PtxZTgGJNiJnWw8AdVYmCZ5OUaoWyroR3gkc-toHQMPKSydmmrYptVXG4lFodyhC6P1bRBIKi83P2Q9mvrEbUr_rkishtiy5kHBXKnPA-5x_0EWty_2Qn0Yzh2diXeDhqNV2rvTsP1yO_lZWNDMeabEklvzQdngtgesBj76bmHNx_RPt277BmPRf1kR5xoDfBoKegjjwH2TB6F3j_TP7-FkmTEQdoY5mBiUXVYA5Q\",\"session_state\":\"KGU4VGyVf08IP137lLXUZRJoxvJLUDr4Uv8nOSBiHBM.3B5446F587E62F53CCDBEABAC6E07C98\",\"access_token\":\"eyJhbGciOiJSUzI1NiIsImtpZCI6IjFFODM0OTZCMjNCQzM4MTIzREM2NEU4M0UyMTg1RjdEIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDM0MTkyNjYsImlhdCI6MTc0MzQxOTI2NiwiZXhwIjoxNzQzNDIxMDY2LCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJ0YXV0dmlzbCIsImF1dGhfdGltZSI6MTc0MzQxOTI2MSwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6InRhdXR2aXNsIiwidGllckdyb3VwIjoiQnJva2VyIiwiY29tcGFueU5hbWUiOiJUIEF1dG8gTG9naXN0aWNzIExMQyIsImN1c3RvbWVySWQiOiIwNzI2MThkNi1kYzJlLTQ5MDYtYjVmNi01OTQxMGFhM2E1OTIiLCJhY3RpdmF0aW9uRGF0ZSI6IjIwMjAtMTEtMTkgMDY6NDE6NDYiLCJhY2NvdW50U3RhdHVzIjoiQWN0aXZlIiwiaXNBY3RpdmUiOnRydWUsInVzZXJJZCI6IjVjMjU4N2UyLTc0MTgtNDFjZS1hZjI2LWVjNGZjMzQ4ZDRlYSIsInJvbGVzIjpbIk9XTkVSIl0sIm1hcmtldFBsYWNlSWRzIjpbMTAwMDBdLCJtYXJrZXRwbGFjZXMiOlt7Ik1hcmtldHBsYWNlSWQiOjEwMDAwLCJBY3RpdmUiOnRydWUsIlJlYXNvbkNvZGUiOiJDT01QTEVURV9BQ1RJVkFURUQifV0sIm51bWJlck9mQWNjb3VudHMiOiIxIiwibG9naW5Vc2VybmFtZSI6InRhdXR2aXNsIiwiZmlyc3ROYW1lIjoiVGF1dHZ5ZGFzIiwibGFzdE5hbWUiOiJMdWthdXNrYXMiLCJlbWFpbCI6ImxvZ2lzdGljc3RhdXRvQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI1ZTZmNzY3Ny0xNjNkLTRlOTItYWUwZC1iNWJhN2VkN2UwYmMiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9LHsiUHJvZHVjdElkIjoiZWE5MDAzNWYtNTU2Ni00YmYwLTljMzgtYTIzZTBkYWY0YWYzIiwiTWFya2V0cGxhY2VJZCI6MTAwMDAsIlByb2R1Y3RTdGF0dXNLZXkiOiJhY3RpdmUifV0sIm1mYUV4cGlyYXRpb24iOiIxNzQzNDIyODYxIiwicGFydG5lcklkIjoiIiwic2lkIjoiQzNCQzgxNzJDMTU5QkNDOEEzMTgwQjkwQzMzNjAxNjkifQ.WqAqI90VFZbxRmWFqo-AP1YK7N8IKxmNJLYz3PUeqAnua_FIYZVnaxJ5sdkXM2FO2usvPf3-nSgHuXtPHXC3vUH2M_OAAtitp9N_eXHsFJjVkSGddymuHIwln6PoYLGUkgAYlgJhbBetpCrQMQoZ5XegQC87e8rl3HftGAlVqIzkqasKdIyRjQ2P_vq9jWXHqr6D5tDjo-ToU0_17FOLjPq5PSnqvHYZmecdyPG9ikqwCOZv8exla0BL8r1IM7MtXmAhKFCCfGIy_MSYHYGFaqmVn09WNFfYiIPPE63-YUnEWZsN9sPnJcjciPWANJZos47woiUsmg-VeHCh3Pmikw\",\"token_type\":\"Bearer\",\"scope\":\"openid listings_search user_management_bff\",\"profile\":{\"amr\":[\"pwd\"],\"sid\":\"C3BC8172C159BCC8A3180B90C3360169\",\"sub\":\"tautvisl\",\"auth_time\":1743419261,\"idp\":\"local\",\"username\":\"tautvisl\",\"tierGroup\":\"Broker\",\"companyName\":\"T Auto Logistics LLC\",\"customerId\":\"072618d6-dc2e-4906-b5f6-59410aa3a592\",\"activationDate\":\"2020-11-19 06:41:46\",\"accountStatus\":\"Active\",\"isActive\":true,\"userId\":\"5c2587e2-7418-41ce-af26-ec4fc348d4ea\",\"roles\":\"OWNER\",\"marketPlaceIds\":10000,\"marketplaces\":{\"MarketplaceId\":10000,\"Active\":true,\"ReasonCode\":\"COMPLETE_ACTIVATED\"},\"numberOfAccounts\":\"1\",\"loginUsername\":\"tautvisl\",\"firstName\":\"Tautvydas\",\"lastName\":\"Lukauskas\",\"email\":\"logisticstauto@gmail.com\",\"products\":[{\"ProductId\":\"5e6f7677-163d-4e92-ae0d-b5ba7ed7e0bc\",\"MarketplaceId\":10000,\"ProductStatusKey\":\"active\"},{\"ProductId\":\"ea90035f-5566-4bf0-9c38-a23e0daf4af3\",\"MarketplaceId\":10000,\"ProductStatusKey\":\"active\"}],\"mfaExpiration\":\"1743422861\",\"partnerId\":\"\"},\"expires_at\":1743421066}"}'''
    #
    # proccessed_local_storage = process_json(local_storage)
    # print(proccessed_local_storage)


