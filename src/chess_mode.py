# src/chess_mode.py
import random
import math

# Default FEN position for standard chess starting position
DEFAULT_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Chess piece mappings
PIECES = {
    'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',  # Black pieces
    'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',  # White pieces
    '.': '·'   # Empty square
}

def fen_to_board(fen):
    """
    Convert FEN notation to 8x8 board representation
    
    Args:
        fen: FEN notation string (can be full FEN or just board part)
    
    Returns:
        8x8 board as list of lists with piece characters
    """
    # Extract just the board part from FEN (before first space)
    board_fen = fen.split()[0] if ' ' in fen else fen
    
    board = []
    rows = board_fen.split('/')
    
    if len(rows) != 8:
        raise ValueError("Invalid FEN: must have 8 rows")
    
    for row_fen in rows:
        row = []
        for char in row_fen:
            if char.isdigit():
                # Empty squares
                empty_count = int(char)
                row.extend(['.'] * empty_count)
            else:
                # Piece
                row.append(char)
        
        if len(row) != 8:
            raise ValueError(f"Invalid FEN row: must have 8 squares, got {len(row)}")
        
        board.append(row)
    
    return board

def board_to_fen(board, additional_info="w KQkq - 0 1"):
    """
    Convert 8x8 board to FEN notation
    
    Args:
        board: 8x8 board as list of lists
        additional_info: Additional FEN info (castling, en passant, etc.)
    
    Returns:
        FEN notation string
    """
    fen_rows = []
    
    for row in board:
        fen_row = ""
        empty_count = 0
        
        for piece in row:
            if piece == '.':
                empty_count += 1
            else:
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                fen_row += piece
        
        if empty_count > 0:
            fen_row += str(empty_count)
        
        fen_rows.append(fen_row)
    
    board_fen = "/".join(fen_rows)
    return f"{board_fen} {additional_info}"

def create_chess_mapping(board, shuffle_key=None):
    """
    Create bidirectional mapping between bytes and chess positions
    
    Args:
        board: 8x8 chess board
        shuffle_key: Key to shuffle position order (optional)
    
    Returns:
        Tuple of (byte_to_position, position_to_byte) dictionaries
    """
    positions = []
    
    # Create all possible positions with their pieces
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            positions.append((row, col, piece))
    
    # We have 64 positions but need 256 mappings for all byte values
    # Create a sequence that cycles through positions with variations
    extended_positions = []
    for i in range(256):
        pos_index = i % 64  # Cycle through the 64 positions
        row, col, piece = positions[pos_index]
        # Add a sequence number to distinguish between cycles
        sequence_num = i // 64  # Which cycle we're in (0, 1, 2, 3)
        extended_positions.append((row, col, piece, sequence_num))
    
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
    
    return byte_to_position, position_to_byte

def encode(data: bytes, encoding: str = "utf-8", chess_fen: str = "", shuffle_key: str = "", format_style: str = "compact") -> str:
    """
    Encode data using chess board positions and pieces
    
    Args:
        data: Bytes data to encode
        encoding: String encoding (compatibility parameter)
        chess_fen: FEN notation for chess position
        shuffle_key: Key to shuffle position mappings
        format_style: Output format style ('compact', 'readable', 'board')
    
    Returns:
        Encoded string representation
    """
    if not data:
        return ""
    
    # Validate chess_fen - now required
    if not chess_fen or not chess_fen.strip():
        raise ValueError(f"Chess FEN is required for Chess mode. Please provide a FEN position (e.g., '{DEFAULT_FEN}').")
    
    # Convert FEN to board
    try:
        board = fen_to_board(chess_fen.strip())
    except Exception as e:
        raise ValueError(f"Invalid FEN notation: {e}")
    
    # Extract FEN metadata for preservation
    fen_parts = chess_fen.strip().split()
    if len(fen_parts) >= 6:
        # Full FEN with metadata
        fen_metadata = " ".join(fen_parts[1:])  # Everything after board position
    else:
        # Incomplete FEN, use defaults
        fen_metadata = "w KQkq - 0 1"
    
    # Create byte to position mapping
    byte_to_position, position_to_byte = create_chess_mapping(board, shuffle_key)
    
    # Encode each byte: store position info with sequence number
    encoded_positions = []
    for i, byte_val in enumerate(data):
        row, col, piece, sequence = byte_to_position[byte_val]
        # Store: position info + sequence + index for ordering
        encoded_positions.append((row, col, piece, sequence, i))
    
    # Format output based on style
    if format_style == "compact":
        # Format: FEN_LINE + r,c,p,s,i|r,c,p,s,i|... (row,col,piece,sequence,index)
        fen_line = f"FEN: {board_to_fen(board, fen_metadata)}"
        positions_line = "|".join([f"{r},{c},{p},{s},{i}" for r, c, p, s, i in encoded_positions])
        result = f"{fen_line}\n{positions_line}"
    elif format_style == "readable":
        # Format: R1C1PR0I0 R2C3Pq1I1 ... (where P is piece, R/C are rank/file)
        result = " ".join([f"R{r+1}C{c+1}P{p}S{s}I{i}" for r, c, p, s, i in encoded_positions])
    elif format_style == "board":
        # Include full board + positions
        board_str = "BOARD:\n"
        for row in board:
            board_str += " ".join([PIECES.get(piece, piece) for piece in row]) + "\n"
        
        fen_str = f"FEN: {board_to_fen(board, fen_metadata)}\n"
        
        positions_str = "POSITIONS:\n"
        for r, c, p, s, i in encoded_positions:
            square_name = chr(ord('a') + c) + str(8 - r)  # Convert to chess notation (a1-h8)
            piece_symbol = PIECES.get(p, p)
            positions_str += f"Byte{i}: {square_name}={piece_symbol}S{s}\n"
        
        result = board_str + "\n" + fen_str + "\n" + positions_str
    else:
        # Default to compact
        fen_line = f"FEN: {board_to_fen(board, fen_metadata)}"
        positions_line = "|".join([f"{r},{c},{p},{s},{i}" for r, c, p, s, i in encoded_positions])
        result = f"{fen_line}\n{positions_line}"
    
    return result

