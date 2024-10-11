from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# Set the path to your image directory
IMAGE_FOLDER = '/home/cc/neurobazaar/neurobazaar/lidc_pixConvImg'

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/')
def index():
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    image_links = [f'<img src="/images/{file}" style="max-width: 300px; margin: 10px;">' for file in image_files]
    return '<h1>Image Gallery</h1>' + ''.join(image_links)

if __name__ == '__main__':
    app.run(debug=True, port=5000)