# src/image_mode.py
from PIL import Image, ImageFile
import io
import numpy as np
import math

# Disable DecompressionBombWarning
# This is necessary when working with large image files
Image.MAX_IMAGE_PIXELS = None  # Disable the maximum pixel limit check
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Allow loading of truncated image data

def encode(data: bytes, encoding: str = "utf-8", **kwargs) -> str:
    """
    Encode binary data into an image and return as a special format string.
    The image can be saved separately.
    
    :param data: Binary data to encode (includes metadata + file content)
    :param encoding: String encoding (used only for metadata storage, not for pixel data)
    :param **kwargs: Additional options (compression)
    :return: A special format string containing image data
    
    Note: The image encoding preserves metadata including filename and encoding.
    The metadata will be extracted during the decoding process.
    """
    # Convert data to numpy array of bytes
    byte_array = np.frombuffer(data, dtype=np.uint8)
    
    # Calculate dimensions for a square-ish image
    # Each pixel stores 3 bytes (R,G,B)
    num_bytes = len(byte_array)
    # We need to store the original length for decoding
    metadata_size = 4  # 4 bytes for storing the size
    total_bytes = num_bytes + metadata_size
    
    # Calculate image dimensions
    pixels_needed = math.ceil(total_bytes / 3)
    width = math.ceil(math.sqrt(pixels_needed))
    height = math.ceil(pixels_needed / width)
    
    # Create image array with all pixels initialized to black
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    
    # First 4 bytes store the original data length (as 4 individual bytes)
    length_bytes = num_bytes.to_bytes(4, byteorder='big')
    
    # Combine metadata and actual data - data already includes metadata
    full_data = length_bytes + data
    
    # Fill the image with data
    index = 0
    for y in range(height):
        for x in range(width):
            # Get 3 bytes for R, G, B
            r = full_data[index] if index < len(full_data) else 0
            g = full_data[index + 1] if index + 1 < len(full_data) else 0
            b = full_data[index + 2] if index + 2 < len(full_data) else 0
            
            # Set pixel values
            img_array[y, x] = [r, g, b]
            
            # Move to next 3 bytes
            index += 3
            
            # Stop if we've used all the data
            if index >= len(full_data):
                break
    
    # Create PIL Image from numpy array
    img = Image.fromarray(img_array)
    
    # Get compression level from kwargs
    compression = kwargs.get('compression', 6)
    
    # Save to BytesIO and convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', compress_level=compression)
    img_data = buffer.getvalue()
    
    # Return special format string that indicates this is image data
    return f"IMG_DATA:{len(img_data)}:{img_data.hex()}"

def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode data from the special image format string.
    
    :param text: Special format string containing image data
    :param encoding: String encoding (not used for actual decoding, kept for API consistency)
    :return: The original binary data (includes metadata + file content)
    """
    # Check if the text starts with our special prefix
    if not text.startswith("IMG_DATA:"):
        raise ValueError("Invalid image data format")
    
    # Extract the data part
    parts = text.split(':', 2)
    if len(parts) != 3:
        raise ValueError("Invalid image data format")
    
    # Convert hex back to binary
    img_data = bytes.fromhex(parts[2])
    
    # Load the image from binary data
    img = Image.open(io.BytesIO(img_data))
    
    # Convert to numpy array
    img_array = np.array(img)
    
    # Extract data from pixels
    height, width, _ = img_array.shape
    data_bytes = []
    
    # Process each pixel
    for y in range(height):
        for x in range(width):
            # Get RGB values
            r, g, b = img_array[y, x]
            
            # Add each byte to our list
            data_bytes.extend([r, g, b])
    
    # Convert to bytes
    all_bytes = bytes(data_bytes)
    
    # First 4 bytes are metadata (original length)
    original_length = int.from_bytes(all_bytes[:4], byteorder='big')
    
    # Return the original data part (includes metadata + file content)
    return all_bytes[4:4 + original_length]

def save_image(text: str, output_path: str) -> bool:
    """
    Save the encoded image data to a file.
    
    :param text: The encoded image string returned by encode()
    :param output_path: Path where to save the image
    :return: True if successful
    """
    if not text.startswith("IMG_DATA:"):
        return False
    
    parts = text.split(':', 2)
    if len(parts) != 3:
        return False
    
    img_data = bytes.fromhex(parts[2])
    
    with open(output_path, 'wb') as f:
        f.write(img_data)
    
    return True

def get_options():
    """
    Return available options for Image encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "compression": {
            "description": "PNG compression level (0-9)",
            "type": "int",
            "default": 6,
            "min": 0,
            "max": 9
        }
    }
