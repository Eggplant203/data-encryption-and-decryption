# src/barcode_mode.py
import barcode
from barcode.writer import ImageWriter
import io
import os
from PIL import Image, ImageDraw, ImageFont
from pyzbar import pyzbar

# Ensure FiraCode is available if possible
try:
    from .font_installer import ensure_firacode_available
    ensure_firacode_available(silent=True)
except ImportError:
    pass

def get_barcode_example_text(barcode_type: str) -> str:
    """
    Get appropriate example text for each barcode type.
    
    :param barcode_type: Type of barcode
    :return: Example text suitable for that barcode type
    """
    # Handle invalid input
    if not isinstance(barcode_type, str):
        barcode_type = str(barcode_type)
    
    barcode_type = barcode_type.lower()
    
    examples = {
        'code128': 'Hello World!',      # Can handle mixed text
        'code39': 'HELLO123',           # Uppercase + numbers
        'ean8': '1234567',              # 7 digits only
        'ean13': '123456789012',        # 12 digits only  
        'upc_a': '12345678901',         # 11 digits only
        'isbn': '9781234567897',        # 13 digits starting with 978/979
        'issn': '12345678',             # 8 digits with dash: 1234-5678
        'pzn': '123456'                 # 6-7 digits
    }
    
    return examples.get(barcode_type, 'Hello World!')  # Default fallback

def get_barcode_tooltip_text(barcode_type: str) -> str:
    """
    Get detailed tooltip text explaining what strings this barcode type can handle.
    
    :param barcode_type: Type of barcode
    :return: Tooltip text with detailed description
    """
    # Handle invalid input
    if not isinstance(barcode_type, str):
        barcode_type = str(barcode_type)
        
    barcode_type = barcode_type.lower()
    
    tooltips = {
        'code128': 'CODE128 - Most flexible\n• Supports: All ASCII characters (letters, numbers, symbols)\n• Examples: "Hello World!", "ABC-123", "2024/08/22"\n• Cannot use: Unicode characters (Vietnamese, emojis)',
        
        'code39': 'CODE39 - Limited character set\n• Supports: A-Z (uppercase only), 0-9, space\n• Special chars: - . $ / + % *\n• Examples: "HELLO123", "ABC-456", "TEST$123"\n• Cannot use: lowercase letters, other symbols',
        
        'ean8': 'EAN-8 - Product barcode (8 digits)\n• Supports: Exactly 7 numbers (8th is auto-calculated)\n• Examples: "1234567", "9876543"\n• Cannot use: Letters, symbols, wrong length',
        
        'ean13': 'EAN-13 - International product barcode\n• Supports: Exactly 12 numbers (13th is auto-calculated)\n• Examples: "123456789012", "978123456789"\n• Cannot use: Letters, symbols, wrong length',
        
        'upca': 'UPC-A - North American product barcode\n• Supports: Exactly 11 numbers (12th is auto-calculated)\n• Examples: "01234567890", "12345678901"\n• Cannot use: Letters, symbols, wrong length',
        
        'isbn10': 'ISBN-10 - Book identifier (old format)\n• Supports: 9 digits + 1 check digit (can be X)\n• Examples: "0123456789", "012345678X"\n• Format: First 9 must be digits, last can be digit or X',
        
        'isbn13': 'ISBN-13 - Book identifier (new format)\n• Supports: Exactly 13 digits (usually starts with 978/979)\n• Examples: "9780123456789", "9791234567890"\n• Cannot use: Letters, symbols, wrong length',
        
        'issn': 'ISSN - Serial publication identifier\n• Supports: 7 digits + 1 check digit (can be X)\n• Examples: "12345678", "1234567X", "1234-5678"\n• Format: XXXXXXXX or XXXX-XXXX',
        
        'pzn': 'PZN - German pharmaceutical code\n• Supports: 6 or 7 digits only\n• Examples: "123456" (6 digits), "1234567" (7 digits)\n• Cannot use: Letters, symbols, other lengths'
    }
    
    return tooltips.get(barcode_type, 'Unknown barcode type')

