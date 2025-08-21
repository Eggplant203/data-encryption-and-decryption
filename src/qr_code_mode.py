# src/qr_code_mode.py
import qrcode
import io
from PIL import Image
from pyzbar import pyzbar

def encode(data, encoding: str = "utf-8", **kwargs) -> str:
    """
    Encode data into a QR code and return as a special format string.
    
    :param data: Text content (string or bytes) to encode in QR code
    :param encoding: String encoding if data is bytes
    :param **kwargs: Additional options (error_correction, box_size, border)
    :return: A special format string containing QR image data
    """
    # Convert data to string if needed
    if isinstance(data, bytes):
        try:
            # Try to decode the bytes to string 
            text = data.decode(encoding, errors="replace")
        except UnicodeDecodeError:
            # If fails, use hex representation
            text = data.hex()
    else:
        text = str(data)
    
    # Get options from kwargs
    error_correction_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    
    error_correction = error_correction_map.get(kwargs.get('error_correction', 'L'), qrcode.constants.ERROR_CORRECT_L)
    box_size = kwargs.get('box_size', 10)
    border = kwargs.get('border', 4)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=None,  # Auto-determine version
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    
    qr.add_data(text)
    qr.make(fit=True)
    
    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_data = buffer.getvalue()
    
    # Return special format string
    return f"QR_CODE:{len(qr_data)}:{qr_data.hex()}"

def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode a QR code image data from special format string.
    
    :param text: Special format string containing QR image data
    :param encoding: String encoding (used to encode result if needed)
    :return: Decoded data from QR code as bytes
    """
    # Check if the text starts with our special prefix
    if not text.startswith("QR_CODE:"):
        raise ValueError("Invalid QR code format")
    
    # Extract the data part
    parts = text.split(':', 2)
    if len(parts) != 3:
        raise ValueError("Invalid QR code format")
    
    # Convert hex back to binary
    qr_data = bytes.fromhex(parts[2])
    
    # Load image from binary data
    img = Image.open(io.BytesIO(qr_data))
    
    # Decode QR code
    decoded_objects = pyzbar.decode(img)
    if not decoded_objects:
        raise ValueError("No QR code found in the image")
    
    # Get the data from the first QR code found
    qr_text = decoded_objects[0].data
    
    # Return the decoded data as bytes
    if isinstance(qr_text, bytes):
        return qr_text
    else:
        return qr_text.encode(encoding)

def save_qr_image(text: str, output_path: str) -> bool:
    """
    Save the QR code image to a file.
    
    :param text: Special format string containing QR image data
    :param output_path: Path where to save the image
    :return: True if successful, False otherwise
    """
    try:
        # Extract the data part
        parts = text.split(':', 2)
        if len(parts) != 3:
            return False
        
        # Convert hex back to binary
        qr_data = bytes.fromhex(parts[2])
        
        # Write to file
        with open(output_path, 'wb') as f:
            f.write(qr_data)
        
        return True
    except Exception:
        return False

def get_max_text_length() -> int:
    """
    Get the maximum recommended text length for QR code.
    
    :return: Maximum text length recommendation
    """
    # QR code version 40 with low error correction can store up to about 7,089 characters (numeric)
    # But for practical purposes, we'll recommend a lower limit
    return 1000  # Reasonable limit for text in a QR code

def get_options():
    """
    Return available options for QR Code encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "error_correction": {
            "description": "Error correction level (higher = more robust)",
            "type": "str",
            "default": "L",
            "choices": ["L", "M", "Q", "H"]
        },
        "box_size": {
            "description": "Size of each QR code box in pixels",
            "type": "int",
            "default": 10,
            "min": 1,
            "max": 20
        },
        "border": {
            "description": "Border size around the QR code",
            "type": "int", 
            "default": 4,
            "min": 0,
            "max": 20
        }
    }
