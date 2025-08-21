# src/sudoku_mode.py
import random
import math
import base64
import hashlib

# Default seed for Sudoku grid generation
DEFAULT_SEED = 12345

def _encode_metadata(grid_seed: str, shuffle_key: str) -> str:
    """
    Encode metadata (seed and shuffle key) to hide sensitive information
    
    Args:
        grid_seed: Seed for Sudoku grid generation
        shuffle_key: Key for shuffling position mappings
    
    Returns:
        Encoded metadata string
    """
    # Create the metadata string
    metadata = f"{grid_seed}:{shuffle_key}"
    
    # Use a simple XOR cipher with a fixed key derived from both seed and shuffle
    # This provides basic obfuscation while still being deterministic for decoding
    cipher_key = f"SUDOKU_{grid_seed}_{shuffle_key}_META"
    cipher_hash = hashlib.md5(cipher_key.encode()).hexdigest()
    
    # XOR the metadata with the hash
    encoded_bytes = []
    for i, char in enumerate(metadata):
        key_char = cipher_hash[i % len(cipher_hash)]
        encoded_bytes.append(ord(char) ^ ord(key_char))
    
    # Convert to base64 for safe text representation
    encoded_data = base64.b64encode(bytes(encoded_bytes)).decode('ascii')
    
    return f"SUD:{encoded_data}"

def _decode_metadata(encoded_metadata: str) -> tuple:
    """
    Decode metadata to extract grid_seed and shuffle_key
    
    Args:
        encoded_metadata: Encoded metadata string
    
    Returns:
        Tuple of (grid_seed, shuffle_key)
    """
    if not encoded_metadata.startswith("SUD:"):
        raise ValueError("Invalid metadata format")
    
    # Extract the base64 encoded data
    encoded_data = encoded_metadata[4:]  # Remove "SUD:" prefix
    
    try:
        # Decode from base64
        encoded_bytes = base64.b64decode(encoded_data.encode('ascii'))
        
        # We need to try different combinations to decode since we don't know the original keys
        # This is a limitation of this approach, but for now we'll use a brute force method
        # with common patterns or expect the keys to be provided during decode
        
        # For now, return empty strings - the decode function will handle this
        return "", ""
        
    except Exception:
        raise ValueError("Failed to decode metadata")

def _decode_metadata_with_keys(encoded_metadata: str, grid_seed: str, shuffle_key: str) -> bool:
    """
    Verify if the provided keys match the encoded metadata
    
    Args:
        encoded_metadata: Encoded metadata string  
        grid_seed: Proposed grid seed
        shuffle_key: Proposed shuffle key
    
    Returns:
        True if keys match, False otherwise
    """
    if not encoded_metadata.startswith("SUD:"):
        return False
        
    try:
        # Extract the base64 encoded data
        encoded_data = encoded_metadata[4:]  # Remove "SUD:" prefix
        encoded_bytes = base64.b64decode(encoded_data.encode('ascii'))
        
        # Reconstruct the cipher key
        cipher_key = f"SUDOKU_{grid_seed}_{shuffle_key}_META"
        cipher_hash = hashlib.md5(cipher_key.encode()).hexdigest()
        
        # Decode the metadata
        decoded_chars = []
        for i, byte_val in enumerate(encoded_bytes):
            key_char = cipher_hash[i % len(cipher_hash)]
            decoded_chars.append(chr(byte_val ^ ord(key_char)))
        
        decoded_metadata = ''.join(decoded_chars)
        expected_metadata = f"{grid_seed}:{shuffle_key}"
        
        return decoded_metadata == expected_metadata
        
    except Exception:
        return False

def generate_sudoku_grid(seed=None):
    """
    Generate a valid 9x9 Sudoku grid
    
    Args:
        seed: Random seed for reproducible grids (optional)
    
    Returns:
        9x9 grid as list of lists with numbers 1-9
    """
    # Store current random state to restore later
    original_state = None
    if seed is not None:
        original_state = random.getstate()
        random.seed(seed)
    
    # Start with empty grid
    grid = [[0 for _ in range(9)] for _ in range(9)]
    
    # Fill diagonal 3x3 boxes first (they don't interfere with each other)
    fill_diagonal_boxes(grid)
    
    # Fill remaining cells
    solve_sudoku(grid)
    
    # Restore original random state if we set a seed
    if seed is not None and original_state is not None:
        random.setstate(original_state)
    
    return grid

def fill_diagonal_boxes(grid):
    """Fill the 3 diagonal 3x3 boxes"""
    for box in range(0, 9, 3):
        fill_3x3_box(grid, box, box)

