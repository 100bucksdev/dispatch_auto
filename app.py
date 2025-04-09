from flask import Flask, request, g

from browser.automatization import Listing

app = Flask(__name__)


@app.route('/post-listing', methods=['POST'])
def post_listing():
    if request.method == 'POST':
        data = request.form.to_dict()
        mode = data.get('mode')
        order = data.get('order')
        local_storage = data.get('local_storage')

        if not order or not local_storage:
            return {'error': 'Parameters missing'}, 400

        # Создаем объект listing
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
            return image, 200
        else:
            return {'error': 'Invalid mode'}, 400
    else:
        return {"error": "Only POST requests are allowed"}, 405



if __name__ == '__main__':
    app.run(debug=True)
