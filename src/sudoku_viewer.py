# src/sudoku_viewer.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import re

class ToolTip:
    """Create tooltip for tkinter widgets - fixed version"""
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.after_id = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<ButtonPress>", self.on_click)  # Hide tooltip on click

    def on_enter(self, event=None):
        if self.text:
            # Cancel any pending tooltip
            if self.after_id:
                self.widget.after_cancel(self.after_id)
            # Add small delay before showing tooltip
            self.after_id = self.widget.after(300, self.show_tooltip)

    def on_leave(self, event=None):
        # Cancel pending tooltip
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide_tooltip()
    
    def on_click(self, event=None):
        self.hide_tooltip()

    def show_tooltip(self):
        if self.tooltip_window or not self.text:
            return
        # Check if widget still exists and mouse is still over it
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
            self.tooltip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.wm_attributes("-topmost", True)  # Keep tooltip on top
            label = tk.Label(tw, text=self.text, justify='left',
                            background="#ffffe0", relief='solid', borderwidth=1,
                            font=("Arial", 9), wraplength=300)  # Add text wrapping
            label.pack()
        except tk.TclError:
            # Widget destroyed, clean up
            self.tooltip_window = None
        finally:
            self.after_id = None

    def hide_tooltip(self):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            try:
                tw.destroy()
            except tk.TclError:
                pass  # Window already destroyed

    def update_text(self, new_text):
        self.text = new_text
        # If tooltip is currently showing, hide it so it will show new text next time
        if self.tooltip_window:
            self.hide_tooltip()

