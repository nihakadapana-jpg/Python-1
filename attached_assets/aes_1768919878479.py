from flask import Flask, request, send_file
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
from PIL import Image
import os

app = Flask(__name__)

# Ensure folders exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)

# ================= AES & Steganography Functions =================

# AES Encryption
def encrypt(text, key):
    cipher = AES.new(key, AES.MODE_ECB)
    padded_text = text.encode()
    pad_len = 16 - len(padded_text) % 16
    padded_text += bytes([pad_len]) * pad_len
    encrypted = cipher.encrypt(padded_text)
    return base64.b64encode(encrypted).decode()

# AES Decryption
def decrypt(encrypted_text, key):
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(base64.b64decode(encrypted_text))
    pad_len = decrypted[-1]
    return decrypted[:-pad_len].decode()

# Hide message in image (LSB of blue channel)
def hide_message(img, message_bytes, output_path):
    width, height = img.size
    pixels = img.load()
    msg_index = 0
    bit_index = 0
    for y in range(height):
        for x in range(width):
            if msg_index >= len(message_bytes):
                img.save(output_path, "PNG")
                return
            r, g, b = pixels[x, y]
            bit = (message_bytes[msg_index] >> (7 - bit_index)) & 1
            b = (b & 0xFE) | bit
            pixels[x, y] = (r, g, b)
            bit_index += 1
            if bit_index == 8:
                bit_index = 0
                msg_index += 1

# Extract message from image
def extract_message(img, message_length):
    width, height = img.size
    pixels = img.load()
    message_bytes = bytearray(message_length)
    msg_index = 0
    bit_index = 0
    for y in range(height):
        for x in range(width):
            if msg_index >= message_length:
                return bytes(message_bytes)
            b = pixels[x, y][2]
            bit = b & 1
            message_bytes[msg_index] = ((message_bytes[msg_index] << 1) | bit) & 0xFF
            bit_index += 1
            if bit_index == 8:
                bit_index = 0
                msg_index += 1
    return bytes(message_bytes)

# ================= Flask Routes =================

@app.route("/")
def home():
    return "AES Image Steganography Flask App is LIVE!"

@app.route("/run", methods=["GET"])
def run_demo():
    # ================= MAIN =================
    key = get_random_bytes(16)
    message = "Secret AES Message"

    encrypted = encrypt(message, key)
    print("Encrypted:", encrypted)
    encrypted_bytes = encrypted.encode()

    # Load image (make sure images.png exists in project)
    img = Image.open("images.png").convert("RGB")

    # Hide message
    hide_message(img, encrypted_bytes, "output/output.png")
    print("Message hidden in output/output.png")

    # Extract message
    out_img = Image.open("output/output.png")
    extracted_bytes = extract_message(out_img, len(encrypted_bytes))
    extracted = extracted_bytes.decode()
    print("Extracted:", extracted)

    # Decrypt
    decrypted = decrypt(extracted, key)
    print("Decrypted:", decrypted)

    return f"""
    Encrypted: {encrypted}<br>
    Extracted: {extracted}<br>
    Decrypted: {decrypted}<br>
    Check 'output/output.png' for the stego image.
    """

# ================= RUN FLASK =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)