def validate_barcode_data(data: str, barcode_type: str) -> tuple[bool, str]:
    """
    Validate if data is compatible with the specified barcode type.
    
    :param data: Text content to validate
    :param barcode_type: Type of barcode to validate against
    :return: Tuple of (is_valid, error_message)
    """
    barcode_type = barcode_type.lower()
    
    if barcode_type == 'code128':
        # Code128 accepts almost any ASCII characters
        try:
            data.encode('ascii')
            return True, ""
        except UnicodeEncodeError:
            return False, "Code128 only supports ASCII characters.\nValid examples: 'Hello123', 'ABC-456', '2024/08/22'"
    
    elif barcode_type == 'code39':
        # Code39 accepts: A-Z, 0-9, space, and special chars: - . $ / + % *
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -.$/+%*')
        data_upper = data.upper()
        invalid_chars = set(data_upper) - valid_chars
        if invalid_chars:
            return False, f"Code39 only supports: A-Z, 0-9, space and special characters: - . $ / + % *\nInvalid characters: {', '.join(invalid_chars)}\nValid examples: 'HELLO123', 'ABC-456', 'TEST$123'"
        return True, ""
    
    elif barcode_type in ['ean8']:
        # EAN-8 requires exactly 7 digits (8th is check digit)
        clean_data = data.replace('-', '').replace(' ', '')
        if not clean_data.isdigit():
            non_digit_chars = [c for c in clean_data if not c.isdigit()]
            return False, f"EAN-8 only accepts numbers.\nInvalid characters: {', '.join(non_digit_chars)}\nValid examples: '1234567', '9876543'"
        if len(clean_data) != 7:
            if len(clean_data) < 7:
                return False, f"EAN-8 requires exactly 7 digits (current: {len(clean_data)} digits, need {7-len(clean_data)} more).\nValid examples: '1234567', '9876543'"
            else:
                return False, f"EAN-8 requires exactly 7 digits (current: {len(clean_data)} digits, {len(clean_data)-7} too many).\nValid examples: '1234567', '9876543'"
        return True, ""
    
    elif barcode_type in ['ean13', 'jan']:
        # EAN-13/JAN requires exactly 12 digits (13th is check digit)
        clean_data = data.replace('-', '').replace(' ', '')
        if not clean_data.isdigit():
            non_digit_chars = [c for c in clean_data if not c.isdigit()]
            return False, f"EAN-13/JAN only accepts numbers.\nInvalid characters: {', '.join(non_digit_chars)}\nValid examples: '123456789012', '978123456789'"
        if len(clean_data) != 12:
            if len(clean_data) < 12:
                return False, f"EAN-13/JAN requires exactly 12 digits (current: {len(clean_data)} digits, need {12-len(clean_data)} more).\nValid examples: '123456789012', '978123456789'"
            else:
                return False, f"EAN-13/JAN requires exactly 12 digits (current: {len(clean_data)} digits, {len(clean_data)-12} too many).\nValid examples: '123456789012', '978123456789'"
        return True, ""
    
    elif barcode_type == 'upca':
        # UPC-A requires exactly 11 digits (12th is check digit)
        clean_data = data.replace('-', '').replace(' ', '')
        if not clean_data.isdigit():
            return False, "UPC-A only accepts numbers.\nValid examples: '01234567890', '12345678901'"
        if len(clean_data) != 11:
            return False, f"UPC-A requires exactly 11 digits (current: {len(clean_data)} digits).\nValid examples: '01234567890', '12345678901'"
        return True, ""
    
    elif barcode_type == 'isbn10':
        # ISBN-10: 9 digits + check digit (can be X)
        clean_data = data.replace('-', '').replace(' ', '').upper()
        if len(clean_data) != 10:
            return False, f"ISBN-10 requires exactly 10 characters (current: {len(clean_data)} characters).\nValid examples: '0123456789', '012345678X'"
        # First 9 must be digits, last can be digit or X
        if not clean_data[:9].isdigit():
            return False, "ISBN-10: First 9 characters must be digits.\nValid examples: '0123456789', '012345678X'"
        if not (clean_data[9].isdigit() or clean_data[9] == 'X'):
            return False, "ISBN-10: Last character must be a digit or X.\nValid examples: '0123456789', '012345678X'"
        return True, ""
    
    elif barcode_type == 'isbn13':
        # ISBN-13: 13 digits (usually starts with 978 or 979)
        clean_data = data.replace('-', '').replace(' ', '')
        if not clean_data.isdigit():
            return False, "ISBN-13 only accepts numbers.\nValid examples: '9780123456789', '9791234567890'"
        if len(clean_data) != 13:
            return False, f"ISBN-13 requires exactly 13 digits (current: {len(clean_data)} digits).\nValid examples: '9780123456789', '9791234567890'"
        return True, ""
    
    elif barcode_type == 'issn':
        # ISSN: 8 digits with format XXXX-XXXX
        clean_data = data.replace('-', '').replace(' ', '').upper()
        if len(clean_data) != 8:
            return False, f"ISSN requires exactly 8 characters (current: {len(clean_data)} characters).\nValid examples: '12345678', '1234567X', '1234-5678'"
        # First 7 must be digits, last can be digit or X
        if not clean_data[:7].isdigit():
            return False, "ISSN: First 7 characters must be digits.\nValid examples: '12345678', '1234567X'"
        if not (clean_data[7].isdigit() or clean_data[7] == 'X'):
            return False, "ISSN: Last character must be a digit or X.\nValid examples: '12345678', '1234567X'"
        return True, ""
    
    elif barcode_type == 'pzn':
        # PZN: 6 or 7 digits
        clean_data = data.replace('-', '').replace(' ', '')
        if not clean_data.isdigit():
            return False, "PZN only accepts numbers.\nValid examples: '123456' (6 digits), '1234567' (7 digits)"
        if len(clean_data) not in [6, 7]:
            if len(clean_data) < 6:
                return False, f"PZN requires at least 6 digits (current: {len(clean_data)} digits).\nValid examples: '123456' (6 digits), '1234567' (7 digits)"
            else:
                return False, f"PZN accepts maximum 7 digits (current: {len(clean_data)} digits).\nValid examples: '123456' (6 digits), '1234567' (7 digits)"
        return True, ""
    
    # Default case
    return True, ""