def fill_3x3_box(grid, row, col):
    """Fill a 3x3 box with random valid numbers"""
    nums = list(range(1, 10))
    random.shuffle(nums)
    
    for i in range(3):
        for j in range(3):
            grid[row + i][col + j] = nums[i * 3 + j]

def is_safe(grid, row, col, num):
    """Check if placing num at (row, col) is valid"""
    # Check row
    for x in range(9):
        if grid[row][x] == num:
            return False
    
    # Check column
    for x in range(9):
        if grid[x][col] == num:
            return False
    
    # Check 3x3 box
    start_row = row - row % 3
    start_col = col - col % 3
    for i in range(3):
        for j in range(3):
            if grid[i + start_row][j + start_col] == num:
                return False
    
    return True

def solve_sudoku(grid):
    """Solve Sudoku using backtracking"""
    for row in range(9):
        for col in range(9):
            if grid[row][col] == 0:
                nums = list(range(1, 10))
                # Use random shuffle but make sure it's using the current seeded state
                random.shuffle(nums)
                for num in nums:
                    if is_safe(grid, row, col, num):
                        grid[row][col] = num
                        if solve_sudoku(grid):
                            return True
                        grid[row][col] = 0
                return False
    return True

def create_sudoku_mapping(grid, shuffle_key=None):
    """
    Create bidirectional mapping between bytes and Sudoku positions
    
    Args:
        grid: 9x9 Sudoku grid
        shuffle_key: Key to shuffle position order (optional)
    
    Returns:
        Tuple of (byte_to_position, position_to_byte) dictionaries
    """
    positions = []
    
    # Create all possible positions with their values
    for row in range(9):
        for col in range(9):
            positions.append((row, col, grid[row][col]))
    
    # We have 81 positions but need 256 mappings for all byte values
    # Create a sequence that cycles through positions with variations
    extended_positions = []
    for i in range(256):
        pos_index = i % 81  # Cycle through the 81 positions
        row, col, value = positions[pos_index]
        # Add a sequence number to distinguish between cycles
        sequence_num = i // 81  # Which cycle we're in (0, 1, 2)
        extended_positions.append((row, col, value, sequence_num))
    
    # Shuffle if key provided
    if shuffle_key and shuffle_key.strip():
        import random
        # Store current random state
        current_state = random.getstate()
        
        # Set seed and shuffle
        seed = sum(ord(c) for c in shuffle_key)
        random.seed(seed)
        random.shuffle(extended_positions)
        
        # Restore previous random state
        random.setstate(current_state)
    
    # Create bidirectional mapping
    byte_to_position = {}
    position_to_byte = {}
    
    for i in range(256):
        pos = extended_positions[i]
        byte_to_position[i] = pos
        # For reverse mapping, map the position+sequence to the byte value
        if pos not in position_to_byte:
            position_to_byte[pos] = i
        # If there's a collision, the later one overwrites (this shouldn't happen with sequence numbers)
    
    return byte_to_position, position_to_byte

def encode(data: bytes, encoding: str = "utf-8", grid_seed: str = "", shuffle_key: str = "", format_style: str = "compact") -> str:
    """
    Encode data using Sudoku grid positions
    
    Args:
        data: Bytes data to encode
        encoding: String encoding (compatibility parameter)
        grid_seed: Seed for Sudoku grid generation 
        shuffle_key: Key to shuffle position mappings
        format_style: Output format style ('compact', 'readable', 'grid')
    
    Returns:
        Encoded string representation
    """
    if not data:
        return ""
    
    # Validate grid_seed - now required
    if not grid_seed or not grid_seed.strip():
        raise ValueError(f"Grid seed is required for Sudoku mode. Please provide a seed value (e.g., '{DEFAULT_SEED}').")
    
    # Generate Sudoku grid
    seed = None
    if isinstance(grid_seed, str):
        # Try to convert string seed to integer first (for numeric strings like "12345")
        try:
            seed = int(grid_seed.strip())
        except ValueError:
            # If not numeric, use ASCII sum as fallback
            seed = sum(ord(c) for c in grid_seed.strip())
    elif isinstance(grid_seed, int):
        seed = grid_seed
    else:
        raise ValueError("Grid seed must be a string or integer.")
    
    grid = generate_sudoku_grid(seed)
    
    # Create byte to position mapping
    byte_to_position, position_to_byte = create_sudoku_mapping(grid, shuffle_key)
    
    # Encode each byte: only store position info with sequence number
    encoded_positions = []
    for i, byte_val in enumerate(data):
        row, col, value, sequence = byte_to_position[byte_val]
        # Store: position info + sequence + index for ordering
        encoded_positions.append((row, col, value, sequence, i))
    
    # Format output based on style
    if format_style == "compact":
        # Format: ENCODED_METADATA|r,c,v,s,i|r,c,v,s,i|... 
        metadata = _encode_metadata(str(grid_seed), shuffle_key if shuffle_key else '')
        result = metadata + "|" + "|".join([f"{r},{c},{v},{s},{i}" for r, c, v, s, i in encoded_positions])
    elif format_style == "readable":
        # Format: ENCODED_METADATA\nR1C1V5S0I0 R2C3V7S1I1 ...
        metadata = _encode_metadata(str(grid_seed), shuffle_key if shuffle_key else '')
        result = metadata + "\n" + " ".join([f"R{r+1}C{c+1}V{v}S{s}I{i}" for r, c, v, s, i in encoded_positions])
    elif format_style == "grid":
        # Include encoded metadata, full grid + positions
        metadata = _encode_metadata(str(grid_seed), shuffle_key if shuffle_key else '') + "\n"
        grid_str = "GRID:\n"
        for row in grid:
            grid_str += " ".join(map(str, row)) + "\n"
        
        positions_str = "POSITIONS:\n"
        for r, c, v, s, i in encoded_positions:
            positions_str += f"Byte{i}: ({r+1},{c+1})={v}S{s}\n"
        
        result = metadata + grid_str + "\n" + positions_str
    else:
        # Default to compact with encoded metadata
        metadata = _encode_metadata(str(grid_seed), shuffle_key if shuffle_key else '')
        result = metadata + "|" + "|".join([f"{r},{c},{v},{s},{i}" for r, c, v, s, i in encoded_positions])
    
    return result

