# src/braille_mode.py
import struct

# Braille Unicode base character (U+2800)
BRAILLE_OFFSET = 0x2800

# Braille dot patterns (8-dot system): dots 1,2,3,4,5,6,7,8
# Each bit represents a dot: bit 0 = dot 1, bit 1 = dot 2, etc.
# Standard 6-dot Braille uses dots 1-6, 8-dot Braille adds dots 7-8

def encode(data: bytes, encoding: str = "utf-8", **kwargs) -> str:
    """
    Encode data using Braille patterns.
    
    Args:
        data: The bytes data to encode
        encoding: String encoding for output (default: utf-8)
        **kwargs: Additional options (braille_type, add_separators, custom_mapping)
    
    Returns:
        String of Braille patterns
    """
    if not data:
        return ""
    
    # Get options from kwargs or use defaults
    braille_type = kwargs.get('braille_type', '8-dot')  # '6-dot' or '8-dot'
    add_separators = kwargs.get('add_separators', False)
    custom_mapping = kwargs.get('custom_mapping', False)
    
    result = []
    
    if braille_type == '6-dot':
        # 6-dot Braille: each byte maps to a 6-bit pattern (0-63)
        for byte_val in data:
            # Map 8-bit byte (0-255) to 6-bit pattern (0-63)
            # We'll use the lower 6 bits and store the upper 2 bits separately
            lower_6_bits = byte_val & 0x3F  # Get bits 0-5
            upper_2_bits = (byte_val >> 6) & 0x03  # Get bits 6-7
            
            # Create Braille character for lower 6 bits
            braille_char1 = chr(BRAILLE_OFFSET + lower_6_bits)
            
            # Create Braille character for upper 2 bits (stored in dots 1-2)
            braille_char2 = chr(BRAILLE_OFFSET + upper_2_bits)
            
            if custom_mapping:
                # Custom mapping: use mathematical transformation
                mapped_val1 = (lower_6_bits * 7 + 13) % 64
                mapped_val2 = (upper_2_bits * 11 + 5) % 4
                braille_char1 = chr(BRAILLE_OFFSET + mapped_val1)
                braille_char2 = chr(BRAILLE_OFFSET + mapped_val2)
            
            result.append(braille_char1 + braille_char2)
            
            if add_separators:
                result.append(' ')
                
    else:  # 8-dot Braille
        # 8-dot Braille: each byte directly maps to an 8-bit pattern (0-255)
        for byte_val in data:
            if custom_mapping:
                # Custom mapping: use mathematical transformation
                mapped_val = (byte_val * 17 + 29) % 256
                braille_char = chr(BRAILLE_OFFSET + mapped_val)
            else:
                braille_char = chr(BRAILLE_OFFSET + byte_val)
            
            result.append(braille_char)
            
            if add_separators:
                result.append(' ')
    
    return ''.join(result)

def decode(text: str, encoding: str = "utf-8", **kwargs) -> bytes:
    """
    Decode Braille-encoded data back to original bytes.
    
    Args:
        text: The Braille-encoded text
        encoding: String encoding for input (default: utf-8)
        **kwargs: Additional options (must match encoding options)
    
    Returns:
        The original bytes data
    """
    if not text.strip():
        return b""
    
    # Get options from kwargs (must match those used in encoding)
    braille_type = kwargs.get('braille_type', '8-dot')
    add_separators = kwargs.get('add_separators', False)
    custom_mapping = kwargs.get('custom_mapping', False)
    
    # Remove separators if they were added
    if add_separators:
        text = text.replace(' ', '')
    
    result = bytearray()
    
    if braille_type == '6-dot':
        # 6-dot Braille: process in pairs of characters
        i = 0
        while i < len(text):
            if i + 1 < len(text):
                # Get two Braille characters
                char1 = text[i]
                char2 = text[i + 1]
                
                # Convert to dot patterns
                pattern1 = ord(char1) - BRAILLE_OFFSET
                pattern2 = ord(char2) - BRAILLE_OFFSET
                
                # Validate patterns
                if pattern1 < 0 or pattern1 > 63 or pattern2 < 0 or pattern2 > 3:
                    i += 1
                    continue
                
                if custom_mapping:
                    # Reverse custom mapping
                    # Find original values by trying all possibilities
                    original_lower = None
                    original_upper = None
                    
                    for test_val in range(64):
                        if (test_val * 7 + 13) % 64 == pattern1:
                            original_lower = test_val
                            break
                    
                    for test_val in range(4):
                        if (test_val * 11 + 5) % 4 == pattern2:
                            original_upper = test_val
                            break
                    
                    if original_lower is not None and original_upper is not None:
                        # Reconstruct original byte
                        byte_val = original_lower | (original_upper << 6)
                        result.append(byte_val)
                else:
                    # Reconstruct original byte from patterns
                    byte_val = pattern1 | (pattern2 << 6)
                    result.append(byte_val)
                
                i += 2
            else:
                i += 1
                
    else:  # 8-dot Braille
        # 8-dot Braille: each character is one byte
        for char in text:
            if ord(char) >= BRAILLE_OFFSET:
                pattern = ord(char) - BRAILLE_OFFSET
                
                if pattern > 255:
                    continue
                
                if custom_mapping:
                    # Reverse custom mapping
                    # Find original value by trying all possibilities
                    original_val = None
                    for test_val in range(256):
                        if (test_val * 17 + 29) % 256 == pattern:
                            original_val = test_val
                            break
                    
                    if original_val is not None:
                        result.append(original_val)
                else:
                    result.append(pattern)
    
    return bytes(result)

def get_info():
    """Return information about Braille mode"""
    return {
        "name": "Braille",
        "description": "Encode data using Braille patterns",
        "supports_key": False,
        "supports_encoding": False,  # No need for string encoding as always outputs Unicode Braille
        "file_extension": ".txt"
    }

def get_options():
    """
    Return available options for Braille encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "braille_type": {
            "description": "Type of Braille system to use",
            "type": "choice",
            "choices": ["6-dot", "8-dot"],
            "default": "8-dot",
            "required": True,
            "note": "6-dot: Traditional Braille (each byte = 2 chars). 8-dot: Modern Braille (each byte = 1 char). 8-dot is more compact."
        },
        "add_separators": {
            "description": "Add spaces between Braille characters for readability",
            "type": "bool",
            "default": False,
            "required": False,
            "note": "Makes output more readable but increases file size. Required for decoding if used during encoding."
        },
        "custom_mapping": {
            "description": "Use custom mathematical mapping for additional obfuscation",
            "type": "bool",
            "default": False,
            "required": False,
            "note": "Applies mathematical transformation to Braille patterns. Makes output less recognizable as direct byte mapping."
        }
    }
