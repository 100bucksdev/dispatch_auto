import json
import re
from datetime import timedelta, datetime
from urllib.parse import quote

import requests
from exeption import CustomBadRequestWithDetail


def parse_json_values(data):
    for key, value in data.items():
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                data[key] = parsed_value
            except json.JSONDecodeError:
                pass
    return data

class RequestsListing:
    def __init__(self, order: dict, offsite_location:str | None, local_storage: str, mode: str = 'preview'):
        self.order = order
        self.offsite_location = offsite_location
        self.local_storage = parse_json_values(json.loads(local_storage))
        self.headers = {
            'Authorization': f"Bearer {self.local_storage['oidc.user:https://id.centraldispatch.com:single_spa_prod_client']['access_token']}"
        }

        self.pickup_location = None
        self.delivery_location = None
        self.VIN_info = None
        self.price = None
        if mode in ['preview', 'post']:
            self.get_pickup_location()
            self.get_delivery_location()
            if None in [self.pickup_location, self.delivery_location]:
                raise CustomBadRequestWithDetail("update_local_storage")
        if mode == 'post':
            self.get_VIN_info()
            self.get_price()
            if None in [self.VIN_info, self.price]:
                raise CustomBadRequestWithDetail("update_local_storage")


    def get_location(self, get_offsite=True):
        if get_offsite:
            location = self.offsite_location
        else:
            location = self.order.get('auction_city', {}).get('location')
        if location:
            while '(' in location and ')' in location:
                start = location.index('(')
                end = location.index(')') + 1
                location = location[:start] + location[end:]
        return location

    def get_auction(self):
        auctions = ['IAAI', 'COPART']
        auction = self.order.get('auction_name')
        if auction.upper() not in auctions:
            raise CustomBadRequestWithDetail(f"Invalid auction: {auction}")
        return auction

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

    def get_vin(self):
        vin = self.order.get('vin')
        if not vin:
            raise CustomBadRequestWithDetail("invalid_vin_in_order")
        return vin

    def get_lot_id(self):
        lot_id = str(self.order.get('lot_id')) if self.order.get('lot_id') else None
        if not lot_id:
            raise CustomBadRequestWithDetail("invalid_lot_id_in_order")
        return lot_id

    def get_pickup_location(self):
        max_attempts = 3
        attempt = 0
        base_url = "https://bff.centraldispatch.com/listing-editor/customers/search-contact"

        # Get auction and location details
        auction = self.get_auction().upper()
        location = self.get_location(False).upper()
        offsite_location = self.get_location()  # Might be None

        # List to hold all search strings
        all_strings = []

        # If offsite_location exists, generate its variations first
        if offsite_location is not None:
            offsite_location = offsite_location.upper()
            offsite_clean = re.sub(r'\d+', '', offsite_location.replace('-', ' '))
            offsite_strings = [
                offsite_location,
                offsite_location.replace('-', ' '),
                offsite_clean,
                offsite_clean.replace('-', ' ')
            ]
            all_strings.extend(offsite_strings)

        # Generate variations for regular location combined with auction
        location_clean = re.sub(r'\d+', '', location.replace('-', ' '))
        location_strings = [
            f"{auction} {location}",
            f"{auction} {location.replace('-', ' ')}",
            f"{auction} {location_clean}",
            f"{auction} {location_clean.replace('-', ' ')}"
        ]
        all_strings.extend(location_strings)

        while attempt < max_attempts:
            print(f"Attempt {attempt + 1}/{max_attempts}")
            try:
                success = False
                for full_string in all_strings:
                    # Split the string into auction and location parts
                    current_location = full_string[len(auction) + 1:]  # Skip auction and space
                    print(f"Trying string: {full_string}")

                    # Now process location character by character
                    current_input = auction + " "
                    for char in current_location:
                        current_input += char
                        encoded_string = quote(current_input)
                        url = f"{base_url}?keyword={encoded_string}"


                        response = requests.get(url, headers=self.headers)


                        if response.status_code == 401:
                            print("Unauthorized access (401) - setting pickup_location to None")
                            self.pickup_location = None
                            return

                        data = response.json()

                        if not data or len(data) == 0:
                            print("No data returned, moving to next string")
                            break

                        for item in data:
                            item_name = item.get('companyName', '').upper()


                            if item_name == full_string:
                                print(f"Exact match found for {full_string}")
                                success = True
                                self.pickup_location = item
                                break
                            elif len(data) == 1 or current_input == full_string:
                                print(f"Single result match found for {full_string}")
                                success = True
                                self.pickup_location = item
                                break

                        if success:
                            print("Successful match found, returning")
                            return
                    if success:
                        print("Breaking inner loop due to success")
                        break
                attempt += 1
            except requests.RequestException as e:
                print(f"RequestException occurred: {str(e)}")
                attempt += 1
            except Exception as e:
                print(f"Unexpected error occurred: {str(e)}")
                attempt += 1

        print("Max attempts reached, raising CustomBadRequestWithDetail")
        raise CustomBadRequestWithDetail('maximal_attempts_reached_while_finding_pickup_location')

    def get_delivery_location(self):
        base_url = "https://bff.centraldispatch.com/listing-editor/customers/search-contact"
        location = self.get_processed_terminal()
        url = f"{base_url}?keyword={location}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 401:
            self.delivery_location = None
            return
        self.delivery_location = response.json()[0]

    def get_VIN_info(self):
        url = f'https://bff.centraldispatch.com/listing-editor/listing-Vehicles/get-vehicle-by-vin/{self.get_vin()}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 401:
            self.VIN_info = None
            return
        self.VIN_info = response.json()

    def get_price(self):
        listing_prices_url = 'https://prod-price-check-app-bff.awsmanlog2.manheim.com/listing-prices'
        data = {
            'stops':[
                {
                    'city':self.pickup_location.get('city'),
                    'country':'US',
                    'latitude': None,
                    'locationName': self.pickup_location.get('companyName'),
                    'locationType': 'Auction',
                    'longitude': None,
                    'postalCode': self.pickup_location.get('zipCode'),
                    'state': self.pickup_location.get('state'),
                    'stopId': '',
                    'stopNumber': 1,
                    'streetAddress1': self.pickup_location.get('address1'),
                    'streetAddress2': self.pickup_location.get('address2')
                },

                {
                    'city': self.delivery_location.get('city'),
                    'country': 'US',
                    'latitude': None,
                    'locationName': self.delivery_location.get('companyName'),
                    'locationType': 'Unspecified',
                    'longitude': None,
                    'postalCode': self.delivery_location.get('zipCode'),
                    'state': self.delivery_location.get('state'),
                    'stopId': '',
                    'stopNumber': 2,
                    'streetAddress1': self.delivery_location.get('address1'),
                    'streetAddress2': self.delivery_location.get('address2')
                }
            ],
            'trailerType': 'OPEN',
            'vehicles':[
                {
                   'dropOffStopNumber': 2,
                    'isOperable': True,
                    'make': self.VIN_info.get('make'),
                    'model': self.VIN_info.get('model'),
                    'pickUpStopNumber': 1,
                    'vehicleType': self.VIN_info.get('vehicleType'),
                    'vin': self.get_vin(),
                    'year': self.VIN_info.get('year'),
                }
            ]
        }

        response = requests.post(listing_prices_url, headers=self.headers, json=data)
        if response.status_code == 401:
            self.price = None
            return
        items = response.json().get('items', [])
        lowest_price = min((item['listingPrice'] for item in items if item.get('listingPrice') is not None), default=None)
        self.price = lowest_price


    def post_listing(self):
        url = 'https://bff.centraldispatch.com/listing-editor/listings'
        current_date = datetime.now()
        future_date = current_date + timedelta(days=3)
        expiration_date = current_date + timedelta(days=30)
        data = {
            'additionalInfo': 'Forklift on/off **Pick Up TITLE!** Zelle/wire payment',
            'availableDate': current_date.strftime("%m/%d/%Y"),
            'desiredDeliveryDate': future_date.strftime("%m/%d/%Y"),
            'expirationDate': expiration_date.strftime("%m/%d/%Y"),
            'externalId': '',
            'hasInOpVehicle': False,
            'listingId': None,
            'partnerReferenceId': '',
            'price': {
                'balance': {
                    'amount': '0.00',
                    'balancePaymentMethod': None,
                    'balancePaymentTermsBeginOn': None,
                    'paymentTime': None
                },
                'cod': {
                    'amount': int(self.price),
                    'paymentLocation': 'DELIVERY',
                    'paymentMethod': 'CASH_CERTIFIED_FUNDS'
                },
                'total': int(self.price)
            },
            'shipperId': self.pickup_location.get('customerId'),
            'shipperOrderId': self.get_vin()[-6:],
            'sla': None,
            'stops': [
                {
                    'address': self.pickup_location.get('address1'),
                    'address2': self.pickup_location.get('address2'),
                    'cell': '',
                    'city': self.pickup_location.get('city'),
                    'contactName': self.pickup_location.get('contact'),
                    'contactPhone': self.pickup_location.get('contactPhone').replace(' ', '').replace('-', ''),
                    'country': 'US',
                    'geoCode':{
                        'latitude': None,
                        'longitude': None
                    },
                    'locationName': self.pickup_location.get('companyName'),
                    'locationType': 'Auction',
                    'metroArea': None,
                    'phone2': '',
                    'phone3': '',
                    'postalCode': self.pickup_location.get('zipCode'),
                    'siteId': '',
                    'state': self.pickup_location.get('state'),
                    'stopId': '',
                    'stopNumber': 1,
                    'twic': False
                },
                {
                    'address': self.delivery_location.get('address1'),
                    'address2': self.delivery_location.get('address2'),
                    'cell': '',
                    'city': self.delivery_location.get('city'),
                    'contactName': self.delivery_location.get('contact'),
                    'contactPhone': self.delivery_location.get('contactPhone').replace(' ', '').replace('-', ''),
                    'country': 'US',
                    'geoCode': {
                        'latitude': None,
                        'longitude': None
                    },
                    'locationName': self.delivery_location.get('companyName'),
                    'locationType': 'Unspecified',
                    'metroArea': None,
                    'phone2': '',
                    'phone3': '',
                    'postalCode': self.delivery_location.get('zipCode'),
                    'siteId': '',
                    'state': self.delivery_location.get('state'),
                    'stopId': '',
                    'stopNumber': 2,
                    'twic': False
                }
            ],
            'tags': [],
            'totalDistanceInMiles': 0,
            'trailerType': 'OPEN',
            'vehicles': [
                {
                    'additionalInfo': 'Please pick up the TITLE and Keys !Please take some PHOTOS around the car AT PICK UP and DROP OFF  send it to 954-703-4009 or  logisticsTauto@gmail.com !\nI’m paying on delivery by ZELLE',
                    'checkedVinAvailable': True,
                    'color': '',
                    'dropoffStopNumber': 2,
                    'isExpanded': True,
                    'isInoperable': False,
                    'isUsingComboBox': True,
                    'licensePlate': '',
                    'licensePlateState': '',
                    'lotNumber': self.get_lot_id(),
                    'make': self.VIN_info.get('make'),
                    'mapId': '609809415',
                    'model': self.VIN_info.get('model'),
                    'order': 0,
                    'pickupStopNumber': 1,
                    'qty': 1,
                    'quotaId': None,
                    'shippingSpecs': self.VIN_info.get('shippingSpecs'),
                    'tariff': 0,
                    'trim': '',
                    'vehicleAttributes': [],
                    'vehicleType': self.VIN_info.get('vehicleType'),
                    'vehicleTypeOther': '',
                    'vin': self.get_vin(),
                    'vinIsRequired': False,
                    'wideLoad': False,
                    'year': self.VIN_info.get('year'),

                }
            ]

        }

        response = requests.post(url, headers=self.headers, json=data)
        print('Response status code:', response.status_code)
        if response.status_code == 401:
            raise CustomBadRequestWithDetail("update_local_storage")