class SudokuViewer:
    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.grid_data = None
        self.encoded_positions = []
        self.current_highlight = -1
        self.cells = []
        
        # Key repeat variables - optimized for responsiveness
        self.key_repeat_active = False
        self.key_repeat_direction = 0
        self.key_repeat_speed = 50  # Reduced from 100 for faster response
        self.key_repeat_initial_delay = 200  # Initial delay before repeat starts
        
        # Performance optimization variables
        self._position_lookup = {}  # Cache for position lookups
        self._last_highlighted_cell = None
        self._ui_update_pending = False
    
    def _validate_sudoku_grid(self, grid):
        """
        Validate if a 9x9 grid follows Sudoku rules
        
        Args:
            grid: 9x9 list of lists with numbers 1-9
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        if not grid or len(grid) != 9:
            return False, ["Grid must be 9x9"]
        
        errors = []
        
        # Check each row
        for i, row in enumerate(grid):
            if len(row) != 9:
                errors.append(f"Row {i+1} has {len(row)} elements, should be 9")
                continue
                
            # Check for valid numbers (1-9)
            for j, val in enumerate(row):
                if not isinstance(val, int) or val < 1 or val > 9:
                    errors.append(f"Row {i+1}, Col {j+1}: invalid value {val}")
            
            # Check for duplicates in row
            unique_vals = set(row)
            if len(unique_vals) != 9:
                duplicates = [x for x in set(row) if row.count(x) > 1]
                errors.append(f"Row {i+1}: duplicates found: {duplicates}")
        
        # Check each column
        for col in range(9):
            column = [grid[row][col] for row in range(9)]
            unique_vals = set(column)
            if len(unique_vals) != 9:
                duplicates = [x for x in set(column) if column.count(x) > 1]
                errors.append(f"Column {col+1}: duplicates found: {duplicates}")
        
        # Check each 3x3 box
        for box_row in range(3):
            for box_col in range(3):
                box_values = []
                for r in range(3):
                    for c in range(3):
                        row = box_row * 3 + r
                        col = box_col * 3 + c
                        box_values.append(grid[row][col])
                
                unique_vals = set(box_values)
                if len(unique_vals) != 9:
                    duplicates = [x for x in set(box_values) if box_values.count(x) > 1]
                    errors.append(f"Box ({box_row+1},{box_col+1}): duplicates found: {duplicates}")
        
        return len(errors) == 0, errors
        
    def show_sudoku_file(self, file_path):
        """
        Parse and display Sudoku file in a visual grid
        
        Args:
            file_path: Path to the encoded Sudoku file
        """
        try:
            # Show progress for large files
            file_size = os.path.getsize(file_path)
            show_progress = file_size > 1024 * 1024  # Show for files > 1MB
            
            if show_progress:
                # Create a simple progress window
                progress_window = tk.Toplevel(self.parent if self.parent else None)
                progress_window.title("Loading Sudoku Viewer")
                progress_window.geometry("300x100")
                progress_window.resizable(False, False)
                progress_window.attributes("-topmost", True)
                
                # Center the progress window
                progress_window.update_idletasks()
                x = (progress_window.winfo_screenwidth() // 2) - 150
                y = (progress_window.winfo_screenheight() // 2) - 50
                progress_window.geometry(f"300x100+{x}+{y}")
                
                progress_label = tk.Label(progress_window, text="Parsing Sudoku file...", font=("Arial", 10))
                progress_label.pack(pady=20)
                
                progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
                progress_bar.pack(pady=10, padx=20, fill=tk.X)
                progress_bar.start()
                
                progress_window.update()
            
            # Parse the Sudoku file with optimized method
            self.grid_data, self.encoded_positions = self._parse_sudoku_file_optimized(file_path)
            
            if show_progress:
                progress_label.config(text="Building position cache...")
                progress_window.update()
            
            # Build position lookup cache for better performance
            self._build_position_cache()
            
            if show_progress:
                progress_window.destroy()
            
            if self.grid_data is None:
                messagebox.showerror("Error", "Could not parse Sudoku file format")
                return
                
            # Create and show viewer window
            self._create_viewer_window(file_path)
            
        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("Error", f"Failed to open Sudoku viewer:\n{str(e)}")
    
    def _parse_sudoku_file(self, file_path):
        """Parse Sudoku file to extract grid and positions"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            grid_data = None
            encoded_positions = []
            
            if "GRID:" in content and "POSITIONS:" in content:
                # Grid format - extract both grid and positions
                lines = content.split('\n')
                in_grid = False
                in_positions = False
                grid_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line == "GRID:":
                        in_grid = True
                        in_positions = False
                        continue
                    elif line.startswith("POSITIONS:"):
                        in_grid = False
                        in_positions = True
                        continue
                    
                    if in_grid and line and not line.startswith("POSITIONS:") and not line.startswith("Byte"):
                        # Parse grid line: "1 2 3 4 5 6 7 8 9"
                        try:
                            row_values = [int(x) for x in line.split()]
                            if len(row_values) == 9:
                                grid_lines.append(row_values)
                        except ValueError:
                            continue
                    
                    if in_positions and "Byte" in line and " -> " in line:
                        try:
                            # Parse: Byte0: (1,2)=3 -> 72
                            byte_part = line.split(": (")[0]
                            idx = int(byte_part.replace("Byte", ""))
                            
                            pos_part = line.split(": (")[1].split(")=")
                            row_col = pos_part[0].split(",")
                            row = int(row_col[0]) - 1  # Convert to 0-based
                            col = int(row_col[1]) - 1
                            
                            value_byte = pos_part[1].split(" -> ")
                            value = int(value_byte[0])
                            byte_val = int(value_byte[1])
                            
                            encoded_positions.append({
                                'index': idx,
                                'row': row,
                                'col': col, 
                                'value': value,
                                'byte_value': byte_val
                            })
                        except (ValueError, IndexError):
                            continue
                
                if len(grid_lines) == 9:
                    # Validate that it's a proper grid (each row has 9 elements)
                    grid_valid, validation_errors = self._validate_sudoku_grid(grid_lines)
                    
                    if grid_valid:
                        grid_data = grid_lines
                    else:
                        print(f"Grid validation failed: {validation_errors}")
                        # Continue to try reconstruction from positions
            
            else:
                # Parse other formats and regenerate grid using the same algorithm
                grid_data, encoded_positions = self._reconstruct_grid_from_encoded(content)
            
            return grid_data, encoded_positions
            
        except Exception as e:
            print(f"Error parsing Sudoku file: {e}")
            return None, []
    
    def _reconstruct_grid_from_encoded(self, content):
        """Reconstruct Sudoku grid from compact/readable format"""
        from src import sudoku_mode
        
        encoded_positions = []
        
        try:
            if content.startswith("R") and "C" in content and "V" in content:
                # Readable format: R1C1V5B72I0 R2C3V7B101I1 ...
                parts = content.strip().split()
                for part in parts:
                    try:
                        if part.startswith("R") and "C" in part and "V" in part and "B" in part and "I" in part:
                            # Extract R1C1V5B72I0
                            r_part = part.split("C")[0][1:]  # Remove 'R', get row
                            c_v_b_i_part = part.split("C")[1]    # Get "1V5B72I0"
                            
                            c_part = c_v_b_i_part.split("V")[0]  # Get col
                            v_b_i_part = c_v_b_i_part.split("V")[1]  # Get "5B72I0"
                            
                            v_part = v_b_i_part.split("B")[0]  # Get value
                            b_i_part = v_b_i_part.split("B")[1]  # Get "72I0"
                            
                            b_part = b_i_part.split("I")[0]  # Get byte value
                            i_part = b_i_part.split("I")[1]  # Get index
                            
                            row = int(r_part) - 1  # Convert to 0-based
                            col = int(c_part) - 1
                            value = int(v_part)
                            byte_val = int(b_part)
                            idx = int(i_part)
                            
                            encoded_positions.append({
                                'index': idx,
                                'row': row,
                                'col': col,
                                'value': value,
                                'byte_value': byte_val
                            })
                    except:
                        continue
            
            elif "|" in content:
                # Compact format: r,c,v,b,i|r,c,v,b,i|...
                parts = content.strip().split("|")
                for part in parts:
                    try:
                        if "," in part:
                            coords = part.split(",")
                            if len(coords) == 5:
                                row, col, value, byte_val, idx = map(int, coords)
                                encoded_positions.append({
                                    'index': idx,
                                    'row': row,
                                    'col': col,
                                    'value': value,
                                    'byte_value': byte_val
                                })
                    except:
                        continue
            
            # Now regenerate the Sudoku grid that was used during encoding
            # Try different seeds to find the one that matches the encoded positions
            grid_data = None
            
            # Try common seeds first, including more comprehensive list
            # Include popular default seeds and common user choices
            test_seeds = [
                # Default and common seeds
                None, 12345, 54321, 42, 123, 456, 789, 999, 1234, 5678,
                # Common patterns
                0, 1, 2, 3, 4, 5, 10, 100, 1000, 9999,
                # Year-based
                2023, 2024, 2025, 2022, 2021,
                # Common passwords/pins
                1111, 2222, 3333, 4444, 5555, 6666, 7777, 8888, 9999,
                # Other common choices
                11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888, 99999,
                # ASCII sums of common words
                sum(ord(c) for c in "password"),
                sum(ord(c) for c in "secret"),
                sum(ord(c) for c in "test"),
                sum(ord(c) for c in "key"),
                sum(ord(c) for c in "seed"),
            ]
            
            for seed in test_seeds:
                test_grid = sudoku_mode.generate_sudoku_grid(seed)
                
                # Check if this grid matches our encoded positions
                matches = True
                for pos in encoded_positions:
                    if 0 <= pos['row'] < 9 and 0 <= pos['col'] < 9:
                        if test_grid[pos['row']][pos['col']] != pos['value']:
                            matches = False
                            break
                
                if matches:
                    grid_data = test_grid
                    # Validate the matched grid
                    is_valid, validation_errors = self._validate_sudoku_grid(test_grid)
                    if not is_valid:
                        print(f"Warning: Matched grid has validation errors: {validation_errors}")
                    break
            
            # If no seed matched, try to reconstruct using the encoded values directly
            if grid_data is None:
                # Create a valid sudoku grid and then verify if we can place the encoded values
                grid_data = sudoku_mode.generate_sudoku_grid(42)  # Use fixed seed as base
                
                # Try to place the encoded values and see if they create conflicts
                test_grid = [row[:] for row in grid_data]  # Deep copy
                has_conflicts = False
                
                for pos in encoded_positions:
                    if 0 <= pos['row'] < 9 and 0 <= pos['col'] < 9:
                        # If the position already has a different value, try to use a generic valid grid
                        if test_grid[pos['row']][pos['col']] != pos['value']:
                            has_conflicts = True
                            break
                
                # If there are conflicts, just use the base grid (valid sudoku)
                # The positions will still be highlighted correctly even if values don't match exactly
                if not has_conflicts:
                    grid_data = test_grid
            
            return grid_data, encoded_positions
            
        except Exception as e:
            print(f"Error reconstructing grid: {e}")
            # Fallback - create a valid sudoku grid using known algorithm
            from src import sudoku_mode
            grid_data = sudoku_mode.generate_sudoku_grid(42)  # Use fixed seed for consistency
            return grid_data, encoded_positions
    
    def _create_viewer_window(self, file_path):
        """Create the main viewer window"""
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title(f"Sudoku Viewer - {os.path.basename(file_path)}")
        self.window.resizable(False, False)
        
        # Set window size first
        window_width = 600
        window_height = 650
        
        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Calculate center position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Ensure window is not positioned off-screen
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))
        
        # Set geometry (width x height + x_offset + y_offset)
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Bring window to front and focus
        self.window.lift()
        self.window.focus_force()
        
        # Title
        title_frame = tk.Frame(self.window)
        title_frame.pack(pady=5)
        
        tk.Label(title_frame, text="Sudoku Encoded Data Viewer", 
                font=("Arial", 14, "bold")).pack()
        tk.Label(title_frame, text=f"File: {os.path.basename(file_path)}", 
                font=("Arial", 9)).pack()
        
        # Create the Sudoku grid
        self._create_sudoku_grid()
        
        # Control panel
        self._create_control_panel()
        
        # Status bar
        status_frame = tk.Frame(self.window)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        # Validate the grid and show status
        if self.grid_data:
            is_valid, validation_errors = self._validate_sudoku_grid(self.grid_data)
            if is_valid:
                grid_status = "Valid Sudoku 9x9"
            else:
                grid_status = f"Invalid Sudoku (errors: {len(validation_errors)})"
                print(f"Sudoku validation errors: {validation_errors}")
        else:
            grid_status = "No grid data"
        
        tk.Label(status_frame, text=f"Data: {len(self.encoded_positions)} bytes | "
                                   f"Grid: {grid_status}", 
                font=("Arial", 8), fg="gray").pack()
        
        # Initialize the current position and highlights
        self.current_highlight = 0 if self.encoded_positions else -1
        self._update_highlights_optimized()  # This will highlight the first position
        self._update_position_display()
        
        # Setup keyboard bindings
        self._setup_keyboard_bindings()
    
    def _setup_keyboard_bindings(self):
        """Setup keyboard bindings for navigation"""
        # Make window focusable and bind keys
        self.window.focus_set()
        
        # Arrow keys
        self.window.bind('<Right>', lambda e: self._navigate_bytes(1))
        self.window.bind('<Left>', lambda e: self._navigate_bytes(-1))
        self.window.bind('<Up>', lambda e: self._navigate_bytes(10))
        self.window.bind('<Down>', lambda e: self._navigate_bytes(-10))
        
        # Page keys
        self.window.bind('<Prior>', lambda e: self._navigate_bytes(100))  # Page Up
        self.window.bind('<Next>', lambda e: self._navigate_bytes(-100))  # Page Down
        
        # Setup repeat functionality for holding keys
        self._setup_key_repeat()
    
    def _setup_key_repeat(self):
        """Setup key repeat functionality for holding keys"""
        # Bind key press and release events
        self.window.bind('<KeyPress>', self._on_key_press)
        self.window.bind('<KeyRelease>', self._on_key_release)
    
    def _on_key_press(self, event):
        """Handle key press for repeat functionality - optimized"""
        direction_map = {
            'Right': 1,
            'Left': -1, 
            'Up': 10,
            'Down': -10,
            'Prior': 100,  # Page Up
            'Next': -100   # Page Down
        }
        
        if event.keysym in direction_map:
            # Immediate first navigation
            self._navigate_bytes(direction_map[event.keysym])
            
            if not self.key_repeat_active:
                self.key_repeat_active = True
                self.key_repeat_direction = direction_map[event.keysym]
                # Start repeating after initial delay
                self.window.after(self.key_repeat_initial_delay, self._key_repeat)
    
    def _on_key_release(self, event):
        """Handle key release to stop repeat"""
        direction_map = {
            'Right': 1,
            'Left': -1,
            'Up': 10, 
            'Down': -10,
            'Prior': 100,
            'Next': -100
        }
        
        if event.keysym in direction_map:
            self.key_repeat_active = False
    
    def _key_repeat(self):
        """Repeat key navigation while key is held - optimized for performance"""
        if self.key_repeat_active:
            self._navigate_bytes(self.key_repeat_direction)
            # Use adaptive speed - faster for larger jumps
            speed = self.key_repeat_speed
            if abs(self.key_repeat_direction) >= 100:  # Page up/down
                speed = max(20, speed // 2)  # Faster for large jumps
            elif abs(self.key_repeat_direction) >= 10:  # Up/down arrow
                speed = max(30, speed // 1.5)  # Medium speed
            
            # Schedule next repeat
            self.window.after(int(speed), self._key_repeat)
    
    def _navigate_bytes(self, direction):
        """Navigate by given number of bytes with bounds checking - optimized"""
        if not self.encoded_positions:
            return
            
        new_position = self.current_highlight + direction
        
        # Bounds checking: 0-based index, so valid range is 0 to len-1
        max_position = len(self.encoded_positions) - 1
        new_position = max(0, min(new_position, max_position))
        
        if new_position != self.current_highlight:
            self.current_highlight = new_position
            # Use optimized update methods
            self._update_highlights_optimized()
            self._update_position_display_optimized()
    
    def _create_sudoku_grid(self):
        """Create the visual Sudoku grid - optimized version"""
        grid_frame = tk.Frame(self.window)
        grid_frame.pack(pady=20)
        
        # Create proper 2D array for cells
        self.cells = [[None for _ in range(9)] for _ in range(9)]
        self.cell_tooltips = [[None for _ in range(9)] for _ in range(9)]
        
        for big_row in range(3):
            for big_col in range(3):
                # Create 3x3 subgrid frame
                subgrid_frame = tk.Frame(grid_frame, bg="black", bd=2, relief="solid")
                subgrid_frame.grid(row=big_row, column=big_col, padx=2, pady=2)
                
                for small_row in range(3):
                    for small_col in range(3):
                        actual_row = big_row * 3 + small_row
                        actual_col = big_col * 3 + small_col
                        
                        value = self.grid_data[actual_row][actual_col]
                        
                        # Determine initial background color
                        initial_bg = "lightyellow" if (actual_row, actual_col) in self._position_lookup else "SystemButtonFace"
                        
                        # Create cell button
                        cell = tk.Button(subgrid_frame, text=str(value), 
                                       width=3, height=2, font=("Arial", 12, "bold"),
                                       relief="raised", bd=1, bg=initial_bg,
                                       command=lambda r=actual_row, c=actual_col: self._cell_clicked(r, c))
                        
                        cell.grid(row=small_row, column=small_col, padx=1, pady=1)
                        
                        # Store cell in 2D array
                        self.cells[actual_row][actual_col] = cell
                        
                        # Create tooltip immediately but with optimized text
                        tooltip_text = self._get_cell_tooltip_text_optimized(actual_row, actual_col)
                        self.cell_tooltips[actual_row][actual_col] = ToolTip(cell, tooltip_text)
    
    def _get_cell_tooltip_text_optimized(self, row, col):
        """Generate optimized tooltip text for a cell using cache"""
        # Check if position lookup cache exists and is populated
        if hasattr(self, '_position_lookup') and self._position_lookup:
            # Use cached lookup for better performance
            if (row, col) in self._position_lookup:
                position_indices = self._position_lookup[(row, col)]
                # Get first position for display
                pos_index = position_indices[0]
                pos = self.encoded_positions[pos_index]
                char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
                return (f"Cell ({row+1},{col+1}) Value: {self.grid_data[row][col]}\n"
                       f"Contains: '{char}' (byte #{pos['index'] + 1})\n"
                       f"ASCII: {pos['byte_value']}")
            else:
                return (f"Cell ({row+1},{col+1}) Value: {self.grid_data[row][col]}\n"
                       f"Empty Sudoku cell\n"
                       f"No encoded data")
        else:
            # Fallback to original method if cache not available
            return self._get_cell_tooltip_text(row, col)
    
    def _get_cell_tooltip_text(self, row, col):
        """Generate tooltip text for a cell"""
        # Find if this cell contains encoded data
        matching_positions = []
        for pos in self.encoded_positions:
            if pos['row'] == row and pos['col'] == col:
                matching_positions.append(pos)
        
        if matching_positions:
            pos = matching_positions[0]  # Take first match
            char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
            return (f"Cell ({row+1},{col+1}) Value: {self.grid_data[row][col]}\n"
                   f"Contains: '{char}' (byte #{pos['index'] + 1})\n"
                   f"ASCII: {pos['byte_value']}")
        else:
            return (f"Cell ({row+1},{col+1}) Value: {self.grid_data[row][col]}\n"
                   f"Empty Sudoku cell\n"
                   f"No encoded data")
    
    def _update_cell_tooltips(self):
        """Update tooltips for all cells - optimized version"""
        # Update tooltips for all cells
        for row in range(9):
            for col in range(9):
                if self.cell_tooltips[row][col] is not None:
                    tooltip_text = self._get_cell_tooltip_text_optimized(row, col)
                    self.cell_tooltips[row][col].update_text(tooltip_text)
    
    def _create_control_panel(self):
        """Create control panel with navigation and info"""
        control_frame = tk.Frame(self.window)
        control_frame.pack(pady=5, fill=tk.X, padx=20)
        
        # Navigation controls
        nav_frame = tk.Frame(control_frame)
        nav_frame.pack(side=tk.TOP, pady=5)
        
        tk.Button(nav_frame, text="◀ Previous Byte", 
                 command=self._prev_position).pack(side=tk.LEFT, padx=5)
        
        self.position_var = tk.StringVar()
        self.position_var.set("Byte: - / -")
        tk.Label(nav_frame, textvariable=self.position_var, 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=15)
        
        tk.Button(nav_frame, text="Next Byte ▶", 
                 command=self._next_position).pack(side=tk.LEFT, padx=5)
        
        # Info display
        info_frame = tk.Frame(control_frame)
        info_frame.pack(side=tk.TOP, pady=10, fill=tk.X)
        
        # Current position info
        self.info_text = tk.Text(info_frame, height=4, width=60, 
                               font=("Courier", 10), state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        button_frame = tk.Frame(control_frame)
        button_frame.pack(side=tk.TOP, pady=10)
        
        tk.Button(button_frame, text="Show All Positions", 
                 command=self._show_all_positions).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Clear Highlights", 
                 command=self._clear_highlights).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Export Grid", 
                 command=self._export_grid).pack(side=tk.LEFT, padx=5)
        
        # Initialize display
        self._update_position_display()
    
    def _cell_clicked(self, row, col):
        """Handle cell click - show if this cell contains encoded data - optimized"""
        # Use cached lookup for better performance
        if hasattr(self, '_position_lookup') and (row, col) in self._position_lookup:
            position_indices = self._position_lookup[(row, col)]
            pos_idx = position_indices[0]  # Take first match
            pos = self.encoded_positions[pos_idx]
            char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
            
            info = f"📍 Clicked Cell: Row {row+1}, Column {col+1}\n"
            info += f"Cell Value: {self.grid_data[row][col]}\n\n"
            info += f"✅ This cell contains encoded data:\n"
            info += f"   Character: '{char}' (byte #{pos['index'] + 1})\n"
            info += f"   ASCII value: {pos['byte_value']}\n\n"
            info += f"💡 Use Next/Previous buttons to navigate through all bytes"
            
            # Update info display (no highlight)
            self._update_info_text(info)
        else:
            info = f"📍 Clicked Cell: Row {row+1}, Column {col+1}\n"
            info += f"Cell Value: {self.grid_data[row][col]}\n\n"
            info += f"❌ This cell does not contain any of your encoded data.\n"
            info += f"It's just part of the Sudoku puzzle structure.\n\n"
            info += f"🟡 Yellow cells contain your actual data"
            
            # Update info display (no highlight)
            self._update_info_text(info)
    
    def _prev_position(self):
        """Navigate to previous encoded position"""
        self._navigate_bytes(-1)
    
    def _next_position(self):
        """Navigate to next encoded position"""
        self._navigate_bytes(1)
    
    def _update_highlights(self):
        """Update cell highlights to show encoded positions"""
        # Clear all highlights first
        for row in range(9):
            for col in range(9):
                self.cells[row][col].configure(bg="SystemButtonFace", fg="black")
        
        # Highlight all encoded positions in light yellow
        for pos in self.encoded_positions:
            if 0 <= pos['row'] < 9 and 0 <= pos['col'] < 9:
                self.cells[pos['row']][pos['col']].configure(bg="lightyellow")
        
        # Highlight current position in bright green
        if 0 <= self.current_highlight < len(self.encoded_positions):
            pos = self.encoded_positions[self.current_highlight]
            if 0 <= pos['row'] < 9 and 0 <= pos['col'] < 9:
                self.cells[pos['row']][pos['col']].configure(bg="lightgreen", fg="darkgreen")
        
        # Update tooltips
        self._update_cell_tooltips()
    
    def _update_highlights_optimized(self):
        """Optimized version of highlight update - only changes necessary cells"""
        # Clear previous highlight if exists
        if self._last_highlighted_cell:
            row, col = self._last_highlighted_cell
            if 0 <= row < 9 and 0 <= col < 9:
                # Check if this cell has any encoded data
                has_data = (row, col) in self._position_lookup
                self.cells[row][col].configure(
                    bg="lightyellow" if has_data else "SystemButtonFace", 
                    fg="black"
                )
        
        # Highlight current position in bright green
        if 0 <= self.current_highlight < len(self.encoded_positions):
            pos = self.encoded_positions[self.current_highlight]
            if 0 <= pos['row'] < 9 and 0 <= pos['col'] < 9:
                self.cells[pos['row']][pos['col']].configure(bg="lightgreen", fg="darkgreen")
                self._last_highlighted_cell = (pos['row'], pos['col'])
        else:
            self._last_highlighted_cell = None
    
    def _update_position_display_optimized(self):
        """Optimized version of position display update"""
        if not self._ui_update_pending:
            self._ui_update_pending = True
            self.window.after_idle(self._do_ui_update)
    
    def _do_ui_update(self):
        """Actual UI update - batched for performance"""
        self._ui_update_pending = False
        
        if self.encoded_positions:
            total = len(self.encoded_positions)
            current = self.current_highlight + 1 if self.current_highlight >= 0 else 0
            self.position_var.set(f"Byte: {current} / {total}")
            
            if 0 <= self.current_highlight < len(self.encoded_positions):
                pos = self.encoded_positions[self.current_highlight]
                char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
                
                info = f"Viewing byte #{self.current_highlight + 1} of your original data\n"
                info += f"Character: '{char}' (ASCII {pos['byte_value']})\n"
                info += f"Stored in Sudoku cell: Row {pos['row']+1}, Column {pos['col']+1}\n"
                info += f"Cell shows number: {pos['value']}\n\n"
                info += f"🟢 Green = Current byte position\n"
                info += f"🟡 Yellow = Other data positions\n"
                info += f"🔵 Blue = Clicked cell\n\n"
                info += f"Keyboard Navigation:\n"
                info += f"← → (±1 byte) | ↑ ↓ (±10 bytes) | PgUp/PgDn (±100 bytes)\n"
                info += f"Hold keys for continuous navigation"
                
                self._update_info_text(info)
        else:
            self.position_var.set("Byte: 0 / 0")
    
    def _highlight_cell(self, row, col, color):
        """Highlight a specific cell"""
        if 0 <= row < 9 and 0 <= col < 9:
            self.cells[row][col].configure(bg=color)
    
    def _update_position_display(self):
        """Update position counter and info"""
        if self.encoded_positions:
            total = len(self.encoded_positions)
            current = self.current_highlight + 1 if self.current_highlight >= 0 else 0
            self.position_var.set(f"Byte: {current} / {total}")
            
            if 0 <= self.current_highlight < len(self.encoded_positions):
                pos = self.encoded_positions[self.current_highlight]
                char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
                
                info = f"Viewing byte #{self.current_highlight + 1} of your original data\n"
                info += f"Character: '{char}' (ASCII {pos['byte_value']})\n"
                info += f"Stored in Sudoku cell: Row {pos['row']+1}, Column {pos['col']+1}\n"
                info += f"Cell shows number: {pos['value']}\n\n"
                info += f"🟢 Green = Current byte position\n"
                info += f"🟡 Yellow = Other data positions\n"
                info += f"🔵 Blue = Clicked cell\n\n"
                info += f"Keyboard Navigation:\n"
                info += f"← → (±1 byte) | ↑ ↓ (±10 bytes) | PgUp/PgDn (±100 bytes)\n"
                info += f"Hold keys for continuous navigation"
                
                self._update_info_text(info)
        else:
            self.position_var.set("Byte: 0 / 0")
            info = "Keyboard Navigation:\n"
            info += "← → (±1 byte) | ↑ ↓ (±10 bytes) | PgUp/PgDn (±100 bytes)\n"
            info += "Hold keys for continuous navigation\n\n"
            info += "🟡 Yellow cells contain your encoded data"
            self._update_info_text(info)
    
    def _update_info_text(self, text):
        """Update the info text display"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, text)
        self.info_text.config(state=tk.DISABLED)
    
    def _show_all_positions(self):
        """Show all encoded positions in the info area"""
        if not self.encoded_positions:
            self._update_info_text("No encoded positions found.")
            return
        
        info = f"All {len(self.encoded_positions)} encoded positions:\n\n"
        for i, pos in enumerate(self.encoded_positions):
            char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
            info += f"Byte {i+1}: '{char}' at ({pos['row']+1},{pos['col']+1}) = {pos['value']}\n"
        
        self._update_info_text(info)
    
    def _clear_highlights(self):
        """Clear all cell highlights"""
        for row in range(9):
            for col in range(9):
                self.cells[row][col].configure(bg="SystemButtonFace", fg="black")
    
    def _export_grid(self):
        """Export the grid to a text file"""
        try:
            from tkinter import filedialog
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("Sudoku Grid:\n")
                    for row in self.grid_data:
                        f.write(" ".join(map(str, row)) + "\n")
                    
                    f.write(f"\nEncoded Positions ({len(self.encoded_positions)} bytes):\n")
                    for i, pos in enumerate(self.encoded_positions):
                        char = chr(pos['byte_value']) if 32 <= pos['byte_value'] <= 126 else '.'
                        f.write(f"Byte {i+1}: '{char}' at ({pos['row']+1},{pos['col']+1}) = {pos['value']}\n")
                
                messagebox.showinfo("Export Complete", f"Grid exported to {file_path}")
        
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export grid:\n{str(e)}")

    def _build_position_cache(self):
        """Build lookup cache for better performance"""
        self._position_lookup = {}
        for i, pos in enumerate(self.encoded_positions):
            row, col = pos['row'], pos['col']
            if (row, col) not in self._position_lookup:
                self._position_lookup[(row, col)] = []
            self._position_lookup[(row, col)].append(i)
    
    def _parse_sudoku_file_optimized(self, file_path):
        """Optimized parsing for large files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Quick format detection
            if "GRID:" in content and "POSITIONS:" in content:
                return self._parse_grid_format(content)
            else:
                return self._parse_encoded_format_optimized(content)
                
        except Exception as e:
            print(f"Error parsing Sudoku file: {e}")
            return None, []
    
    def _parse_grid_format(self, content):
        """Parse explicit grid format"""
        grid_data = None
        encoded_positions = []
        
        lines = content.split('\n')
        in_grid = False
        in_positions = False
        grid_lines = []
        
        for line in lines:
            line = line.strip()
            if line == "GRID:":
                in_grid = True
                in_positions = False
                continue
            elif line.startswith("POSITIONS:"):
                in_grid = False
                in_positions = True
                continue
                
            if in_grid and line and not line.startswith("POSITIONS:") and not line.startswith("Byte"):
                # Parse grid row
                try:
                    row = [int(x) for x in line.split()]
                    if len(row) == 9:
                        grid_lines.append(row)
                except:
                    continue
                    
            elif in_positions and "Byte" in line and " -> " in line:
                # Parse position data
                try:
                    byte_part = line.split(": (")[0]
                    idx = int(byte_part.replace("Byte", ""))
                    
                    pos_part = line.split(": (")[1].split(")=")
                    row_col = pos_part[0].split(",")
                    row = int(row_col[0]) - 1  # Convert to 0-based
                    col = int(row_col[1]) - 1
                    
                    value_byte = pos_part[1].split(" -> ")
                    value = int(value_byte[0])
                    byte_val = int(value_byte[1])
                    
                    encoded_positions.append({
                        'index': idx,
                        'row': row,
                        'col': col, 
                        'value': value,
                        'byte_value': byte_val
                    })
                except:
                    continue
        
        if len(grid_lines) == 9:
            grid_data = grid_lines
            
        return grid_data, encoded_positions
    
    def _parse_encoded_format_optimized(self, content):
        """Optimized parsing for encoded formats with metadata support"""
        encoded_positions = []
        grid_seed = None
        shuffle_key = None
        
        # Extract metadata if present
        actual_content = content
        if content.startswith("SUDOKU:"):
            # Extract metadata: SUDOKU:grid_seed:shuffle_key|data...
            if "|" in content:
                metadata_part, actual_content = content.split("|", 1)
            elif "\n" in content:
                metadata_part, actual_content = content.split("\n", 1)
            else:
                metadata_part = content
                actual_content = ""
                
            # Parse metadata: SUDOKU:grid_seed:shuffle_key
            parts = metadata_part.split(":")
            if len(parts) >= 3:
                grid_seed = parts[1] if parts[1] else None
                shuffle_key = parts[2] if parts[2] else None
        
        # Fast parsing based on format detection
        if actual_content.startswith("R") and "C" in actual_content:
            # Readable format - batch processing
            encoded_positions = self._parse_readable_format_batch(actual_content)
        elif "|" in actual_content:
            # Compact format - batch processing  
            encoded_positions = self._parse_compact_format_batch(actual_content)
        
        # Try to reconstruct grid with extracted metadata
        if grid_seed is not None:
            grid_data = self._reconstruct_grid_with_metadata(encoded_positions, grid_seed, shuffle_key)
        else:
            # Fallback to smart detection
            grid_data = self._reconstruct_grid_smart(encoded_positions)
        
        return grid_data, encoded_positions
    
    def _parse_readable_format_batch(self, content):
        """Batch parse readable format for better performance"""
        encoded_positions = []
        parts = content.strip().split()
        
        # Use regex for faster parsing
        pattern = re.compile(r'R(\d+)C(\d+)V(\d+)B(\d+)I(\d+)')
        
        for part in parts:
            match = pattern.match(part)
            if match:
                try:
                    row, col, value, byte_val, idx = map(int, match.groups())
                    encoded_positions.append({
                        'index': idx,
                        'row': row - 1,  # Convert to 0-based
                        'col': col - 1,
                        'value': value,
                        'byte_value': byte_val
                    })
                except:
                    continue
        
        return encoded_positions
    
    def _parse_compact_format_batch(self, content):
        """Batch parse compact format for better performance"""
        encoded_positions = []
        parts = content.strip().split("|")
        
        for part in parts:
            try:
                coords = part.split(",")
                if len(coords) >= 5:
                    row, col, value, byte_val, idx = map(int, coords[:5])
                    encoded_positions.append({
                        'index': idx,
                        'row': row,
                        'col': col,
                        'value': value,
                        'byte_value': byte_val
                    })
            except:
                continue
                
        return encoded_positions
    
    def _reconstruct_grid_with_metadata(self, encoded_positions, grid_seed, shuffle_key):
        """Reconstruct grid using extracted metadata"""
        try:
            from src import sudoku_mode
            
            # Convert grid_seed to proper format
            if isinstance(grid_seed, str):
                try:
                    seed = int(grid_seed.strip())
                except ValueError:
                    seed = sum(ord(c) for c in grid_seed.strip())
            else:
                seed = grid_seed
            
            # Generate the same grid used during encoding
            grid = sudoku_mode.generate_sudoku_grid(seed)
            
            # Create the same mapping used during encoding
            byte_to_position, position_to_byte = sudoku_mode.create_sudoku_mapping(grid, shuffle_key)
            
            # Verify that the grid matches by checking a few positions
            matches = 0
            total_checks = min(10, len(encoded_positions))
            
            for i in range(total_checks):
                pos = encoded_positions[i]
                if (0 <= pos['row'] < 9 and 0 <= pos['col'] < 9 and 
                    grid[pos['row']][pos['col']] == pos['value']):
                    matches += 1
            
            # If most positions match, we have the right grid
            if matches >= total_checks * 0.8:
                return grid
            else:
                print(f"Warning: Grid metadata reconstruction had {matches}/{total_checks} matches")
                return grid  # Return anyway, might still be usable
                
        except Exception as e:
            print(f"Error reconstructing grid with metadata: {e}")
            # Fallback to smart detection
            return self._reconstruct_grid_smart(encoded_positions)
    
    def _reconstruct_grid_smart(self, encoded_positions):
        """Smart grid reconstruction with fewer seed attempts"""
        if not encoded_positions:
            return None
            
        # Try most common seeds first
        priority_seeds = [12345, None, 54321, 42, 123, 1234, 0, 1]
        
        for seed in priority_seeds:
            if self._test_seed_match(seed, encoded_positions):
                from src import sudoku_mode
                return sudoku_mode.generate_sudoku_grid(seed)
        
        # If no quick match, try a few more common ones
        extended_seeds = [999, 456, 789, 2024, 2025, 1111, 5555]
        for seed in extended_seeds:
            if self._test_seed_match(seed, encoded_positions):
                from src import sudoku_mode
                return sudoku_mode.generate_sudoku_grid(seed)
                
        # Last resort: try ASCII sums of common words
        word_seeds = ['password', 'secret', 'test', 'key', 'data', 'file']
        for word in word_seeds:
            seed = sum(ord(c) for c in word)
            if self._test_seed_match(seed, encoded_positions):
                from src import sudoku_mode
                return sudoku_mode.generate_sudoku_grid(seed)
        
        # If still no match, use first few positions to make a basic grid
        return self._create_fallback_grid(encoded_positions)
    
    def _test_seed_match(self, seed, encoded_positions, max_test=10):
        """Test if seed matches by checking first few positions only"""
        try:
            from src import sudoku_mode
            test_grid = sudoku_mode.generate_sudoku_grid(seed)
            
            # Test only first few positions for speed
            test_count = min(max_test, len(encoded_positions))
            matches = 0
            
            for i in range(test_count):
                pos = encoded_positions[i]
                if (0 <= pos['row'] < 9 and 0 <= pos['col'] < 9 and 
                    test_grid[pos['row']][pos['col']] == pos['value']):
                    matches += 1
                    
            # If most positions match, it's probably the right seed
            return matches >= test_count * 0.8
            
        except:
            return False
    
    def _create_fallback_grid(self, encoded_positions):
        """Create a fallback grid when no seed matches"""
        # Create a basic grid with default values
        from src import sudoku_mode
        grid = sudoku_mode.generate_sudoku_grid(42)  # Use fixed seed for consistency
        
        # Override with known values from positions where they match
        for pos in encoded_positions:
            if 0 <= pos['row'] < 9 and 0 <= pos['col'] < 9:
                # Only override if the value is valid (1-9)
                if 1 <= pos['value'] <= 9:
                    grid[pos['row']][pos['col']] = pos['value']
        
        return grid

# Standalone function for compatibility with progress_handler
def show_sudoku_viewer(file_path, parent_window=None):
    """
    Show Sudoku viewer for the given file
    
    Args:
        file_path: Path to the Sudoku encoded file
        parent_window: Parent window (optional)
    """
    try:
        viewer = SudokuViewer(parent_window)
        viewer.show_sudoku_file(file_path)
    except Exception as e:
        raise Exception(f"Failed to open Sudoku viewer: {str(e)}")

# Test function for standalone use
def main():
    """Test the Sudoku viewer with a sample file"""
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            
            viewer = SudokuViewer()
            viewer.show_sudoku_file(file_path)
            
            root.mainloop()
        else:
            print(f"File not found: {file_path}")
    else:
        print("Usage: python sudoku_viewer.py <sudoku_file>")

if __name__ == "__main__":
    main()