def encode(data, encoding: str = "utf-8", **kwargs) -> str:
    """
    Encode data into a barcode and return as a special format string.
    
    :param data: Text content (string or bytes) to encode in barcode
    :param encoding: String encoding if data is bytes
    :param **kwargs: Additional options (barcode_type, module_width, module_height, quiet_zone, text_distance, custom_text_content, hide_text)
    :return: A special format string containing barcode image data
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
    barcode_type = kwargs.get('barcode_type', 'code128')
    module_width = kwargs.get('module_width', 0.2)
    module_height = kwargs.get('module_height', 15.0)
    quiet_zone = kwargs.get('quiet_zone', 6.5)
    text_distance = kwargs.get('text_distance', 5.0)
    font_size = kwargs.get('font_size', 10)
    custom_text_content = kwargs.get('custom_text_content', '')
    hide_text = kwargs.get('hide_text', False)
    
    # Validate data against barcode type
    is_valid, error_message = validate_barcode_data(text, barcode_type)
    if not is_valid:
        raise ValueError(f"Data is not compatible with barcode type {barcode_type.upper()}:\n\n{error_message}")
    
    # Map barcode types to available classes
    barcode_classes = {
        'code128': barcode.Code128,
        'code39': barcode.Code39,
        'ean8': barcode.EAN8,
        'ean13': barcode.EAN13,
        'jan': barcode.JAN,
        'isbn10': barcode.ISBN10,
        'isbn13': barcode.ISBN13,
        'issn': barcode.ISSN,
        'upca': barcode.UPCA,
        'pzn': barcode.PZN
    }
    
    # Get the barcode class
    barcode_class = barcode_classes.get(barcode_type.lower(), barcode.Code128)
    
    try:
        # Store original text for decoding later
        original_text = text
        
        # Prepare data for specific barcode types
        barcode_data_text = text
        
        # Clean and format data for specific barcode types
        if barcode_type.lower() in ['ean8', 'ean13', 'jan', 'upca', 'isbn10', 'isbn13', 'issn', 'pzn']:
            # Remove formatting characters for numeric barcodes
            barcode_data_text = text.replace('-', '').replace(' ', '')
        
        if barcode_type.lower() == 'code39':
            # Code39 requires uppercase
            barcode_data_text = text.upper()
        
        # Handle text display options
        display_text = text  # Original text to display
        if hide_text:
            # Hide text completely - set text_distance to 0 and create barcode without text
            text_distance = 0
            display_text = ""
        elif custom_text_content and custom_text_content.strip():
            # Use custom text content
            display_text = custom_text_content.strip()
        
        writer = ImageWriter()
        writer.set_options({
            'module_width': module_width,
            'module_height': module_height,
            'quiet_zone': quiet_zone,
            'text_distance': text_distance if not hide_text else 0,
            'font_size': font_size,
            'write_text': not hide_text  # Control whether text is written or not
        })
        
        # Generate barcode using the cleaned/formatted data
        code = barcode_class(barcode_data_text, writer=writer)
        
        # Create an image from the barcode
        buffer = io.BytesIO()
        
        if hide_text:
            # Generate barcode without text
            code.write(buffer, options={'write_text': False})
        elif custom_text_content and custom_text_content.strip():
            # Generate barcode without default text, we'll add custom text later
            code.write(buffer, options={'write_text': False})
        else:
            # Generate barcode with default text
            code.write(buffer)
        
        barcode_data = buffer.getvalue()
        
        # If custom text is specified and we're not hiding text, we need to modify the image
        if custom_text_content and custom_text_content.strip() and not hide_text:
            # Load the generated barcode image and add custom text
            try:
                from PIL import Image, ImageDraw, ImageFont
                
                # Load the barcode image from buffer
                barcode_img = Image.open(io.BytesIO(barcode_data))
                
                # Create a new image with extra space for custom text
                img_width, img_height = barcode_img.size
                text_height = int(font_size + text_distance + 10)  # Extra padding, convert to int
                new_height = int(img_height + text_height)  # Convert to int
                new_img = Image.new('RGB', (img_width, new_height), 'white')
                
                # Paste the original barcode
                new_img.paste(barcode_img, (0, 0))
                
                # Add custom text
                draw = ImageDraw.Draw(new_img)
                # Improved font loading with better fallback chain
                font = None
                
                # Get current directory for relative font paths
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                fonts_dir = os.path.join(current_dir, "fonts")
                
                font_paths = [
                    # FiraCode in project fonts directory (highest priority)
                    os.path.join(fonts_dir, "FiraCode-Regular.ttf"),
                    os.path.join(fonts_dir, "FiraCode.ttf"),
                    os.path.join(fonts_dir, "firacode-regular.ttf"),
                    # FiraCode system installations
                    "FiraCode-Regular.ttf",
                    "C:/Windows/Fonts/FiraCode-Regular.ttf",
                    f"C:/Users/{os.environ.get('USERNAME', 'user')}/AppData/Local/Microsoft/Windows/Fonts/FiraCode-Regular.ttf",
                    "FiraCode.ttf", 
                    "C:/Windows/Fonts/FiraCode.ttf",
                    "firacode",
                    # Consolas (excellent monospace font on Windows)
                    "C:/Windows/Fonts/consola.ttf",
                    "consolas.ttf",
                    "C:/Windows/Fonts/consolab.ttf",  # Bold version
                    # Courier New (classic monospace)
                    "C:/Windows/Fonts/cour.ttf",
                    "C:/Windows/Fonts/courbd.ttf",
                    "courier.ttf",
                    # DejaVu Sans Mono (good cross-platform option)
                    "DejaVuSansMono.ttf",
                    "DejaVuSansMono-Bold.ttf",
                    # Arial fallbacks
                    "C:/Windows/Fonts/arial.ttf",
                    "arial.ttf"
                ]
                
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue
                
                # Final fallback to default font
                if font is None:
                    font = ImageFont.load_default()
                
                # Calculate text position (centered)
                bbox = draw.textbbox((0, 0), custom_text_content, font=font)
                text_width = bbox[2] - bbox[0]
                text_x = (img_width - text_width) // 2
                text_y = int(img_height + text_distance)  # Convert to int
                
                draw.text((text_x, text_y), custom_text_content, fill='black', font=font)
                
                # Save the modified image back to buffer
                buffer = io.BytesIO()
                new_img.save(buffer, format='PNG')
                barcode_data = buffer.getvalue()
                
            except Exception:
                # If image manipulation fails, use original barcode
                pass
        
        # Return special format string with original text preserved
        return f"BARCODE:{len(barcode_data)}:{barcode_data.hex()}:ORIGINAL:{original_text}"
        
    except Exception as e:
        # Re-raise the error for proper error handling
        raise ValueError(f"Cannot create barcode {barcode_type.upper()}: {str(e)}")

def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode a barcode image data from special format string.
    
    :param text: Special format string containing barcode image data
    :param encoding: String encoding (used to encode result if needed)
    :return: Decoded data from barcode as bytes
    """
    # Check if the text starts with our special prefix
    if not text.startswith("BARCODE:"):
        raise ValueError("Invalid barcode format")
    
    # Check if this is the new format with original text preserved
    if ":ORIGINAL:" in text:
        # New format: BARCODE:length:hex_data:ORIGINAL:original_text
        parts = text.split(':ORIGINAL:', 1)
        if len(parts) == 2:
            # Return the original text as bytes
            original_text = parts[1]
            return original_text.encode(encoding)
    
    # Old format or fallback: extract and decode the barcode image
    parts = text.split(':', 3)  # Allow for more parts in case of new format
    if len(parts) < 3:
        raise ValueError("Invalid barcode format")
    
    # Convert hex back to binary
    barcode_data = bytes.fromhex(parts[2])
    
    # Load image from binary data
    img = Image.open(io.BytesIO(barcode_data))
    
    # Decode barcode
    decoded_objects = pyzbar.decode(img)
    if not decoded_objects:
        raise ValueError("No barcode found in the image")
    
    # Get the data from the first barcode found
    barcode_raw = decoded_objects[0]
    barcode_text = barcode_raw.data
    barcode_format = barcode_raw.type
    
    # Convert to string if bytes
    if isinstance(barcode_text, bytes):
        decoded_text = barcode_text.decode(encoding)
    else:
        decoded_text = str(barcode_text)
    
    # Try to reverse the formatting that standard barcodes add
    original_data = reverse_barcode_formatting(decoded_text, barcode_format)
    
    # Return the decoded data as bytes
    return original_data.encode(encoding)