if __name__ == "__main__":
    local_storage = r"""{"tcUntilDate":"null","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$variation_map":"{}","supportedCADYears":"{\"data\":[1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026],\"timestamp\":1745579562354}","tcCheckTime":"04/26/2025, 13:12","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$layer_map":"{}","oidc.2af7e85e0fed42c58a5e15a109898355":"{\"id\":\"2af7e85e0fed42c58a5e15a109898355\",\"created\":1745334154,\"request_type\":\"si:s\",\"code_verifier\":\"0c95e4f97b78445aaae38881675cbaa91509b5ef976f4b029104ddb50c6f35b8c346179ca373409581cf49a87a0bdeea\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$tracker_optimizely":"{}","isLeaving":"true","supportedCADModels_2019_Volkswagen":"{\"data\":[\"Arteon\",\"Atlas\",\"Beetle\",\"Beetle Convertible\",\"e-Golf\",\"Golf\",\"Golf Alltrack\",\"Golf GTI\",\"Golf R\",\"Golf SportWagen\",\"Jetta\",\"Passat\",\"Tiguan\"],\"timestamp\":1745502828620}","NavBffKey":"eyJhbGciOiJSUzI1NiIsImtpZCI6IjQ2M0VCNThGOEJBQ0Q5RThFQTVGNDBFRUNFMkZGNzkxIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDU1ODA3MTEsImlhdCI6MTc0NTU4MDcxMSwiZXhwIjoxNzQ1NTgyNTExLCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJ0YXV0dmlzbCIsImF1dGhfdGltZSI6MTc0NDc5NzYwMiwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6InRhdXR2aXNsIiwidGllckdyb3VwIjoiQnJva2VyIiwiY29tcGFueU5hbWUiOiJUIEF1dG8gTG9naXN0aWNzIExMQyIsImN1c3RvbWVySWQiOiIwNzI2MThkNi1kYzJlLTQ5MDYtYjVmNi01OTQxMGFhM2E1OTIiLCJhY3RpdmF0aW9uRGF0ZSI6IjIwMjAtMTEtMTkgMDY6NDE6NDYiLCJhY2NvdW50U3RhdHVzIjoiQWN0aXZlIiwiaXNBY3RpdmUiOnRydWUsInVzZXJJZCI6IjVjMjU4N2UyLTc0MTgtNDFjZS1hZjI2LWVjNGZjMzQ4ZDRlYSIsInJvbGVzIjpbIk9XTkVSIl0sIm1hcmtldFBsYWNlSWRzIjpbMTAwMDBdLCJtYXJrZXRwbGFjZXMiOlt7Ik1hcmtldHBsYWNlSWQiOjEwMDAwLCJBY3RpdmUiOnRydWUsIlJlYXNvbkNvZGUiOiJDT01QTEVURV9BQ1RJVkFURUQifV0sIm51bWJlck9mQWNjb3VudHMiOiIxIiwibG9naW5Vc2VybmFtZSI6InRhdXR2aXNsIiwiZmlyc3ROYW1lIjoiVGF1dHZ5ZGFzIiwibGFzdE5hbWUiOiJMdWthdXNrYXMiLCJlbWFpbCI6ImxvZ2lzdGljc3RhdXRvQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI1ZTZmNzY3Ny0xNjNkLTRlOTItYWUwZC1iNWJhN2VkN2UwYmMiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9LHsiUHJvZHVjdElkIjoiZWE5MDAzNWYtNTU2Ni00YmYwLTljMzgtYTIzZTBkYWY0YWYzIiwiTWFya2V0cGxhY2VJZCI6MTAwMDAsIlByb2R1Y3RTdGF0dXNLZXkiOiJhY3RpdmUifV0sIm1mYUV4cGlyYXRpb24iOiIxNzQ0ODAxMjAyIiwicGFydG5lcklkIjoiIiwic2lkIjoiQUJGOUQ5RkQ0NUI3RkFFRTNBMDIwNDhFMjc3MEYzM0QifQ.VEaRjt3fwOgtvIi18lsNRp7uHg23IljpZ059AVyDzG9WzSpSuabl9kf2PlWlo9kNlHmiXIZ1kvHOFEdkSsJbW9kcjE7Lp8jQGhZYsh-XaVxvB8sRuBpwJyfDDBIwmcHJ-FwPRgYynjtPmizNrtujnPVZjEk_Z37IVIfOe7pwVmAmrYi2d-lzfnXXZ5GRroOH2PEf2jX8cmHLHeAT4ZvZYXfVQ5N7j4ye0V3ycnR0wEVVRKLyClMXnRHM6eartLuFHJtXzxqF04yO0FGd-WVzS0Tzi3E4iCFlswBj7DVqH66ApnL8JiD8j6B1NUmac4an0xS6aNTzwJFxXqAG85ADQw","supportedCADMakes_2019":"{\"data\":[\"Acura\",\"Alfa Romeo\",\"Aston Martin\",\"Audi\",\"Bentley\",\"BMW\",\"Bugatti\",\"Buick\",\"Cadillac\",\"Chevrolet\",\"Chrysler\",\"Dodge\",\"Ferrari\",\"FIAT\",\"Ford\",\"Freightliner\",\"Genesis\",\"GMC\",\"Honda\",\"Hyundai\",\"INFINITI\",\"Jaguar\",\"Jeep\",\"Karma\",\"Kia\",\"Lamborghini\",\"Land Rover\",\"Lexus\",\"Lincoln\",\"Maserati\",\"MAZDA\",\"McLaren\",\"Mercedes-Benz\",\"MINI\",\"Mitsubishi\",\"Nissan\",\"Porsche\",\"Ram\",\"Rolls-Royce\",\"smart\",\"Subaru\",\"Tesla\",\"Toyota\",\"Volkswagen\",\"Volvo\"],\"timestamp\":1745502829024}","showTCBanner":"false","optimizely-vuid":"vuid_3efbc577bc7c472b92afce9d8be","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$session_state":"{\"lastSessionTimestamp\":1745581267508,\"sessionId\":\"3ecff3d7-749e-4eb6-b7e0-eba09a5ec5d2\"}","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$layer_states":"[]","optimizely_data$$pending_events":"{\"51f47d33-2849-46e5-a290-eb09488c925a\":{\"id\":\"51f47d33-2849-46e5-a290-eb09488c925a\",\"timeStamp\":1745581267506,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.223.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"575\",\"visitors\":[{\"visitor_id\":\"oeu1744797605083r0.16842611819067865\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://id.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1745580961514,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"d5155897-8ace-4b17-8e89-c0183c22f388\",\"t\":1745580709589}]}]},{\"visitor_id\":\"oeu1744797605083r0.16842611819067865\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://id.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1745580961514,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"ebea16dc-5481-41e2-9b8b-95bf3b668128\",\"t\":1745580961519}]}]}]}},\"retryCount\":2},\"20105589-3161-4435-9c2d-456acb43ea72\":{\"id\":\"20105589-3161-4435-9c2d-456acb43ea72\",\"timeStamp\":1745581268554,\"data\":{\"url\":\"https://logx.optimizely.com/v1/events\",\"method\":\"POST\",\"data\":{\"account_id\":\"10829270344\",\"anonymize_ip\":true,\"client_name\":\"js\",\"client_version\":\"0.223.0\",\"enrich_decisions\":true,\"project_id\":\"22031524578\",\"revision\":\"575\",\"visitors\":[{\"visitor_id\":\"oeu1744797605083r0.16842611819067865\",\"session_id\":\"AUTO\",\"attributes\":[{\"e\":null,\"k\":\"\",\"t\":\"first_session\",\"v\":true},{\"e\":null,\"k\":\"\",\"t\":\"browserId\",\"v\":\"gc\"},{\"e\":null,\"k\":\"\",\"t\":\"device\",\"v\":\"desktop\"},{\"e\":null,\"k\":\"\",\"t\":\"device_type\",\"v\":\"desktop_laptop\"},{\"e\":null,\"k\":\"\",\"t\":\"referrer\",\"v\":\"https://id.centraldispatch.com/\"},{\"e\":null,\"k\":\"\",\"t\":\"source_type\",\"v\":\"referral\"}],\"snapshots\":[{\"activationTimestamp\":1745581267506,\"decisions\":[],\"events\":[{\"e\":null,\"y\":\"client_activation\",\"u\":\"91a30a0a-11db-42c0-91ca-9e63223b5945\",\"t\":1745581267512}]}]}]}},\"retryCount\":1}}","oidc.14c03c0c1dbd42d5a39eac680351eb85":"{\"id\":\"14c03c0c1dbd42d5a39eac680351eb85\",\"created\":1744798522,\"request_type\":\"si:s\",\"code_verifier\":\"4af6a66a7edf467398fc2e676f75a808926c30faa8c44be19c706b2772838a8722b02b334c034be1ace031af732967a5\",\"redirect_uri\":\"https://app.centraldispatch.com/oidc-renew\",\"authority\":\"https://id.centraldispatch.com\",\"client_id\":\"single_spa_prod_client\",\"response_mode\":\"query\",\"scope\":\"openid listings_search user_management_bff\",\"extraTokenParams\":{}}","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$contextual_mab":"{}","optimizely_data$$oeu1744797605083r0.16842611819067865$$22031524578$$visitor_profile":"{\"profile\":{\"visitorId\":\"oeu1744797605083r0.16842611819067865\",\"customBehavior\":{},\"first_session\":true,\"browserId\":\"gc\",\"browserVersion\":\"135.0.0.0\",\"device\":\"desktop\",\"device_type\":\"desktop_laptop\",\"referrer\":\"https://id.centraldispatch.com/\",\"source_type\":\"referral\"},\"metadata\":{\"visitorId\":{},\"events\":{},\"customBehavior\":{},\"first_session\":{},\"browserId\":{},\"browserVersion\":{},\"device\":{},\"device_type\":{},\"referrer\":{},\"source_type\":{}}}","DBAppKey":"\"oidc.user:https://id.centraldispatch.com:single_spa_prod_client\"","DBLayout":"{\"lg\":[{\"i\":\"quickLinks\",\"x\":0,\"y\":0,\"w\":6,\"h\":192,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"savedSearch\",\"x\":0,\"y\":384,\"w\":6,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"offers\",\"x\":3,\"y\":192,\"w\":3,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"totalTransports\",\"x\":0,\"y\":654,\"w\":6,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"readyDispatch\",\"x\":6,\"y\":0,\"w\":6,\"h\":652,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"ratings\",\"x\":0,\"y\":192,\"w\":3,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false}],\"md\":[{\"i\":\"quickLinks\",\"x\":0,\"y\":0,\"w\":12,\"h\":184,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"savedSearch\",\"x\":0,\"y\":575,\"w\":12,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"offers\",\"x\":0,\"y\":384,\"w\":12,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"totalTransports\",\"x\":0,\"y\":844,\"w\":12,\"h\":269,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"readyDispatch\",\"x\":0,\"y\":1113,\"w\":12,\"h\":651,\"static\":false,\"isDraggable\":false,\"isResizable\":false},{\"i\":\"ratings\",\"x\":0,\"y\":185,\"w\":12,\"h\":191,\"static\":false,\"isDraggable\":false,\"isResizable\":false}]}","oidc.user:https://id.centraldispatch.com:single_spa_prod_client":"{\"id_token\":\"eyJhbGciOiJSUzI1NiIsImtpZCI6IjQ2M0VCNThGOEJBQ0Q5RThFQTVGNDBFRUNFMkZGNzkxIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDU1ODA3MTEsImlhdCI6MTc0NTU4MDcxMSwiZXhwIjoxNzQ1NTgxMDExLCJhdWQiOiJzaW5nbGVfc3BhX3Byb2RfY2xpZW50IiwiYW1yIjpbInB3ZCJdLCJhdF9oYXNoIjoiVHhUdm1Obm93WGVlMUZUWDNkOFVLZyIsInNpZCI6IkFCRjlEOUZENDVCN0ZBRUUzQTAyMDQ4RTI3NzBGMzNEIiwic3ViIjoidGF1dHZpc2wiLCJhdXRoX3RpbWUiOjE3NDQ3OTc2MDIsImlkcCI6ImxvY2FsIn0.TdOOgikR4njX11kZVJ9hcO0Kv_JNM19loia4WMTWjnymfgNOc_l5xPs59IOvq0K8ymcRO7y-9vPJ_Dru8bCQ0hJA99S3czokPH3dWquomk8WQD9znmwTABL7XGcKKGAGavix9kIKP_gC8zFEGX8ejrWIf-FfN0VxKK_pLgU9WDNtNeMDSvKavm3QoFBAGwSByIpJEkM2tDU7VGsCBC4_bEeytqWmfZcJQOzpUF1SPBM-CpGYtqntQxJ_p7eAs9RHK8ZhC-ZMuPpIv2-PY5cdHOVzyYyAF4FBKKta2iA55ZIv_lsADrTKqXtx-YpGCKId_ywxC7xlbVb0lG0GeZciVg\",\"session_state\":\"TML3uoi2p1PAafLGw7pfgfAXroe6ykOEl5ZtMw7xSiM.C0AC2F57FAAFCA75CFB7FCD0C284C345\",\"access_token\":\"eyJhbGciOiJSUzI1NiIsImtpZCI6IjQ2M0VCNThGOEJBQ0Q5RThFQTVGNDBFRUNFMkZGNzkxIiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2lkLmNlbnRyYWxkaXNwYXRjaC5jb20iLCJuYmYiOjE3NDU1ODA3MTEsImlhdCI6MTc0NTU4MDcxMSwiZXhwIjoxNzQ1NTgyNTExLCJhdWQiOlsibGlzdGluZ3Mtc2VhcmNoLWFwaSIsInVzZXJfbWFuYWdlbWVudF9iZmYiXSwic2NvcGUiOlsib3BlbmlkIiwibGlzdGluZ3Nfc2VhcmNoIiwidXNlcl9tYW5hZ2VtZW50X2JmZiJdLCJhbXIiOlsicHdkIl0sImNsaWVudF9pZCI6InNpbmdsZV9zcGFfcHJvZF9jbGllbnQiLCJzdWIiOiJ0YXV0dmlzbCIsImF1dGhfdGltZSI6MTc0NDc5NzYwMiwiaWRwIjoibG9jYWwiLCJ1c2VybmFtZSI6InRhdXR2aXNsIiwidGllckdyb3VwIjoiQnJva2VyIiwiY29tcGFueU5hbWUiOiJUIEF1dG8gTG9naXN0aWNzIExMQyIsImN1c3RvbWVySWQiOiIwNzI2MThkNi1kYzJlLTQ5MDYtYjVmNi01OTQxMGFhM2E1OTIiLCJhY3RpdmF0aW9uRGF0ZSI6IjIwMjAtMTEtMTkgMDY6NDE6NDYiLCJhY2NvdW50U3RhdHVzIjoiQWN0aXZlIiwiaXNBY3RpdmUiOnRydWUsInVzZXJJZCI6IjVjMjU4N2UyLTc0MTgtNDFjZS1hZjI2LWVjNGZjMzQ4ZDRlYSIsInJvbGVzIjpbIk9XTkVSIl0sIm1hcmtldFBsYWNlSWRzIjpbMTAwMDBdLCJtYXJrZXRwbGFjZXMiOlt7Ik1hcmtldHBsYWNlSWQiOjEwMDAwLCJBY3RpdmUiOnRydWUsIlJlYXNvbkNvZGUiOiJDT01QTEVURV9BQ1RJVkFURUQifV0sIm51bWJlck9mQWNjb3VudHMiOiIxIiwibG9naW5Vc2VybmFtZSI6InRhdXR2aXNsIiwiZmlyc3ROYW1lIjoiVGF1dHZ5ZGFzIiwibGFzdE5hbWUiOiJMdWthdXNrYXMiLCJlbWFpbCI6ImxvZ2lzdGljc3RhdXRvQGdtYWlsLmNvbSIsInByb2R1Y3RzIjpbeyJQcm9kdWN0SWQiOiI1ZTZmNzY3Ny0xNjNkLTRlOTItYWUwZC1iNWJhN2VkN2UwYmMiLCJNYXJrZXRwbGFjZUlkIjoxMDAwMCwiUHJvZHVjdFN0YXR1c0tleSI6ImFjdGl2ZSJ9LHsiUHJvZHVjdElkIjoiZWE5MDAzNWYtNTU2Ni00YmYwLTljMzgtYTIzZTBkYWY0YWYzIiwiTWFya2V0cGxhY2VJZCI6MTAwMDAsIlByb2R1Y3RTdGF0dXNLZXkiOiJhY3RpdmUifV0sIm1mYUV4cGlyYXRpb24iOiIxNzQ0ODAxMjAyIiwicGFydG5lcklkIjoiIiwic2lkIjoiQUJGOUQ5RkQ0NUI3RkFFRTNBMDIwNDhFMjc3MEYzM0QifQ.VEaRjt3fwOgtvIi18lsNRp7uHg23IljpZ059AVyDzG9WzSpSuabl9kf2PlWlo9kNlHmiXIZ1kvHOFEdkSsJbW9kcjE7Lp8jQGhZYsh-XaVxvB8sRuBpwJyfDDBIwmcHJ-FwPRgYynjtPmizNrtujnPVZjEk_Z37IVIfOe7pwVmAmrYi2d-lzfnXXZ5GRroOH2PEf2jX8cmHLHeAT4ZvZYXfVQ5N7j4ye0V3ycnR0wEVVRKLyClMXnRHM6eartLuFHJtXzxqF04yO0FGd-WVzS0Tzi3E4iCFlswBj7DVqH66ApnL8JiD8j6B1NUmac4an0xS6aNTzwJFxXqAG85ADQw\",\"token_type\":\"Bearer\",\"scope\":\"openid listings_search user_management_bff\",\"profile\":{\"amr\":[\"pwd\"],\"sid\":\"ABF9D9FD45B7FAEE3A02048E2770F33D\",\"sub\":\"tautvisl\",\"auth_time\":1744797602,\"idp\":\"local\",\"username\":\"tautvisl\",\"tierGroup\":\"Broker\",\"companyName\":\"T Auto Logistics LLC\",\"customerId\":\"072618d6-dc2e-4906-b5f6-59410aa3a592\",\"activationDate\":\"2020-11-19 06:41:46\",\"accountStatus\":\"Active\",\"isActive\":true,\"userId\":\"5c2587e2-7418-41ce-af26-ec4fc348d4ea\",\"roles\":\"OWNER\",\"marketPlaceIds\":10000,\"marketplaces\":{\"MarketplaceId\":10000,\"Active\":true,\"ReasonCode\":\"COMPLETE_ACTIVATED\"},\"numberOfAccounts\":\"1\",\"loginUsername\":\"tautvisl\",\"firstName\":\"Tautvydas\",\"lastName\":\"Lukauskas\",\"email\":\"logisticstauto@gmail.com\",\"products\":[{\"ProductId\":\"5e6f7677-163d-4e92-ae0d-b5ba7ed7e0bc\",\"MarketplaceId\":10000,\"ProductStatusKey\":\"active\"},{\"ProductId\":\"ea90035f-5566-4bf0-9c38-a23e0daf4af3\",\"MarketplaceId\":10000,\"ProductStatusKey\":\"active\"}],\"mfaExpiration\":\"1744801202\",\"partnerId\":\"\"},\"expires_at\":1745582511}"}"""
    order = json.loads("""{"id":1177,"auction_city":{"location":"Long Island (NY)","city":"Long Island","state":"NY","postal_code":"11763","savannah":0,"nj":270,"houston":0,"miami":0,"chicago":0,"email":""},"auction_image":[],"container":{"destination":null,"ship_line":"","vessel":"","container_key":""},"user":{"id":5012,"delivery_info":{"id":2107,"country":"Lithuania","state":"Siauliai District Municipality","zip_code":78337,"city":"Siauliai","address":"Architektu g. 2A-28"},"is_superuser":false,"first_name":"Mantas","last_name":"Tumėnas","is_staff":false,"email":"tummantas@gmail.com","phone_number":"+37068260054","is_email_confirmed":true,"is_phone_confirmed":true,"country":"LT"},"delivery_status":"pending_payment","appeal":null,"assigned_vehicle":null,"depth_video":{"is_depth_video":false,"is_video_attached":false,"depth_video_url":null},"items":{"2016 BMW 3 SERIES (WBA8B3G57GNT92971)":10400,"Auction Fee":850,"Title Mailing Fee":20,"Broker Fee":275,"Environmental Fee":15,"Premium Vehicle Report":15,"Auction Service Fee":95,"Ocean Transportation":775,"Local Transportation":270,"Internet Bid Fee":160},"created_at":"2025-04-25T00:00:00Z","updated_at":"2025-04-25T09:42:43.272477Z","auction_name":"IAAI","lot_id":40435883,"from_dealer":false,"terminal":"NEW YORK","car_value":10400,"extra_fee":[{"name":"","amount":0}],"invoice_type":"t_autologistics_invoice","vehicle_type":"CAR","vin":"WBA8B3G57GNT92971","vehicle_name":"2016 BMW 3 SERIES","keys":true,"damage":true,"color":"Silver","auto_generated":false,"fee_type":"non_clean_title_fee"}""")
    lising = RequestsListing(order, None,local_storage,  'preview')
    lising.get_pickup_location()
    lising.get_delivery_location()
    lising.get_VIN_info()
    lising.get_price()
    lising.post_listing()

    print(lising.pickup_location)
    print(lising.delivery_location)
    print(lising.VIN_info)
    print(lising.price)









