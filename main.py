from flask import Flask, render_template, request, send_file, redirect, url_for
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
from PIL import Image
import os
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# ================= AES & Steganography Functions =================

def encrypt_aes(text, key):
    # Ensure key is 16 bytes
    key_bytes = key.encode().ljust(16)[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_text = text.encode()
    pad_len = 16 - len(padded_text) % 16
    padded_text += bytes([pad_len]) * pad_len
    encrypted = cipher.encrypt(padded_text)
    return base64.b64encode(encrypted).decode()

def decrypt_aes(encrypted_text, key):
    key_bytes = key.encode().ljust(16)[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    try:
        decrypted = cipher.decrypt(base64.b64decode(encrypted_text))
        pad_len = decrypted[-1]
        if pad_len < 1 or pad_len > 16:
            return "Error: Invalid Padding or Key"
        return decrypted[:-pad_len].decode()
    except Exception as e:
        return f"Error: {str(e)}"

def hide_message(img, message_bytes, output_path):
    img = img.convert("RGB")
    width, height = img.size
    pixels = img.load()
    
    # Store length of message first (4 bytes)
    msg_len = len(message_bytes)
    full_data = msg_len.to_bytes(4, 'big') + message_bytes
    
    data_index = 0
    bit_index = 0
    
    for y in range(height):
        for x in range(width):
            if data_index >= len(full_data):
                img.save(output_path, "PNG")
                return
            
            r, g, b = pixels[x, y]
            # Hide bit in Blue channel LSB
            bit = (full_data[data_index] >> (7 - bit_index)) & 1
            b = (b & 0xFE) | bit
            pixels[x, y] = (r, g, b)
            
            bit_index += 1
            if bit_index == 8:
                bit_index = 0
                data_index += 1
    img.save(output_path, "PNG")

def extract_message(img):
    img = img.convert("RGB")
    width, height = img.size
    pixels = img.load()
    
    # Extract length first
    len_bytes = bytearray(4)
    data_index = 0
    bit_index = 0
    
    # Extract first 4 bytes for length
    for y in range(height):
        for x in range(width):
            if data_index >= 4:
                break
            b = pixels[x, y][2]
            bit = b & 1
            len_bytes[data_index] = ((len_bytes[data_index] << 1) | bit) & 0xFF
            bit_index += 1
            if bit_index == 8:
                bit_index = 0
                data_index += 1
        if data_index >= 4:
            break
            
    msg_length = int.from_bytes(len_bytes, 'big')
    if msg_length > width * height: # Safety check
        return None
        
    message_bytes = bytearray(msg_length)
    data_index = 0
    bit_index = 0
    
    # Reset bit extraction for the message part
    current_bit_count = 0
    bits_to_skip = 32 # 4 bytes
    
    for y in range(height):
        for x in range(width):
            if current_bit_count < bits_to_skip:
                current_bit_count += 1
                continue
                
            if data_index >= msg_length:
                return bytes(message_bytes)
                
            b = pixels[x, y][2]
            bit = b & 1
            message_bytes[data_index] = ((message_bytes[data_index] << 1) | bit) & 0xFF
            
            bit_index += 1
            if bit_index == 8:
                bit_index = 0
                data_index += 1
    return bytes(message_bytes)

# ================= Routes =================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/encrypt", methods=["GET", "POST"])
def encrypt_page():
    suggestions = [
        "nature_landscape,_ci_a1059f2e.jpg",
        "nature_landscape,_ci_6d770e91.jpg",
        "nature_landscape,_ci_cf31e7fa.jpg"
    ]
    if request.method == "POST":
        text = request.form.get("text")
        key = request.form.get("key")
        
        file = request.files.get("image")
        suggested_img = request.form.get("suggested_image")
        
        if file and file.filename:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(img_path)
            img = Image.open(img_path)
        elif suggested_img:
            img_path = os.path.join("attached_assets/stock_images", suggested_img)
            img = Image.open(img_path)
        else:
            return "Please select or upload an image"

        encrypted_text = encrypt_aes(text, key)
        output_filename = "encrypted_image.png"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        hide_message(img, encrypted_text.encode(), output_path)
        
        return render_template("encrypt.html", suggestions=suggestions, download=output_filename)
        
    return render_template("encrypt.html", suggestions=suggestions)

@app.route("/decrypt", methods=["GET", "POST"])
def decrypt_page():
    result = None
    if request.method == "POST":
        key = request.form.get("key")
        file = request.files.get("image")
        
        if file:
            img = Image.open(file)
            extracted_bytes = extract_message(img)
            if extracted_bytes:
                encrypted_text = extracted_bytes.decode()
                result = decrypt_aes(encrypted_text, key)
            else:
                result = "Could not extract message."
                
    return render_template("decrypt.html", result=result)

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

@app.route("/how-to-use")
def how_to_use():
    return render_template("how_to_use.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