def reverse_barcode_formatting(decoded_text: str, barcode_format: str) -> str:
    """
    Try to reverse the standard formatting that barcode libraries add.
    
    :param decoded_text: The text decoded by pyzbar
    :param barcode_format: The barcode format detected by pyzbar
    :return: The original data if possible to reverse, otherwise the decoded text
    """
    try:
        if barcode_format == "CODE39":
            # PZN barcodes are encoded as Code39 and pyzbar returns "PZN-XXXXXXX" 
            if decoded_text.startswith("PZN-") and len(decoded_text) >= 5:
                # Extract just the numeric part, remove check digit if present
                numeric_part = decoded_text[4:]  # Remove "PZN-"
                # Check if it's likely our original data (6-7 digits)
                if numeric_part.isdigit() and len(numeric_part) in [7, 8]:
                    # Remove the last digit (check digit) to get back original
                    return numeric_part[:-1]
            
            # Code39 sometimes adds trailing characters, remove them
            if decoded_text.endswith('$'):
                return decoded_text[:-1]
                
        elif barcode_format == "EAN8":
            # EAN8 barcodes add check digits
            if decoded_text.isdigit() and len(decoded_text) == 8:
                # Remove check digit to get original 7 digits
                return decoded_text[:-1]
                
        elif barcode_format == "EAN13":
            # EAN13 could be regular EAN13 or UPC-A encoded as EAN13
            if decoded_text.isdigit() and len(decoded_text) == 13:
                # Check if this might be UPC-A encoded as EAN13
                if decoded_text.startswith("00"):
                    # UPC-A: Remove "00" prefix and check digit, but need to preserve the leading zero
                    upc_part = decoded_text[2:-1]  # Remove "00" and check digit
                    # The original UPC-A likely had a leading zero, so add it back
                    if len(upc_part) == 10:
                        return "0" + upc_part
                    return upc_part
                else:
                    # Regular EAN13 - remove check digit to get original 12 digits
                    return decoded_text[:-1]
    
    except Exception:
        # If anything fails, just return the original decoded text
        pass
    
    # Default: return the decoded text as-is
    return decoded_text