def decode(text: str, encoding: str = "utf-8", chess_fen: str = "", shuffle_key: str = "", format_style: str = "") -> bytes:
    """
    Decode chess encoded data back to original bytes
    
    Args:
        text: Encoded text to decode
        encoding: String encoding (compatibility parameter)
        chess_fen: FEN notation used for original encoding
        shuffle_key: Key used for position shuffling
        format_style: Format style used for encoding (auto-detected if empty)
    
    Returns:
        Original bytes data
    """
    if not text or not text.strip():
        return b""
    
    # Auto-detect format if not specified
    if not format_style:
        text_check = text.strip()
        if "BOARD:" in text_check and "POSITIONS:" in text_check:
            format_style = "board"
        elif text_check.startswith("R") and "C" in text_check and "P" in text_check and "S" in text_check and "I" in text_check:
            format_style = "readable"
        elif "|" in text_check and "," in text_check:
            format_style = "compact"
        elif text_check.startswith("FEN:") and "|" in text_check:  # New compact format with FEN
            format_style = "compact"
        else:
            format_style = "compact"  # Default fallback
    
    # Parse encoded positions based on format
    positions = []
    
    if format_style == "board":
        # Extract positions from board format
        lines = text.strip().split('\n')
        in_positions = False
        for line in lines:
            if line.startswith("POSITIONS:"):
                in_positions = True
                continue
            if in_positions and ":" in line and "=" in line:
                try:
                    # Parse: Byte0: a1=♜S0
                    idx_str = line.split(": ")[0].replace("Byte", "")
                    idx = int(idx_str)
                    
                    # Extract square, piece, and sequence
                    square_piece_part = line.split(": ")[1]  # Get "a1=♜S0"
                    square_part = square_piece_part.split("=")[0]  # Get "a1"
                    piece_seq_part = square_piece_part.split("=")[1]  # Get "♜S0"
                    
                    # Convert chess notation to row/col (a1 -> row=7, col=0)
                    col = ord(square_part[0]) - ord('a')
                    row = 8 - int(square_part[1])
                    
                    if "S" in piece_seq_part:
                        piece_symbol = piece_seq_part.split("S")[0]
                        sequence = int(piece_seq_part.split("S")[1])
                    else:
                        piece_symbol = piece_seq_part
                        sequence = 0
                    
                    # Convert piece symbol back to character
                    piece = piece_symbol
                    for char, symbol in PIECES.items():
                        if symbol == piece_symbol:
                            piece = char
                            break
                    
                    positions.append((row, col, piece, sequence, idx))
                except Exception as e:
                    print(f"Error parsing board line: {line} - {e}")
                    continue
                    
    elif format_style == "readable":
        # Parse readable format: R1C1PR0I0 R2C3Pq1I1 ...
        parts = text.strip().split()
        for part in parts:
            try:
                if part.startswith("R") and "C" in part and "P" in part and "I" in part:
                    # Extract R1C1PR0I0
                    r_part = part[1:].split("C")[0]  # Get row number
                    c_p_s_i_part = part.split("C")[1]  # Get "1PR0I0"
                    c_part = c_p_s_i_part.split("P")[0]  # Get col number
                    p_s_i_part = c_p_s_i_part.split("P")[1]  # Get "R0I0"
                    
                    if "S" in p_s_i_part:
                        p_part = p_s_i_part.split("S")[0]  # Get piece
                        s_i_part = p_s_i_part.split("S")[1]  # Get "0I0"
                        s_part = s_i_part.split("I")[0]  # Get sequence
                        i_part = s_i_part.split("I")[1]  # Get index
                        sequence = int(s_part)
                    else:
                        # Backward compatibility - no sequence number
                        p_part = p_s_i_part.split("I")[0]  # Get piece
                        i_part = p_s_i_part.split("I")[1]  # Get index
                        sequence = 0
                    
                    row = int(r_part) - 1  # Convert to 0-based
                    col = int(c_part) - 1  # Convert to 0-based
                    piece = p_part
                    idx = int(i_part)
                    positions.append((row, col, piece, sequence, idx))
            except:
                continue
    else:
        # Default compact format: r,c,p,s,i|r,c,p,s,i|...
        # Can have FEN line at the beginning (new format)
        text_lines = text.strip().split('\n')
        
        # Check if first line is FEN
        if text_lines[0].startswith("FEN:"):
            # Skip FEN line, use positions line
            if len(text_lines) > 1:
                positions_text = text_lines[1]
            else:
                positions_text = ""
        else:
            # Old format without FEN line
            positions_text = text.strip()
        
        parts = positions_text.split("|") if positions_text else []
        for part in parts:
            try:
                if "," in part:
                    coords = part.split(",")
                    if len(coords) == 5:
                        row, col, piece, sequence, idx = coords[0], coords[1], coords[2], coords[3], coords[4]
                        positions.append((int(row), int(col), piece, int(sequence), int(idx)))
                    elif len(coords) == 4:
                        # Backward compatibility - no sequence number
                        row, col, piece, idx = coords
                        positions.append((int(row), int(col), piece, 0, int(idx)))
            except:
                continue
    
    if not positions:
        raise ValueError("No valid positions found in encoded text")
    
    # Sort positions by index to restore original order
    positions.sort(key=lambda x: x[4])  # Sort by index (5th element)
        
    # Validate chess_fen - now required for decode as well
    if not chess_fen or not chess_fen.strip():
        raise ValueError("Chess FEN is required for Chess decode. Please provide the same FEN used for encoding.")
        
    # Recreate the original board and mapping to decode positions back to bytes
    try:
        board = fen_to_board(chess_fen.strip())
    except Exception as e:
        raise ValueError(f"Invalid FEN notation: {e}")
    
    # Create the same byte to position mapping using the same shuffle key
    byte_to_position, position_to_byte = create_chess_mapping(board, shuffle_key)
    
    # Convert positions back to bytes
    result = bytearray()
    for row, col, piece, sequence, idx in positions:
        position_tuple = (row, col, piece, sequence)
        if position_tuple in position_to_byte:
            byte_val = position_to_byte[position_tuple]
            result.append(byte_val)
        else:
            raise ValueError(f"Invalid position ({row}, {col}, {piece}, seq={sequence}) not found in mapping. Wrong FEN or shuffle_key?")
    
    return bytes(result)

