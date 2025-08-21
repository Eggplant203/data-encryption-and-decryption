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
        # For numeric-only barcodes, check if text is valid
        if barcode_type.lower() in ['ean8', 'ean13', 'jan', 'upca']:
            # These require numeric input of specific length
            if not text.isdigit():
                # Convert to numeric representation
                text = ''.join([str(ord(c)) for c in text])
                # Pad or truncate to required length
                if barcode_type.lower() == 'ean8':
                    text = text[:7].ljust(7, '0')
                elif barcode_type.lower() in ['ean13', 'jan']:
                    text = text[:12].ljust(12, '0')
                elif barcode_type.lower() == 'upca':
                    text = text[:11].ljust(11, '0')
        elif barcode_type.lower() in ['isbn10', 'isbn13']:
            # ISBN requires specific format
            if not (text.replace('-', '').replace(' ', '').isdigit() or 'X' in text.upper()):
                # Convert to a valid ISBN-like format
                numeric_text = ''.join([str(ord(c)) for c in text])
                if barcode_type.lower() == 'isbn10':
                    text = numeric_text[:9].ljust(9, '0')
                else:
                    text = '978' + numeric_text[:9].ljust(9, '0')
        elif barcode_type.lower() == 'issn':
            # ISSN requires specific format
            if not text.replace('-', '').replace(' ', '').isdigit():
                numeric_text = ''.join([str(ord(c)) for c in text])
                text = numeric_text[:7].ljust(7, '0')
        elif barcode_type.lower() == 'pzn':
            # PZN requires numeric input
            if not text.isdigit():
                text = ''.join([str(ord(c)) for c in text])
                text = text[:6].ljust(6, '0')
        elif barcode_type.lower() == 'code39':
            pass
        
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
        
        # Generate barcode
        code = barcode_class(text, writer=writer)
        
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
        
        # Return special format string
        return f"BARCODE:{len(barcode_data)}:{barcode_data.hex()}"
        
    except Exception as e:
        # If specific barcode type fails, fall back to Code128
        try:
            # Handle text display options for fallback
            display_text = text
            if hide_text:
                text_distance = 0
                display_text = ""
            elif custom_text_content and custom_text_content.strip():
                display_text = custom_text_content.strip()
            
            writer = ImageWriter()
            writer.set_options({
                'module_width': module_width,
                'module_height': module_height,
                'quiet_zone': quiet_zone,
                'text_distance': text_distance if not hide_text else 0,
                'font_size': font_size,
                'write_text': not hide_text
            })
            code = barcode.Code128(text, writer=writer)
            buffer = io.BytesIO()
            
            if hide_text:
                code.write(buffer, options={'write_text': False})
            elif custom_text_content and custom_text_content.strip():
                # Generate barcode without default text, we'll add custom text later
                code.write(buffer, options={'write_text': False})
            else:
                code.write(buffer)
            
            barcode_data = buffer.getvalue()
            
            # If custom text is specified for fallback code as well
            if custom_text_content and custom_text_content.strip() and not hide_text:
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
                    # If image manipulation fails for fallback, use original
                    pass
            
            return f"BARCODE:{len(barcode_data)}:{barcode_data.hex()}"
        except Exception:
            raise ValueError(f"Failed to generate barcode: {str(e)}")

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
    
    # Extract the data part
    parts = text.split(':', 2)
    if len(parts) != 3:
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
    barcode_text = decoded_objects[0].data
    
    # Return the decoded data as bytes
    if isinstance(barcode_text, bytes):
        return barcode_text
    else:
        return barcode_text.encode(encoding)

def save_barcode_image(text: str, output_path: str) -> bool:
    """
    Save the barcode image to a file.
    
    :param text: Special format string containing barcode image data
    :param output_path: Path where to save the image
    :return: True if successful, False otherwise
    """
    try:
        # Extract the data part
        parts = text.split(':', 2)
        if len(parts) != 3:
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