def save_barcode_image(text: str, output_path: str) -> bool:
    """
    Save the barcode image to a file.
    
    :param text: Special format string containing barcode image data
    :param output_path: Path where to save the image
    :return: True if successful, False otherwise
    """
    try:
        # Handle new format with original text
        if ":ORIGINAL:" in text:
            # New format: BARCODE:length:hex_data:ORIGINAL:original_text
            parts = text.split(':ORIGINAL:', 1)[0].split(':')
        else:
            # Old format: BARCODE:length:hex_data
            parts = text.split(':')
        
        if len(parts) < 3:
            return False
        
        # Convert hex back to binary
        barcode_data = bytes.fromhex(parts[2])
        
        # Write to file
        with open(output_path, 'wb') as f:
            f.write(barcode_data)
        
        return True
    except Exception:
        return False

def get_max_text_length() -> int:
    """
    Get the maximum recommended text length for barcode.
    
    :return: Maximum text length recommendation
    """
    # Code128 can handle up to about 80 characters effectively
    return 80

def get_options():
    """
    Return available options for Barcode encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "barcode_type": {
            "description": "Type of barcode to generate",
            "type": "str",
            "default": "code128",
            "choices": ["code128", "code39", "ean8", "ean13", "jan", "isbn10", "isbn13", "issn", "upca", "pzn"]
        },
        "module_width": {
            "description": "Width of individual barcode modules (mm)",
            "type": "float",
            "default": 0.2
        },
        "module_height": {
            "description": "Height of barcode modules (mm)",
            "type": "float",
            "default": 15.0
        },
        "quiet_zone": {
            "description": "Size of quiet zone around barcode (mm)",
            "type": "float",
            "default": 6.5
        },
        "text_distance": {
            "description": "Distance between barcode and text (mm)",
            "type": "float",
            "default": 5.0
        },
        "font_size": {
            "description": "Font size for barcode text (pt)",
            "type": "int",
            "default": 43
        },
        "custom_text_content": {
            "description": "Custom text to display under barcode",
            "type": "str",
            "default": "",
            "placeholder": "Enter custom text"
        },
        "hide_text": {
            "description": "Hide text below barcode completely",
            "type": "bool",
            "default": False
        }
    }
