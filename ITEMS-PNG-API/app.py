import os
import json
import io
from flask import Flask, request, send_file, jsonify, redirect, abort
from PIL import Image
import requests

app = Flask(__name__)

# Configuration for composite images
ITEM_DATA_FILE = 'main.json'
BACKGROUND_FOLDER = 'background'
DEFAULT_BACKGROUND_IMAGE = 'background/Default.png'  # Fallback background image

# Global variable to store item data
item_data = None

def load_item_data():
    """Loads item data from main.json."""
    global item_data
    if item_data is not None:
        return item_data

    file_path = os.path.join(os.path.dirname(__file__), ITEM_DATA_FILE)    
    if not os.path.exists(file_path):    
        app.logger.error(f"Error: {ITEM_DATA_FILE} not found at {file_path}")    
        return None    

    try:    
        with open(file_path, 'r', encoding='utf-8') as f:    
            item_data = json.load(f)    
            app.logger.info(f"Successfully loaded {len(item_data)} items from {ITEM_DATA_FILE}.")    
            return item_data    
    except json.JSONDecodeError as e:    
        app.logger.error(f"Error decoding JSON from {ITEM_DATA_FILE}: {e}")    
        return None    
    except Exception as e:    
        app.logger.error(f"An unexpected error occurred while loading {ITEM_DATA_FILE}: {e}")    
        return None

# Load data when the app starts
with app.app_context():
    load_item_data()

@app.route('/item-image')
def get_item_image():
    """Direct image API - returns raw PNG without background"""
    item_id = request.args.get('id')
    key = request.args.get('key')

    # Validate key    
    if key != 'NRCODEX':    
        abort(403, description="Invalid key")    
  
    if not item_id:    
        abort(400, description="Item ID is required")    
  
    # Check repositories 1 to 6 (updated to include repo 6)
    for repo_num in range(1, 7):    
        # Determine batch range for this repo    
        if repo_num == 1:    
            # First repo has batches 01-06    
            batch_range = range(1, 7)    
        else:    
            # Subsequent repos start from batch 07, 13, 19, 25, 31
            start_batch = (repo_num - 1) * 6 + 1    
            batch_range = range(start_batch, start_batch + 6)    
            
        # Check each batch in this repository    
        for batch_num in batch_range:    
            # Format batch number with leading zero    
            batch_str = f"{batch_num:02d}"    
                
            # Construct the URL    
            url = f"https://raw.githubusercontent.com/djdndbdjfi/free-fire-items-{repo_num}/main/items/batch-{batch_str}/{item_id}.png"    
                
            # Check if image exists    
            response = requests.head(url)    
            if response.status_code == 200:    
                return redirect(url)    
  
    # If no image found in any repository    
    abort(404, description="Item image not found")

