from flask import Flask, request, jsonify
from automatization import RequestsListing
from exeption import CustomBadRequestWithDetail

app = Flask(__name__)

@app.errorhandler(CustomBadRequestWithDetail)
def handle_custom_bad_request(error):
    response = jsonify({"error": error.detail})
    response.status_code = error.status_code
    return response

@app.route('/post-listing', methods=['POST'])
def post_listing():
    if request.method != 'POST':
        return {"error": "Only POST requests are allowed"}, 405
    data = request.get_json()
    mode = data.get('mode')
    order = data.get('order')
    local_storage = data.get('local_storage')
    offsite_location = data.get('offsite_location')
    if not mode or not order or not local_storage:
        return {"error": "Missing required parameters"}, 400

    listing = RequestsListing(order, offsite_location, local_storage, mode)

    if mode == 'preview':
        return {'pickup_location': listing.pickup_location, 'delivery_location': listing.delivery_location}, 200
    else:
        return {'success': True}, 200



if __name__ == '__main__':
    print("Starting Flask on port 6000")
    app.run(debug=True, port=6000)