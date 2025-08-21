# src/chess_viewer.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import re

class ToolTip:
    """Create tooltip for tkinter widgets"""
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)

    def on_enter(self, event=None):
        if self.text:
            self.show_tooltip()

    def on_leave(self, event=None):
        self.hide_tooltip()

    def show_tooltip(self):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("Arial", 9))
        label.pack()

    def hide_tooltip(self):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

    def update_text(self, new_text):
        self.text = new_text

class ChessViewer:
    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.board_data = None
        self.encoded_positions = []
        self.current_highlight = -1
        self.squares = []
        self.original_fen = None  # Store original FEN notation
        
        # Chess piece mappings
        self.pieces = {
            'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',  # Black pieces
            'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',  # White pieces
            '.': '·'   # Empty square
        }
        
        # Key repeat variables
        self.key_repeat_active = False
        self.key_repeat_direction = 0
        self.key_repeat_speed = 100
    
    def _validate_chess_board(self, board):
        """
        Validate if an 8x8 board has valid chess pieces
        
        Args:
            board: 8x8 list of lists with piece characters
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        if not board or len(board) != 8:
            return False, ["Board must be 8x8"]
        
        errors = []
        valid_pieces = set('rnbqkpRNBQKP.')
        
        # Check each row
        for i, row in enumerate(board):
            if len(row) != 8:
                errors.append(f"Row {i+1} has {len(row)} elements, should be 8")
                continue
                
            # Check for valid pieces
            for j, piece in enumerate(row):
                if piece not in valid_pieces:
                    errors.append(f"Row {i+1}, Col {j+1}: invalid piece '{piece}'")
        
        # Check for valid piece counts (basic validation)
        all_pieces = [piece for row in board for piece in row if piece != '.']
        piece_counts = {}
        for piece in all_pieces:
            piece_counts[piece] = piece_counts.get(piece, 0) + 1
        
        # Check for too many pieces (basic rule)
        max_pieces = {'p': 8, 'P': 8, 'r': 2, 'R': 2, 'n': 2, 'N': 2, 
                     'b': 2, 'B': 2, 'q': 1, 'Q': 1, 'k': 1, 'K': 1}
        
        for piece, count in piece_counts.items():
            if piece in max_pieces and count > max_pieces[piece]:
                errors.append(f"Too many {piece} pieces: {count} (max {max_pieces[piece]})")
        
        # Check for exactly one king of each color
        if piece_counts.get('k', 0) != 1:
            errors.append(f"Must have exactly 1 black king, found {piece_counts.get('k', 0)}")
        if piece_counts.get('K', 0) != 1:
            errors.append(f"Must have exactly 1 white king, found {piece_counts.get('K', 0)}")
        
        return len(errors) == 0, errors
        
    def show_chess_file(self, file_path):
        """
        Parse and display Chess file in a visual board
        
        Args:
            file_path: Path to the encoded Chess file
        """
        try:
            # Parse the Chess file
            self.board_data, self.encoded_positions = self._parse_chess_file(file_path)
            
            if self.board_data is None:
                messagebox.showerror("Error", "Could not parse Chess file format")
                return
                
            # Create and show viewer window
            self._create_viewer_window(file_path)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Chess viewer:\n{str(e)}")
    
    def _parse_chess_file(self, file_path):
        """Parse Chess file to extract board and positions"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            board_data = None
            encoded_positions = []
            
            if "BOARD:" in content and "POSITIONS:" in content:
                # Board format - extract both board and positions
                lines = content.split('\n')
                in_board = False
                in_positions = False
                board_lines = []
                
                for line in lines:
                    if line.startswith("BOARD:"):
                        in_board = True
                        in_positions = False
                        continue
                    elif line.startswith("FEN:"):
                        in_board = False
                        continue
                    elif line.startswith("POSITIONS:"):
                        in_board = False
                        in_positions = True
                        continue
                    elif line.strip() == "":
                        continue
                    
                    if in_board:
                        # Parse board line with chess pieces
                        board_lines.append(line.strip())
                    elif in_positions and ":" in line and "=" in line:
                        # Parse position line
                        try:
                            # Parse: Byte0: a1=♜S0
                            parts = line.split(": ")
                            if len(parts) >= 2:
                                byte_index = int(parts[0].replace("Byte", ""))
                                
                                # Parse square and piece info
                                square_piece = parts[1]
                                if "=" in square_piece:
                                    square_part = square_piece.split("=")[0]
                                    piece_seq_part = square_piece.split("=")[1]
                                    
                                    # Convert chess notation to row/col
                                    if len(square_part) >= 2:
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
                                        for char, symbol in self.pieces.items():
                                            if symbol == piece_symbol:
                                                piece = char
                                                break
                                        
                                        encoded_positions.append({
                                            'index': byte_index,
                                            'row': row,
                                            'col': col,
                                            'piece': piece,
                                            'sequence': sequence,
                                            'square': square_part,
                                            'symbol': piece_symbol
                                        })
                        except Exception as e:
                            print(f"Error parsing position line: {line} - {e}")
                
                # Convert board lines to 8x8 grid
                if board_lines:
                    board_data = []
                    for line in board_lines:
                        if line:
                            # Split by spaces and convert symbols back to characters
                            symbols = line.split()
                            row = []
                            for symbol in symbols:
                                piece = symbol
                                for char, sym in self.pieces.items():
                                    if sym == symbol:
                                        piece = char
                                        break
                                row.append(piece)
                            if len(row) == 8:
                                board_data.append(row)
                    
                    if len(board_data) != 8:
                        board_data = None
            
            else:
                # Parse compact format and other formats
                if "|" in content and "," in content:
                    # Compact format - check if it has FEN line (new format)
                    lines = content.strip().split('\n')
                    
                    if lines[0].startswith("FEN:"):
                        # New format with FEN
                        fen_line = lines[0].replace("FEN:", "").strip()
                        positions_line = lines[1] if len(lines) > 1 else ""
                        
                        # Store original FEN for copying
                        self.original_fen = fen_line
                        
                        # Parse FEN to create board
                        try:
                            board_data = self._fen_to_board(fen_line)
                        except Exception as e:
                            print(f"Error parsing FEN: {e}")
                            board_data = self._create_default_board()
                    else:
                        # Old format without FEN - use default board
                        board_data = self._create_default_board()
                        positions_line = content.strip()
                    
                    # Parse positions from compact format
                    parts = positions_line.split("|") if positions_line else []
                    for i, part in enumerate(parts):
                        try:
                            coords = part.split(",")
                            if len(coords) >= 5:  # Should have 5 elements: row,col,piece,sequence,index
                                row, col, piece = int(coords[0]), int(coords[1]), coords[2]
                                sequence, index = int(coords[3]), int(coords[4])
                                
                                square = chr(ord('a') + col) + str(8 - row)
                                symbol = self.pieces.get(piece, piece)
                                
                                encoded_positions.append({
                                    'index': index,  # Use actual index from file
                                    'row': row,
                                    'col': col,
                                    'piece': piece,
                                    'sequence': sequence,
                                    'square': square,
                                    'symbol': symbol
                                })
                        except Exception as e:
                            print(f"Error parsing compact position: {part} - {e}")
                            continue
                else:
                    # For readable format or other formats, return None to indicate 
                    # that chess viewer should not be used
                    return None, []
            
            # Sort positions by index
            encoded_positions.sort(key=lambda x: x['index'])
            
            return board_data, encoded_positions
            
        except Exception as e:
            print(f"Error parsing chess file: {e}")
            return None, []
    
    def _create_default_board(self):
        """Create a default chess starting position"""
        return [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ]
    
    def _fen_to_board(self, fen):
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
    
    def _create_viewer_window(self, file_path):
        """Create the chess viewer window"""
        if self.window:
            self.window.destroy()
        
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title(f"Chess Viewer - {os.path.basename(file_path)}")
        self.window.geometry("1200x600")
        self.window.resizable(True, True)
        
        # Center the window on screen
        self.window.update_idletasks()  # Update window to get accurate dimensions
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights - chess board on left, controls on right
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=0)  # Chess board - fixed width
        main_frame.columnconfigure(1, weight=1)  # Right panel - expandable
        main_frame.rowconfigure(0, weight=1)
        
        # Create chess board frame (left side)
        board_frame = ttk.LabelFrame(main_frame, text="Chess Board", padding="10")
        board_frame.grid(row=0, column=0, sticky=(tk.W, tk.N), padx=(0, 10))
        
        # Create board grid
        self._create_board_grid(board_frame)
        
        # Create right panel with scrollable content
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(right_panel, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid the canvas and scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure canvas column weight
        right_panel.columnconfigure(0, weight=1)
        
        # Create navigation controls in scrollable frame
        controls_frame = ttk.LabelFrame(scrollable_frame, text="Navigation", padding="10")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        controls_frame.columnconfigure(0, weight=1)
        
        # Create position info frame in scrollable frame
        info_frame = ttk.LabelFrame(scrollable_frame, text="Position Info", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        # Create statistics frame in scrollable frame
        stats_frame = ttk.LabelFrame(scrollable_frame, text="Statistics", padding="10")
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=(0, 10))
        stats_frame.columnconfigure(0, weight=1)
        
        # Configure scrollable_frame column weight
        scrollable_frame.columnconfigure(0, weight=1)
        
        # Create navigation controls
        self._create_navigation_controls(controls_frame)
        
        # Create info display
        self._create_info_display(info_frame)
        
        # Create statistics display
        self._create_statistics_display(stats_frame)
        
        # Bind mousewheel to canvas for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Set focus and key bindings
        self.window.focus_set()
        self._setup_key_bindings()
        
        # Update display
        self._update_board_display()
        self._update_info_display()
    
    def _create_board_grid(self, parent):
        """Create the 8x8 chess board grid"""
        self.squares = []
        
        # Create coordinate labels
        # File labels (a-h)
        for col in range(8):
            label = tk.Label(parent, text=chr(ord('a') + col), font=("Arial", 10, "bold"))
            label.grid(row=9, column=col+1, pady=2)
        
        # Rank labels (8-1)
        for row in range(8):
            label = tk.Label(parent, text=str(8-row), font=("Arial", 10, "bold"))
            label.grid(row=row+1, column=0, padx=2)
        
        # Create chess squares
        for row in range(8):
            square_row = []
            for col in range(8):
                # Determine square color (alternating)
                is_light = (row + col) % 2 == 0
                bg_color = "#F0D9B5" if is_light else "#B58863"  # Chess.com colors
                
                # Create square button
                square = tk.Button(
                    parent,
                    width=3,
                    height=1,
                    font=("Arial", 24),  # Reduced font size for better fit
                    bg=bg_color,
                    relief="raised",
                    bd=1,
                    command=lambda r=row, c=col: self._on_square_click(r, c)
                )
                square.grid(row=row+1, column=col+1, padx=1, pady=1)
                
                # Add piece if present
                if self.board_data and row < len(self.board_data) and col < len(self.board_data[row]):
                    piece = self.board_data[row][col]
                    # Don't show empty squares on the board
                    piece_text = '' if piece == '.' else self.pieces.get(piece, piece)
                    square.config(text=piece_text)
                
                square_row.append(square)
            self.squares.append(square_row)
    
    def _create_navigation_controls(self, parent):
        """Create navigation controls"""
        # Position navigation
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(nav_frame, text="First", command=self._go_to_first).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="Previous", command=self._go_to_previous).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="Next", command=self._go_to_next).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="Last", command=self._go_to_last).pack(side="left", padx=2)
        
        # Position counter
        self.position_label = ttk.Label(parent, text="Position: 0 / 0")
        self.position_label.pack(pady=5)
        
        # Board validation
        ttk.Button(parent, text="Validate Board", command=self._validate_board).pack(pady=5)
        
        # Export options
        export_frame = ttk.LabelFrame(parent, text="Export", padding="5")
        export_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(export_frame, text="Save as PNG", command=self._save_as_png).pack(side="left", padx=2)
        ttk.Button(export_frame, text="Copy FEN", command=self._copy_fen).pack(side="left", padx=2)
        ttk.Button(export_frame, text="Copy FEN Analysis", command=self._copy_fen_analysis).pack(side="left", padx=2)
    
    def _create_info_display(self, parent):
        """Create position info display"""
        # Create a frame for text and scrollbar
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # Current position info
        self.info_text = tk.Text(text_frame, height=12, wrap="word", font=("Consolas", 9), state="disabled")
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for info text
        info_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
    
    def _create_statistics_display(self, parent):
        """Create statistics display"""
        parent.columnconfigure(0, weight=1)
        
        # Create a text widget for better formatting and scrollability
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill="both", expand=True)
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        
        stats_text_widget = tk.Text(stats_frame, height=8, wrap="word", font=("Arial", 9), 
                                   relief="flat", bg='#f0f0f0')
        stats_text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for stats if needed
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=stats_text_widget.yview)
        stats_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        stats_text_widget.configure(yscrollcommand=stats_scrollbar.set)
        
        # Insert statistics content
        # Calculate board statistics
        occupied_squares = 0
        empty_squares = 0
        white_pieces = 0
        black_pieces = 0
        
        if self.board_data:
            for row in self.board_data:
                for piece in row:
                    if piece == '.':
                        empty_squares += 1
                    else:
                        occupied_squares += 1
                        if piece.isupper():
                            white_pieces += 1
                        else:
                            black_pieces += 1
        
        # Calculate encoding density
        total_positions = len(self.encoded_positions)
        density = (total_positions / 64) * 100 if total_positions > 0 else 0
        
        # FEN Analysis
        fen_analysis = self._analyze_fen() if self.original_fen else self._analyze_board_fen()
        
        stats_content = f"""Total positions: {total_positions}
Board size: 8x8 (64 squares)
File: {os.path.basename(self.window.title().split(' - ')[1]) if ' - ' in self.window.title() else 'Unknown'}

Board Statistics:
• Total squares: 64
• Occupied squares: {occupied_squares}
• Empty squares: {empty_squares}
• White pieces: {white_pieces}
• Black pieces: {black_pieces}
• Encoding density: {density:.1f}%

{fen_analysis}

Chess Piece Symbols:
♜♞♝♛♚♝♞♜ (Black pieces)
♟♟♟♟♟♟♟♟ (Black pawns)
♙♙♙♙♙♙♙♙ (White pawns)
♖♘♗♕♔♗♘♖ (White pieces)
· (Empty squares)

Navigation:
• Left/Right arrows: Navigate positions
• Home/End: First/Last position
• Space: Next position
• Backspace: Previous position
• Click on squares to jump to positions
        """
        
        stats_text_widget.insert("1.0", stats_content)
        stats_text_widget.config(state="disabled")  # Make read-only
    
    def _analyze_fen(self):
        """Analyze FEN notation and return formatted statistics"""
        if not self.original_fen:
            return "FEN Analysis: Not available"
        
        try:
            fen_parts = self.original_fen.split()
            if len(fen_parts) < 6:
                return "FEN Analysis: Incomplete FEN notation"
            
            board_fen = fen_parts[0]
            active_color = fen_parts[1]
            castling_rights = fen_parts[2]
            en_passant = fen_parts[3]
            halfmove_clock = fen_parts[4]
            fullmove_number = fen_parts[5]
            
            # Analyze active color
            active_player = "White" if active_color == 'w' else "Black"
            
            # Analyze castling rights
            castling_analysis = []
            if 'K' in castling_rights:
                castling_analysis.append("White kingside")
            if 'Q' in castling_rights:
                castling_analysis.append("White queenside")
            if 'k' in castling_rights:
                castling_analysis.append("Black kingside")
            if 'q' in castling_rights:
                castling_analysis.append("Black queenside")
            
            castling_text = ", ".join(castling_analysis) if castling_analysis else "None"
            
            # Analyze en passant
            en_passant_text = f"Square {en_passant}" if en_passant != '-' else "None"
            
            # Analyze game state
            moves_played = int(fullmove_number) - 1
            total_halfmoves = (moves_played * 2) + (0 if active_color == 'w' else 1)
            
            # Check for special positions
            position_type = self._analyze_position_type(board_fen)
            game_phase = self._determine_game_phase(int(fullmove_number), int(halfmove_clock))
            
            fen_analysis = f"""FEN Analysis:
• Active player: {active_player}
• Castling rights: {castling_text}
• En passant target: {en_passant_text}
• Halfmove clock: {halfmove_clock} (moves since last pawn move/capture)
• Full moves: {fullmove_number} (game moves completed)
• Total half-moves: {total_halfmoves}
• Game phase: {game_phase}
• Position type: {position_type}
• FEN: {self.original_fen}"""
            
            return fen_analysis
            
        except Exception as e:
            return f"FEN Analysis: Error parsing FEN - {str(e)}"
    
    def _analyze_board_fen(self):
        """Generate FEN analysis from current board state"""
        if not self.board_data:
            return "FEN Analysis: No board data available"
        
        try:
            # Convert board to FEN
            fen_rows = []
            for row in self.board_data:
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
            full_fen = f"{board_fen} w KQkq - 0 1"  # Default metadata
            
            position_type = self._analyze_position_type(board_fen)
            
            fen_analysis = f"""FEN Analysis:
• Board FEN: {board_fen}
• Full FEN: {full_fen}
• Position type: {position_type}
• Active player: White (default)
• Castling rights: All available (default)
• En passant: None
• Halfmove clock: 0 (default)
• Full moves: 1 (default)"""
            
            return fen_analysis
            
        except Exception as e:
            return f"FEN Analysis: Error generating FEN - {str(e)}"
    
    def _analyze_position_type(self, board_fen):
        """Analyze the type of chess position"""
        # Count pieces from FEN
        piece_counts = {}
        for char in board_fen:
            if char.isalpha():
                piece_counts[char] = piece_counts.get(char, 0) + 1
        
        total_pieces = sum(piece_counts.values())
        
        # Count by color
        white_pieces = sum(count for piece, count in piece_counts.items() if piece.isupper())
        black_pieces = sum(count for piece, count in piece_counts.items() if piece.islower())
        
        # Count major pieces (queens, rooks)
        white_major = piece_counts.get('Q', 0) + piece_counts.get('R', 0)
        black_major = piece_counts.get('q', 0) + piece_counts.get('r', 0)
        total_major = white_major + black_major
        
        # Count minor pieces (bishops, knights)
        white_minor = piece_counts.get('B', 0) + piece_counts.get('N', 0)
        black_minor = piece_counts.get('b', 0) + piece_counts.get('n', 0)
        total_minor = white_minor + black_minor
        
        # Count pawns
        white_pawns = piece_counts.get('P', 0)
        black_pawns = piece_counts.get('p', 0)
        total_pawns = white_pawns + black_pawns
        
        # Detailed analysis
        analysis_parts = []
        
        # Basic position type
        if total_pieces == 32 and total_pawns == 16:
            analysis_parts.append("Starting position")
        elif total_pieces >= 28:
            analysis_parts.append("Opening phase")
        elif total_pieces >= 20:
            analysis_parts.append("Middle game")
        elif total_pieces >= 12:
            analysis_parts.append("Endgame")
        elif total_pieces >= 6:
            analysis_parts.append("Late endgame")
        else:
            analysis_parts.append("Minimal endgame")
        
        # Material balance
        if white_pieces > black_pieces:
            analysis_parts.append(f"White advantage (+{white_pieces - black_pieces})")
        elif black_pieces > white_pieces:
            analysis_parts.append(f"Black advantage (+{black_pieces - white_pieces})")
        else:
            analysis_parts.append("Material balanced")
        
        # Special position characteristics
        if total_major == 0:
            analysis_parts.append("No major pieces")
        elif total_major <= 2:
            analysis_parts.append("Few major pieces")
        
        if total_minor == 0:
            analysis_parts.append("No minor pieces")
        
        if total_pawns == 0:
            analysis_parts.append("Pawnless")
        elif total_pawns <= 4:
            analysis_parts.append("Few pawns")
        
        # Piece composition details
        piece_summary = f"({white_pieces}v{black_pieces}, {total_major}M, {total_minor}m, {total_pawns}p)"
        
        return " • ".join(analysis_parts) + f" {piece_summary}"
    
    def _determine_game_phase(self, fullmove_number, halfmove_clock):
        """Determine the phase of the game based on move numbers"""
        game_phase_parts = []
        
        if fullmove_number <= 10:
            game_phase_parts.append("Early game")
        elif fullmove_number <= 25:
            game_phase_parts.append("Mid game")
        else:
            game_phase_parts.append("Late game")
        
        # Check for fifty-move rule approach
        if halfmove_clock >= 40:
            game_phase_parts.append("Approaching 50-move rule")
        elif halfmove_clock >= 30:
            game_phase_parts.append("Long without capture/pawn move")
        elif halfmove_clock >= 20:
            game_phase_parts.append("Quiet position")
        
        # Add move count info
        game_phase_parts.append(f"Move {fullmove_number}")
        
        return " • ".join(game_phase_parts)
    
    def _setup_key_bindings(self):
        """Setup keyboard shortcuts"""
        self.window.bind("<Left>", lambda e: self._go_to_previous())
        self.window.bind("<Right>", lambda e: self._go_to_next())
        self.window.bind("<Home>", lambda e: self._go_to_first())
        self.window.bind("<End>", lambda e: self._go_to_last())
        self.window.bind("<space>", lambda e: self._go_to_next())
        self.window.bind("<BackSpace>", lambda e: self._go_to_previous())
        
        # Key repeat handling
        self.window.bind("<KeyPress-Left>", lambda e: self._start_key_repeat(-1))
        self.window.bind("<KeyPress-Right>", lambda e: self._start_key_repeat(1))
        self.window.bind("<KeyRelease-Left>", lambda e: self._stop_key_repeat())
        self.window.bind("<KeyRelease-Right>", lambda e: self._stop_key_repeat())
    
    def _start_key_repeat(self, direction):
        """Start key repeat for navigation"""
        self.key_repeat_direction = direction
        if not self.key_repeat_active:
            self.key_repeat_active = True
            self._key_repeat_step()
    
    def _stop_key_repeat(self):
        """Stop key repeat"""
        self.key_repeat_active = False
    
    def _key_repeat_step(self):
        """Execute one step of key repeat"""
        if self.key_repeat_active:
            if self.key_repeat_direction == -1:
                self._go_to_previous()
            elif self.key_repeat_direction == 1:
                self._go_to_next()
            
            # Schedule next repeat
            self.window.after(self.key_repeat_speed, self._key_repeat_step)
    
    def _on_square_click(self, row, col):
        """Handle square click"""
        # Find if this square corresponds to any encoded position
        for i, pos in enumerate(self.encoded_positions):
            if pos['row'] == row and pos['col'] == col:
                self.current_highlight = i
                self._update_board_display()
                self._update_info_display()
                break
    
    def _go_to_first(self):
        """Go to first position"""
        if self.encoded_positions:
            self.current_highlight = 0
            self._update_board_display()
            self._update_info_display()
    
    def _go_to_previous(self):
        """Go to previous position"""
        if self.encoded_positions and self.current_highlight > 0:
            self.current_highlight -= 1
            self._update_board_display()
            self._update_info_display()
    
    def _go_to_next(self):
        """Go to next position"""
        if self.encoded_positions and self.current_highlight < len(self.encoded_positions) - 1:
            self.current_highlight += 1
            self._update_board_display()
            self._update_info_display()
    
    def _go_to_last(self):
        """Go to last position"""
        if self.encoded_positions:
            self.current_highlight = len(self.encoded_positions) - 1
            self._update_board_display()
            self._update_info_display()
    
    def _update_board_display(self):
        """Update the chess board display with highlighting"""
        if not self.squares or not self.board_data:
            return
        
        # Reset all squares
        for row in range(8):
            for col in range(8):
                if row < len(self.squares) and col < len(self.squares[row]):
                    square = self.squares[row][col]
                    
                    # Determine base color
                    is_light = (row + col) % 2 == 0
                    base_color = "#F0D9B5" if is_light else "#B58863"
                    
                    # Check if this square should be highlighted
                    highlight_color = None
                    if (self.current_highlight >= 0 and 
                        self.current_highlight < len(self.encoded_positions)):
                        pos = self.encoded_positions[self.current_highlight]
                        if pos['row'] == row and pos['col'] == col:
                            highlight_color = "#FFFF00"  # Yellow highlight
                    
                    # Set color and piece (hide empty squares on board)
                    piece = self.board_data[row][col]
                    piece_text = '' if piece == '.' else self.pieces.get(piece, piece)
                    square.config(
                        bg=highlight_color if highlight_color else base_color,
                        text=piece_text
                    )
        
        # Update position counter
        if hasattr(self, 'position_label'):
            total = len(self.encoded_positions)
            current = self.current_highlight + 1 if self.current_highlight >= 0 else 0
            self.position_label.config(text=f"Position: {current} / {total}")
    
    def _update_info_display(self):
        """Update the position info display"""
        if not hasattr(self, 'info_text'):
            return
        
        # Enable editing temporarily to update content
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        
        if (self.current_highlight >= 0 and 
            self.current_highlight < len(self.encoded_positions)):
            pos = self.encoded_positions[self.current_highlight]
            
            info = f"""Current Position: {self.current_highlight + 1} / {len(self.encoded_positions)}

Square: {pos['square']}
Row: {pos['row'] + 1} (Rank {8 - pos['row']})
Column: {pos['col'] + 1} (File {chr(ord('a') + pos['col'])})
Piece: {pos['piece']} ({pos['symbol']})
Sequence: {pos['sequence']}
Byte Index: {pos['index']}

Chess Notation: {pos['square']}
Coordinates: ({pos['row']}, {pos['col']})
"""
            
            self.info_text.insert(1.0, info)
        else:
            self.info_text.insert(1.0, "No position selected\n\nClick on a highlighted square or use navigation controls")
        
        # Disable editing after update
        self.info_text.config(state="disabled")
    
    def _validate_board(self):
        """Validate the chess board"""
        if not self.board_data:
            messagebox.showwarning("No Board", "No board data to validate")
            return
        
        is_valid, errors = self._validate_chess_board(self.board_data)
        
        if is_valid:
            messagebox.showinfo("Valid Board", "Chess board is valid!")
        else:
            error_msg = "Board validation errors:\n\n" + "\n".join(errors)
            messagebox.showerror("Invalid Board", error_msg)
    
    def _save_as_png(self):
        """Save board as PNG image"""
        if not self.board_data:
            messagebox.showwarning("No Board", "No board data to export")
            return
        
        try:
            # Import PIL for image creation
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError:
                messagebox.showerror("Error", "PIL (Pillow) library is required for PNG export.\nInstall with: pip install Pillow")
                return
            
            # Create chess_images directory
            import os
            chess_images_dir = os.path.abspath("chess_images")
            os.makedirs(chess_images_dir, exist_ok=True)
            
            # Ask user for export option if many positions
            num_positions = len(self.encoded_positions)
            max_single_image = 150  # Increased threshold - can show up to 6 columns (150 positions)
            
            if num_positions > max_single_image:
                from tkinter import messagebox as mb
                choice = mb.askyesnocancel("Export Options", 
                                         f"You have {num_positions} positions.\n\n"
                                         f"Yes: Create multiple images (recommended)\n"
                                         f"No: Create one large image\n"
                                         f"Cancel: Cancel export")
                
                if choice is None:  # Cancel
                    return
                elif choice:  # Multiple images
                    self._save_multiple_png_images(chess_images_dir)
                    return
                else:  # Single large image
                    self._save_single_large_png(chess_images_dir)
                    return
            else:
                # Default single image for small number of positions
                self._save_single_png_image(chess_images_dir)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PNG:\n{str(e)}")
    
    def _save_single_png_image(self, chess_images_dir):
        """Save single PNG image with all positions"""
        from PIL import Image, ImageDraw, ImageFont
        import os, datetime
        
        # Board settings with dynamic legend width based on columns
        square_size = 60
        board_size = 8 * square_size
        margin = 40
        
        # Calculate number of columns needed (25 positions per column)
        positions_per_column = 25
        num_positions = len(self.encoded_positions)
        num_columns = (num_positions + positions_per_column - 1) // positions_per_column if num_positions > 0 else 1
        
        # Each column needs about 280px width
        column_width = 280
        legend_width = num_columns * column_width
        
        # Height is based on tallest column (max 25 positions)
        max_positions_in_column = min(positions_per_column, num_positions)
        base_legend_height = 140  # Increased from 120 to make image taller
        positions_height = max_positions_in_column * 20 + 25  # Increased spacing from 18 to 20, added 5 more pixels
        required_height = board_size + 2 * margin
        legend_height = base_legend_height + positions_height
        
        img_width = board_size + 2 * margin + legend_width
        img_height = max(required_height, legend_height + margin * 2)
        
        # Create and draw image
        img = self._create_chess_image(img_width, img_height, square_size, board_size, margin, 
                                     legend_width, show_all_positions=True)
        
        # Generate filename and save
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chess_board_{timestamp}.png"
        filepath = os.path.join(chess_images_dir, filename)
        img.save(filepath, "PNG")
        
        messagebox.showinfo("PNG Saved", f"Chess board saved as:\n{filepath}")
    
    def _save_single_large_png(self, chess_images_dir):
        """Save single large PNG image with all positions (user confirmed)"""
        self._save_single_png_image(chess_images_dir)
    
    def _save_multiple_png_images(self, chess_images_dir):
        """Save multiple PNG images for large number of positions"""
        from PIL import Image, ImageDraw, ImageFont
        import os, datetime
        
        positions_per_image = 75  # Increased to 75 (3 columns of 25 each)
        total_positions = len(self.encoded_positions)
        num_images = (total_positions + positions_per_image - 1) // positions_per_image
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []
        
        for img_num in range(num_images):
            start_idx = img_num * positions_per_image
            end_idx = min(start_idx + positions_per_image, total_positions)
            
            # Create subset of positions for this image
            subset_positions = self.encoded_positions[start_idx:end_idx]
            
            # Adjust current highlight for this subset
            adjusted_highlight = -1
            if self.current_highlight >= start_idx and self.current_highlight < end_idx:
                adjusted_highlight = self.current_highlight - start_idx
            
            # Calculate image dimensions with multi-column layout
            square_size = 60
            board_size = 8 * square_size
            margin = 40
            
            # Calculate number of columns needed (25 positions per column)
            positions_per_column = 25
            num_positions = len(subset_positions)
            num_columns = (num_positions + positions_per_column - 1) // positions_per_column if num_positions > 0 else 1
            
            # Each column needs about 280px width
            column_width = 280
            legend_width = num_columns * column_width
            
            # Height is based on tallest column (max 25 positions)
            max_positions_in_column = min(positions_per_column, num_positions)
            base_legend_height = 140  # Increased from 120 to make image taller
            positions_height = max_positions_in_column * 20 + 25  # Increased spacing from 18 to 20, added 5 more pixels
            required_height = board_size + 2 * margin
            legend_height = base_legend_height + positions_height
            
            img_width = board_size + 2 * margin + legend_width
            img_height = max(required_height, legend_height + margin * 2)
            
            # Create image with title indicating part number
            img = self._create_chess_image(img_width, img_height, square_size, board_size, margin, 
                                         legend_width, show_all_positions=True, 
                                         part_info=f"Part {img_num + 1} of {num_images}",
                                         total_positions=total_positions,
                                         custom_encoded_positions=subset_positions,
                                         custom_highlight=adjusted_highlight,
                                         position_start_index=start_idx)
            
            # Save this image
            filename = f"chess_board_{timestamp}_part{img_num + 1}of{num_images}.png"
            filepath = os.path.join(chess_images_dir, filename)
            img.save(filepath, "PNG")
            saved_files.append(filepath)
        
        # Show success message
        files_list = "\n".join([os.path.basename(f) for f in saved_files])
        messagebox.showinfo("PNG Saved", f"Chess board saved as {num_images} images:\n\n{files_list}")
    
    def _create_chess_image(self, img_width, img_height, square_size, board_size, margin, 
                           legend_width, show_all_positions=False, part_info="", total_positions=None, 
                           custom_encoded_positions=None, custom_highlight=-1, position_start_index=0):
        """Create chess board image with specified parameters"""
        from PIL import Image, ImageDraw, ImageFont
        
        # Use custom positions if provided, otherwise use instance positions
        encoded_positions = custom_encoded_positions if custom_encoded_positions is not None else self.encoded_positions
        current_highlight = custom_highlight if custom_highlight >= 0 else self.current_highlight
        
        # Colors
        light_square = "#F0D9B5"
        dark_square = "#B58863"
        highlight_color = "#FFFF00"
        border_color = "#8B4513"
        text_color = "#000000"
        
        # Create image
        img = Image.new("RGB", (img_width, img_height), "white")
        draw = ImageDraw.Draw(img)
        
        # Try to load fonts
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            coord_font = ImageFont.truetype("arial.ttf", 14)
            title_font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                import platform
                if platform.system() == "Windows":
                    font = ImageFont.truetype("segoeui.ttf", 20)
                    coord_font = ImageFont.truetype("segoeui.ttf", 14)
                    title_font = ImageFont.truetype("segoeui.ttf", 16)
                else:
                    font = ImageFont.load_default()
                    coord_font = ImageFont.load_default()
                    title_font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
                coord_font = ImageFont.load_default()
                title_font = ImageFont.load_default()
        
        # Draw title if part info provided
        if part_info and title_font:
            draw.text((margin, 10), part_info, fill=text_color, font=title_font)
        
        # Create piece mapping for display
        piece_letters = {
            'r': 'r', 'n': 'n', 'b': 'b', 'q': 'q', 'k': 'k', 'p': 'p',
            'R': 'R', 'N': 'N', 'B': 'B', 'Q': 'Q', 'K': 'K', 'P': 'P',
            '.': ''
        }
        
        # Colors for highlighting encoded positions
        position_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"]
        
        # Draw board border
        board_left = margin
        board_top = margin + (30 if part_info else 0)  # Adjust for title
        draw.rectangle(
            [board_left - 2, board_top - 2, board_left + board_size + 2, board_top + board_size + 2],
            outline=border_color, width=2
        )
        
        # Draw squares and pieces
        for row in range(8):
            for col in range(8):
                x = board_left + col * square_size
                y = board_top + row * square_size
                
                # Determine square color
                is_light = (row + col) % 2 == 0
                square_color = light_square if is_light else dark_square
                
                # Check if this square is part of any encoded position
                position_index = -1
                for i, pos in enumerate(encoded_positions):
                    if pos['row'] == row and pos['col'] == col:
                        color_index = i % len(position_colors)
                        square_color = position_colors[color_index]
                        position_index = i
                        break
                
                # Highlight current position with yellow
                if (current_highlight >= 0 and 
                    current_highlight < len(encoded_positions)):
                    pos = encoded_positions[current_highlight]
                    if pos['row'] == row and pos['col'] == col:
                        square_color = highlight_color
                
                # Draw square
                draw.rectangle([x, y, x + square_size, y + square_size], fill=square_color)
                
                # Draw border for highlighted squares
                if position_index >= 0:
                    draw.rectangle([x, y, x + square_size, y + square_size], outline="#FF0000", width=2)
                
                # Draw piece using letters
                if row < len(self.board_data) and col < len(self.board_data[row]):
                    piece = self.board_data[row][col]
                    piece_letter = piece_letters.get(piece, piece)
                    
                    if piece_letter and font:
                        piece_color = "#000000" if piece.isupper() else "#FFFFFF"
                        if square_color == highlight_color:
                            piece_color = "#000000"
                        
                        # Calculate text position
                        text_bbox = draw.textbbox((0, 0), piece_letter, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        text_x = x + (square_size - text_width) // 2
                        text_y = y + (square_size - text_height) // 2
                        
                        draw.text((text_x, text_y), piece_letter, fill=piece_color, font=font)
                
                # Draw position index
                if position_index >= 0 and coord_font:
                    index_text = str(position_index + 1 + position_start_index)  # Show correct global index
                    text_bbox = draw.textbbox((0, 0), index_text, font=coord_font)
                    text_width = text_bbox[2] - text_bbox[0]
                    draw.text((x + square_size - text_width - 2, y + 2), index_text, fill="#000000", font=coord_font)
        
        # Draw coordinates
        if coord_font:
            # File labels (a-h) at bottom
            for col in range(8):
                label = chr(ord('a') + col)
                x = board_left + col * square_size + square_size // 2
                y = board_top + board_size + 5
                text_bbox = draw.textbbox((0, 0), label, font=coord_font)
                text_width = text_bbox[2] - text_bbox[0]
                draw.text((x - text_width // 2, y), label, fill=text_color, font=coord_font)
            
            # Rank labels (8-1) at left
            for row in range(8):
                label = str(8 - row)
                x = board_left - 20
                y = board_top + row * square_size + square_size // 2
                text_bbox = draw.textbbox((0, 0), label, font=coord_font)
                text_height = text_bbox[3] - text_bbox[1]
                draw.text((x, y - text_height // 2), label, fill=text_color, font=coord_font)
        
        # Draw legend for encoded positions
        if encoded_positions and coord_font:
            legend_x = board_left + board_size + 20
            legend_y = board_top
            
            # Title
            draw.text((legend_x, legend_y), "Encoded Positions:", fill=text_color, font=font)
            legend_y += 30
            
            # Current position indicator
            if (current_highlight >= 0 and current_highlight < len(encoded_positions)):
                current_pos = encoded_positions[current_highlight]
                global_index = current_highlight + 1 + position_start_index
                draw.text((legend_x, legend_y), f"Current: #{global_index} at {current_pos['square']}", 
                         fill="#FFD700", font=coord_font)
            legend_y += 25
            
            # Multi-column layout for positions
            positions_per_column = 25
            column_width = 280
            num_positions = len(encoded_positions)
            
            if show_all_positions:
                positions_to_show = encoded_positions
            else:
                positions_to_show = encoded_positions[:15]  # For compatibility with old behavior
            
            # Draw positions in columns
            current_column = 0
            current_row_in_column = 0
            
            for i, pos in enumerate(positions_to_show):
                # Calculate position in current column
                if current_row_in_column >= positions_per_column:
                    current_column += 1
                    current_row_in_column = 0
                
                # Calculate drawing position
                col_x = legend_x + current_column * column_width
                row_y = legend_y + current_row_in_column * 18
                
                # Color for this position
                color_index = i % len(position_colors)
                color = position_colors[color_index]
                
                # Draw color square
                draw.rectangle([col_x, row_y, col_x + 15, row_y + 15], fill=color, outline="#000000")
                
                # Draw position info
                pos_text = f"{i + 1 + position_start_index}: {pos['square']} ({pos['piece']})"  # Show correct global index
                draw.text((col_x + 20, row_y), pos_text, fill=text_color, font=coord_font)
                
                current_row_in_column += 1
            
            # Show remaining count if not showing all (for old behavior compatibility)
            if not show_all_positions and len(encoded_positions) > 15:
                # Find position for "more" text
                if current_row_in_column >= positions_per_column:
                    current_column += 1
                    current_row_in_column = 0
                
                col_x = legend_x + current_column * column_width
                row_y = legend_y + current_row_in_column * 18
                
                draw.text((col_x, row_y), f"... and {len(encoded_positions) - 15} more positions", 
                         fill=text_color, font=coord_font)
            
            # Legend info - position it below the tallest column
            max_rows_used = min(positions_per_column, len(positions_to_show))
            legend_info_y = legend_y + max_rows_used * 18 + 40
            
            legend_info = [
                "Legend:",
                "• Yellow = Current position",
                "• Colors = Encoded positions", 
                "• Numbers = Position index",
                "• Letters = Chess pieces",
                f"• Total positions: {total_positions if total_positions is not None else len(encoded_positions)}"
            ]
            
            for line in legend_info:
                draw.text((legend_x, legend_info_y), line, fill=text_color, font=coord_font)
                legend_info_y += 16
        
        return img
    
    def _copy_fen(self):
        """Copy FEN notation to clipboard"""
        if not self.board_data:
            messagebox.showwarning("No Board", "No board data to export")
            return
        
        try:
            # Convert board to FEN
            fen_rows = []
            for row in self.board_data:
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
            
            # Use original FEN metadata if available, otherwise use defaults
            if self.original_fen:
                # Parse original FEN to extract metadata
                fen_parts = self.original_fen.split()
                if len(fen_parts) >= 6:
                    # Full FEN: use original metadata
                    active_color = fen_parts[1]
                    castling = fen_parts[2] 
                    en_passant = fen_parts[3]
                    halfmove = fen_parts[4]
                    fullmove = fen_parts[5]
                    full_fen = f"{board_fen} {active_color} {castling} {en_passant} {halfmove} {fullmove}"
                else:
                    # Incomplete FEN: use defaults for missing parts
                    full_fen = f"{board_fen} w KQkq - 0 1"
            else:
                # No original FEN: use defaults
                full_fen = f"{board_fen} w KQkq - 0 1"
            
            # Copy to clipboard
            self.window.clipboard_clear()
            self.window.clipboard_append(full_fen)
            self.window.update()
            
            messagebox.showinfo("FEN Copied", f"FEN notation copied to clipboard:\n\n{full_fen}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate FEN:\n{str(e)}")
    
    def _copy_fen_analysis(self):
        """Copy detailed FEN analysis to clipboard"""
        try:
            fen_analysis = self._analyze_fen() if self.original_fen else self._analyze_board_fen()
            
            # Copy to clipboard
            self.window.clipboard_clear()
            self.window.clipboard_append(fen_analysis)
            self.window.update()
            
            messagebox.showinfo("FEN Analysis Copied", "FEN analysis copied to clipboard")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate FEN analysis:\n{str(e)}")

def show_chess_viewer(file_path, parent=None):
    """
    Convenience function to show chess viewer
    
    Args:
        file_path: Path to the chess file
        parent: Parent window (optional)
    """
    viewer = ChessViewer(parent)
    viewer.show_chess_file(file_path)