def decode(text: str, encoding: str = "utf-8", grid_seed: str = "", shuffle_key: str = "", format_style: str = "") -> bytes:
    """
    Decode Sudoku encoded data back to original bytes
    
    Args:
        text: Encoded text to decode
        encoding: String encoding (compatibility parameter)  
        grid_seed: Seed used for original Sudoku grid
        shuffle_key: Key used for position shuffling
        format_style: Format style used for encoding (auto-detected if empty)
    
    Returns:
        Original bytes data
    """
    if not text or not text.strip():
        return b""
    
    # Extract metadata if present
    extracted_grid_seed = grid_seed
    extracted_shuffle_key = shuffle_key
    content = text.strip()
    
    # Check for encoded metadata in different formats
    metadata_found = False
    if content.startswith("SUD:"):
        # New encoded metadata format: SUD:base64_data|content or SUD:base64_data\ncontent
        if "|" in content:
            metadata_part, content = content.split("|", 1)
        elif "\n" in content:
            metadata_part, content = content.split("\n", 1)
        else:
            metadata_part = content
            content = ""
            
        # For encoded metadata, we need the keys to decode - they should be provided
        # We'll validate the keys match the encoded metadata
        if grid_seed and shuffle_key is not None:  # shuffle_key can be empty string
            if _decode_metadata_with_keys(metadata_part, str(grid_seed), shuffle_key):
                extracted_grid_seed = str(grid_seed)
                extracted_shuffle_key = shuffle_key
                metadata_found = True
            else:
                raise ValueError("Invalid grid_seed or shuffle_key - metadata verification failed")
        else:
            raise ValueError("Grid seed and shuffle key are required for decoding encoded metadata")
            
    elif content.startswith("SUDOKU:"):
        # Legacy plain text metadata format: SUDOKU:grid_seed:shuffle_key|data...
        if "|" in content:
            metadata_part, content = content.split("|", 1)
        elif "\n" in content:
            metadata_part, content = content.split("\n", 1)
        else:
            metadata_part = content
            content = ""
            
        # Parse legacy metadata: SUDOKU:grid_seed:shuffle_key
        parts = metadata_part.split(":")
        if len(parts) >= 3:
            extracted_grid_seed = parts[1] if parts[1] else grid_seed
            extracted_shuffle_key = parts[2] if parts[2] else shuffle_key
            metadata_found = True
    
    # Use extracted metadata if original parameters are empty
    if not grid_seed and extracted_grid_seed:
        grid_seed = extracted_grid_seed
    if shuffle_key is None and extracted_shuffle_key:  # Handle None vs empty string
        shuffle_key = extracted_shuffle_key
        
    # Validate grid_seed - now required for decode as well
    if not grid_seed or not grid_seed.strip():
        if metadata_found:
            raise ValueError("Grid seed is required for Sudoku decode. The file contains encoded metadata but no valid seed was provided.")
        else:
            raise ValueError("Grid seed is required for Sudoku decode. Please provide the same seed used for encoding.")
        
    # Auto-detect format if not specified
    if not format_style:
        text_check = content.strip()
        if "GRID:" in text_check and "POSITIONS:" in text_check:
            format_style = "grid"
        elif text_check.startswith("R") and "C" in text_check and "V" in text_check and "S" in text_check and "I" in text_check:
            format_style = "readable" 
        elif text_check.startswith("R") and "C" in text_check and "V" in text_check and "B" in text_check and "I" in text_check:
            format_style = "readable_old"  # Old format with B (byte value)
        elif "|" in text_check and "," in text_check:
            format_style = "compact"
        else:
            format_style = "compact"  # Default fallback
    
    # Parse encoded positions based on format
    positions = []
    is_old_format = False
    
    if format_style == "grid":
        # Extract positions from grid format
        lines = content.strip().split('\n')
        in_positions = False
        for line in lines:
            if line.startswith("POSITIONS:"):
                in_positions = True
                continue
            if in_positions and ":" in line and "(" in line:
                try:
                    # Check for old format: Byte0: (9,1)=2 -> 72
                    if " -> " in line:
                        # Old format - extract byte value directly
                        is_old_format = True
                        idx_str = line.split(": (")[0].replace("Byte", "")
                        idx = int(idx_str)
                        byte_val = int(line.split(" -> ")[1])
                        positions.append((0, 0, 0, 0, idx, byte_val))  # (row,col,value,seq,idx,byte)
                    else:
                        # New format: Byte0: (9,1)=2S0
                        idx_str = line.split(": (")[0].replace("Byte", "")
                        idx = int(idx_str)
                        
                        # Extract position, value, and sequence
                        pos_val_part = line.split(": (")[1]  # Get "(9,1)=2S0"
                        pos_part = pos_val_part.split(")=")[0]  # Get "9,1"
                        val_seq_part = pos_val_part.split(")=")[1]  # Get "2S0"
                        
                        row, col = map(int, pos_part.split(","))
                        
                        if "S" in val_seq_part:
                            value = int(val_seq_part.split("S")[0])
                            sequence = int(val_seq_part.split("S")[1])
                        else:
                            value = int(val_seq_part)
                            sequence = 0  # Default sequence for backward compatibility
                        
                        positions.append((row-1, col-1, value, sequence, idx))  # Convert to 0-based indexing
                except Exception as e:
                    print(f"Error parsing grid line: {line} - {e}")
                    continue
                    
    elif format_style == "readable_old":
        # Parse old readable format: R1C1V5B72I0 R2C3V7B101I1 ...
        is_old_format = True
        parts = content.strip().split()
        for part in parts:
            try:
                if part.startswith("R") and "C" in part and "V" in part and "B" in part and "I" in part:
                    # Extract R1C1V5B72I0
                    b_i_part = part.split("B")[1]  # Get "72I0"
                    b_part = b_i_part.split("I")[0]  # Get byte value
                    i_part = b_i_part.split("I")[1]  # Get index
                    
                    byte_val = int(b_part)
                    idx = int(i_part)
                    positions.append((0, 0, 0, 0, idx, byte_val))  # (row,col,value,seq,idx,byte)
            except:
                continue
                
    elif format_style == "readable":
        # Parse new readable format: R1C1V5S0I0 R2C3V7S1I1 ...
        parts = content.strip().split()
        for part in parts:
            try:
                if part.startswith("R") and "C" in part and "V" in part and "I" in part:
                    # Extract R1C1V5S0I0
                    r_part = part[1:].split("C")[0]  # Get row number
                    c_v_s_i_part = part.split("C")[1]  # Get "1V5S0I0"
                    c_part = c_v_s_i_part.split("V")[0]  # Get col number
                    v_s_i_part = c_v_s_i_part.split("V")[1]  # Get "5S0I0"
                    
                    if "S" in v_s_i_part:
                        v_part = v_s_i_part.split("S")[0]  # Get value
                        s_i_part = v_s_i_part.split("S")[1]  # Get "0I0"
                        s_part = s_i_part.split("I")[0]  # Get sequence
                        i_part = s_i_part.split("I")[1]  # Get index
                        sequence = int(s_part)
                    else:
                        # Backward compatibility - no sequence number
                        v_part = v_s_i_part.split("I")[0]  # Get value
                        i_part = v_s_i_part.split("I")[1]  # Get index
                        sequence = 0
                    
                    row = int(r_part) - 1  # Convert to 0-based
                    col = int(c_part) - 1  # Convert to 0-based
                    value = int(v_part)
                    idx = int(i_part)
                    positions.append((row, col, value, sequence, idx))
            except:
                continue
    else:
        # Default compact format: r,c,v,s,i|r,c,v,s,i|... or old r,c,v,b,i|r,c,v,b,i|...
        parts = content.strip().split("|")
        for part in parts:
            try:
                if "," in part:
                    coords = part.split(",")
                    if len(coords) == 5:
                        # Check if this is old format (has byte values)
                        # In old format, the 4th element (coords[3]) would be a byte value (0-255)
                        # In new format, the 4th element would be a sequence (0-2, but could be higher with shuffle)
                        # Better heuristic: if 4th value is very high (>81), it's likely old format
                        fourth_val = int(coords[3])
                        if fourth_val > 81:  # Likely a byte value, so this is old format
                            is_old_format = True
                            row, col, value, byte_val, idx = map(int, coords)
                            positions.append((row, col, value, 0, idx, byte_val))  # (row,col,value,seq,idx,byte)
                        else:
                            # New format
                            row, col, value, sequence, idx = map(int, coords)
                            positions.append((row, col, value, sequence, idx))
                    elif len(coords) == 4:
                        # Backward compatibility - no sequence number
                        row, col, value, idx = map(int, coords)
                        positions.append((row, col, value, 0, idx))
            except:
                continue
    
    if not positions:
        raise ValueError("No valid positions found in encoded text")
    
    # Sort positions by index to restore original order
    if is_old_format:
        positions.sort(key=lambda x: x[4])  # Sort by index (5th element)
        
        # For old format, we can directly extract byte values
        result = bytearray()
        for pos in positions:
            if len(pos) >= 6:  # Has byte value
                result.append(pos[5])  # byte value is at index 5
            else:
                result.append(0)  # Fallback
        
        return bytes(result)
    else:
        positions.sort(key=lambda x: x[4])  # Sort by index (5th element)
        
    # Now we need to recreate the original grid and mapping to decode positions back to bytes
    # Generate the same Sudoku grid using the same seed
    seed = None
    if isinstance(grid_seed, str):
        # Try to convert string seed to integer first (for numeric strings like "12345")
        try:
            seed = int(grid_seed.strip())
        except ValueError:
            # If not numeric, use ASCII sum as fallback
            seed = sum(ord(c) for c in grid_seed.strip())
    elif isinstance(grid_seed, int):
        seed = grid_seed
    else:
        raise ValueError("Grid seed must be a string or integer.")
    
    grid = generate_sudoku_grid(seed)
    
    # Create the same byte to position mapping using the same shuffle key
    byte_to_position, position_to_byte = create_sudoku_mapping(grid, shuffle_key)
    
    # Convert positions back to bytes
    result = bytearray()
    for row, col, value, sequence, idx in positions:
        position_tuple = (row, col, value, sequence)
        if position_tuple in position_to_byte:
            byte_val = position_to_byte[position_tuple]
            result.append(byte_val)
        else:
            raise ValueError(f"Invalid position ({row}, {col}, {value}, seq={sequence}) not found in mapping. Wrong grid_seed or shuffle_key?")
    
    return bytes(result)