def get_info():
    """Return information about Chess mode"""
    return {
        "name": "Chess",
        "description": "Encode data using chess board positions and FEN notation",
        "supports_key": False,  # Uses custom keys, not XOR encryption
        "supports_encoding": False,  # Output format is always position-based
        "file_extension": ".txt"
    }

def get_options():
    """
    Return available options for Chess encoding.
    
    Returns:
        Dictionary of options for both encoding and decoding
    """
    return {
        "chess_fen": {
            "description": "FEN notation for chess position",
            "type": "str", 
            "default": DEFAULT_FEN,
            "required": True,
            "example": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1, r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1",
            "note": "Defines chess board layout. Same FEN = same board. REQUIRED.",
            "decode_required": True
        },
        "shuffle_key": {
            "description": "Key to shuffle position mappings", 
            "type": "str",
            "default": "",
            "required": False,
            "example": "shuffle123, randomize, mykey",
            "note": "Randomizes byte-to-position mapping. DIFFERENT from XOR encryption.",
            "placeholder": "optional",
            "decode_required": True
        },
        "format_style": {
            "description": "Output format style",
            "type": "choice",
            "choices": ["compact", "readable", "board"],
            "default": "compact", 
            "required": False,
            "note": "Compact: r,c,p|r,c,p | Readable: R1C1PR R2C3Pq | Board: Full board + positions",
            "decode_required": True
        }
    }
