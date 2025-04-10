from flask import Flask, request, g, jsonify, make_response

from browser.automatization import Listing
from exeption import CustomBadRequestWithDetail

app = Flask(__name__)

@app.errorhandler(CustomBadRequestWithDetail)
def handle_custom_bad_request(error):
    response = jsonify({"error": str(error.detail)})
    response.status_code = 400
    return response
@app.route('/post-listing', methods=['POST'])
def post_listing():
    if request.method == 'POST':
        data = request.get_json()
        mode = data.get('mode')
        order = data.get('order')
        local_storage = data.get('local_storage')

        if not order or not local_storage:
            return {'error': 'miss_params'}, 400

        try:
            listing = Listing(order, local_storage)
            listing.set_local_storage()

            if mode == 'post':
                listing.fill_all_fields()
                listing.post_listing()
                return {'success': 'listing_posted'}, 200
            elif mode == 'preview':
                listing.fill_pickup_info()
                listing.fill_delivery_info()
                image = listing.get_screenshots()
                listing.delete_screenshots()
                # Возвращаем изображение с правильным Content-Type
                return make_response(image, 200, {'Content-Type': 'image/png'})
            else:
                return {'error': 'invalid_mode'}, 400
        except Exception as e:
            return {'error': str(e)}, 400
    else:
        return {"error": "Only POST requests are allowed"}, 405



if __name__ == '__main__':
    app.run(debug=True, port=6000)