def get_info():
    """Return information about Sudoku mode"""
    return {
        "name": "Sudoku",
        "description": "Encode data using Sudoku grid positions and values",
        "supports_key": False,  # Uses custom keys, not XOR encryption
        "supports_encoding": False,  # Output format is always position-based
        "file_extension": ".txt"
    }

def get_options():
    """
    Return available options for Sudoku encoding.
    
    Returns:
        Dictionary of options for both encoding and decoding
    """
    return {
        "grid_seed": {
            "description": "Seed for Sudoku grid generation",
            "type": "str", 
            "default": str(DEFAULT_SEED),
            "required": True,  # Now required - cannot be empty
            "example": "myseed123, puzzle1, secret",
            "note": f"Controls Sudoku grid layout. Same seed = same grid. Default = {DEFAULT_SEED}. REQUIRED.",
            "decode_required": True  # Needed for both encode and decode
        },
        "shuffle_key": {
            "description": "Key to shuffle position mappings", 
            "type": "str",
            "default": "",
            "required": False,
            "example": "shuffle123, randomize, mykey",
            "note": "Randomizes byte-to-position mapping. DIFFERENT from XOR encryption.",
            "placeholder": "optional",
            "decode_required": True  # Needed for both encode and decode
        },
        "format_style": {
            "description": "Output format style",
            "type": "choice",
            "choices": ["compact", "readable", "grid"],
            "default": "compact", 
            "required": False,
            "note": "Compact: r,c,v|r,c,v | Readable: R1C1V5 R2C3V7 | Grid: Full grid + positions",
            "decode_required": True  # Format must match for decoding
        }
    }