@app.route('/main/ICON/<int:itemid>.png', methods=['GET'])
def get_combined_item_image(itemid):
    """Composite image API - returns PNG with background based on rarity"""
    if item_data is None:
        return jsonify({"error": "Item data not loaded. Check server logs."}), 500

    # 1. Find item details from main.json    
    item_found = next((item for item in item_data if item.get("Id") == itemid), None)    

    if not item_found:    
        app.logger.warning(f"Item with ID {itemid} not found in {ITEM_DATA_FILE}")    
        return jsonify({"error": f"Item with ID {itemid} not found."}), 404    

    rare_type = item_found.get("Rare", "Default")  # Default if 'Rare' key is missing    

    # 2. Load background image based on 'Rare' type    
    background_image_path = os.path.join(os.path.dirname(__file__), BACKGROUND_FOLDER, f'{rare_type}.png')    

    if not os.path.exists(background_image_path):    
        app.logger.warning(f"Background image for Rare type '{rare_type}' not found. Using default.")    
        background_image_path = os.path.join(os.path.dirname(__file__), DEFAULT_BACKGROUND_IMAGE)    
        if not os.path.exists(background_image_path):    
            app.logger.error(f"Default background image not found at {DEFAULT_BACKGROUND_IMAGE}.")    
            return jsonify({"error": "Background image not found and default is missing."}), 500    

    try:    
        background = Image.open(background_image_path).convert("RGBA")    
    except Exception as e:    
        app.logger.error(f"Error loading background image {background_image_path}: {e}")    
        return jsonify({"error": "Could not load background image."}), 500    

    # 3. Fetch item image using the direct image API logic    
    item_image_url = None    
    # Check repositories 1 to 6 (updated to include repo 6)
    for repo_num in range(1, 7):    
        # Determine batch range for this repo    
        if repo_num == 1:    
            # First repo has batches 01-06    
            batch_range = range(1, 7)    
        else:    
            # Subsequent repos start from batch 07, 13, 19, 25, 31
            start_batch = (repo_num - 1) * 6 + 1    
            batch_range = range(start_batch, start_batch + 6)    
            
        # Check each batch in this repository    
        for batch_num in batch_range:    
            # Format batch number with leading zero    
            batch_str = f"{batch_num:02d}"    
                
            # Construct the URL    
            url = f"https://raw.githubusercontent.com/djdndbdjfi/free-fire-items-{repo_num}/main/items/batch-{batch_str}/{itemid}.png"    
                
            # Check if image exists    
            response = requests.head(url)    
            if response.status_code == 200:    
                item_image_url = url    
                break    
        if item_image_url:    
            break    
  
    if not item_image_url:    
        app.logger.error(f"Item image for ID {itemid} not found in any repository.")    
        return jsonify({"error": f"Item image for ID {itemid} not found."}), 404    

    # 4. Download the item image    
    try:    
        response = requests.get(item_image_url, stream=True)    
        response.raise_for_status()  # Raise HTTPError for bad responses    

        item_image_bytes = io.BytesIO(response.content)    
        item_image = Image.open(item_image_bytes).convert("RGBA")    
    except requests.exceptions.RequestException as e:    
        app.logger.error(f"Error fetching item image from GitHub for ID {itemid}: {e}")    
        return jsonify({"error": f"Could not fetch item image from GitHub. Error: {e}"}), 502    
    except Image.UnidentifiedImageError:    
        app.logger.error(f"GitHub RAW returned unidentifiable image for ID {itemid}.")    
        return jsonify({"error": "External API did not return a valid image."}), 502    
    except Exception as e:    
        app.logger.error(f"Unexpected error with external image for ID {itemid}: {e}")    
        return jsonify({"error": "Unexpected error with external image."}), 500    

    # 5. Resize and overlay item image onto background    
    bg_width, bg_height = background.size  

    # Calculate target size for item image (80% of background dimensions)  
    target_width = int(bg_width * 0.8)  
    target_height = int(bg_height * 0.8)  
    
    # Resize the item image while maintaining aspect ratio  
    item_width, item_height = item_image.size  
    item_ratio = item_width / item_height  
    target_ratio = target_width / target_height  
    
    if item_ratio > target_ratio:  
        # Image is wider than target  
        new_width = target_width  
        new_height = int(target_width / item_ratio)  
    else:  
        # Image is taller than target  
        new_height = target_height  
        new_width = int(target_height * item_ratio)  
    
    # Resize the item image with high-quality resampling  
    item_image = item_image.resize((new_width, new_height), Image.LANCZOS)  

    # Calculate position to center the item image  
    paste_x = (bg_width - new_width) // 2  
    paste_y = (bg_height - new_height) // 2  

    # Create a transparent layer for the item image  
    item_layer = Image.new("RGBA", background.size, (0, 0, 0, 0))  
    
    # Paste the item image onto the transparent layer  
    item_layer.paste(item_image, (paste_x, paste_y), item_image)  
    
    # Composite the background and item layer  
    combined_image = Image.alpha_composite(background, item_layer)  

    # 6. Return the combined image as PNG    
    img_byte_arr = io.BytesIO()    
    combined_image.save(img_byte_arr, format='PNG')    
    img_byte_arr.seek(0)    

    app.logger.info(f"Successfully generated image for Item ID: {itemid}, Rare: {rare_type}")    
    return send_file(img_byte_arr, mimetype='image/png', as_attachment=False, download_name=f'item_{itemid}.png')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
