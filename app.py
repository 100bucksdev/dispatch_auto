from flask import Flask, request, make_response
from browser.automatization import Listing
from multiprocessing import Process, Queue

app = Flask(__name__)

def run_listing(order, local_storage, mode, queue):
    try:
        listing = Listing(order, local_storage)
        listing.set_local_storage()
        if mode == 'post':
            listing.fill_all_fields()
            listing.post_listing()
            queue.put({'success': 'listing_posted'})
        elif mode == 'preview':
            listing.fill_pickup_info()
            listing.fill_delivery_info()
            image = listing.get_screenshots()
            listing.delete_screenshots()
            queue.put({'image': image})
        else:
            queue.put({'error': 'invalid_mode'})
    except Exception as e:
        queue.put({'error': str(e)})

@app.route('/post-listing', methods=['POST'])
def post_listing():
    if request.method != 'POST':
        return {"error": "Only POST requests are allowed"}, 405

    data = request.get_json()
    mode = data.get('mode')
    order = data.get('order')
    local_storage = data.get('local_storage')

    if not order or not local_storage:
        return {'error': 'miss_params'}, 400

    queue = Queue()
    process = Process(target=run_listing, args=(order, local_storage, mode, queue))
    process.start()
    process.join()
    result = queue.get()

    if 'error' in result:
        return {'error': result['error']}, 400
    elif 'success' in result:
        return {'success': result['success']}, 200
    elif 'image' in result:
        return make_response(result['image'], 200, {'Content-Type': 'image/png'})
    else:
        return {'error': 'unknown_error'}, 500

if __name__ == '__main__':
    app.run(debug=True, port=6000)