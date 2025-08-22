import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
import subprocess

class ProgressHandler:
    """
    Handles and displays progress bar when processing large files.
    Integrates error display and success result feedback.
    """
    def __init__(self, title="Processing", max_value=100):
        """
        Initialize the progress window.
        
        :param title: Window title
        :param max_value: Maximum value for the progress bar
        """
        self.window = tk.Toplevel()
        self.window.title(title)
        self.window.geometry("450x180")  # Initial size is wider
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.window.attributes("-topmost", True)
        
        # Center the window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Information label
        self.info_label = tk.Label(self.window, text="Processing file...", wraplength=430, justify="left", font=("Arial", 9))
        self.info_label.pack(pady=(10, 5))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.window, orient="horizontal", length=430, mode="determinate"
        )
        self.progress.pack(pady=5, padx=10)
        
        # Percentage label
        self.percent_label = tk.Label(self.window, text="0%")
        self.percent_label.pack(pady=5)
        
        # Button frame (initially hidden)
        self.btn_frame = tk.Frame(self.window)
        self.btn_frame.pack(pady=10)
        self.btn_frame.pack_forget()
        
        # Other attributes
        self.is_cancelled = False
        self.max_value = max_value
        self.completed = False
        self.output_file = None
        self.is_indeterminate = False
        
        # Ensure UI is updated
        self.window.update()
    
    def _on_closing(self):
        """Handle when user closes the window"""
        self.is_cancelled = True
        if self.completed:
            self.window.destroy()
    
    def open_file(self, file_path):
        """
        Open file in the operating system's default application.
        
        :param file_path: Path to the file to open
        """
        try:
            if sys.platform.startswith("darwin"):  # macOS
                subprocess.call(["open", file_path])
            elif os.name == "nt":  # Windows
                os.startfile(file_path)
            elif os.name == "posix":  # Linux/Unix
                subprocess.call(["xdg-open", file_path])
        except Exception as e:
            # Display error in current window if file can't be opened
            self.info_label.config(text=f"Could not open file:\n{str(e)}")
    
    def open_output_file(self):
        """
        Open output file in default application and temporarily turn off topmost window attribute.
        For Sudoku encoded files, opens custom Sudoku viewer instead.
        """
        if not self.output_file:
            return
        
        # Turn off topmost so the window doesn't block the opened application
        self.window.attributes("-topmost", False)
        
        # Check if this is a Sudoku encoded file
        if self._is_sudoku_file(self.output_file):
            self._open_sudoku_viewer(self.output_file)
        # Check if this is a Chess encoded file
        elif self._is_chess_file(self.output_file):
            self._open_chess_viewer(self.output_file)
        else:
            # Open the file normally
            self.open_file(self.output_file)
        
        # After opening the file, allow the window to be closed
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
    
    def _is_sudoku_file(self, file_path):
        """
        Check if a file contains Sudoku encoded data by examining its content
        
        :param file_path: Path to the file to check
        :return: True if file contains Sudoku encoded data
        """
        try:
            # Skip Python files and other code files
            if file_path.endswith(('.py', '.js', '.cpp', '.c', '.h', '.java')):
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Check for Sudoku format patterns
            # Grid format: contains "GRID:" and "POSITIONS:"
            if "GRID:" in content and "POSITIONS:" in content:
                # Additional validation - should contain typical Sudoku patterns
                lines = content.split('\n')
                grid_found = False
                positions_found = False
                
                for line in lines:
                    if line.strip() == "GRID:":
                        grid_found = True
                    elif line.startswith("POSITIONS:"):
                        positions_found = True
                    elif "Byte" in line and " -> " in line and positions_found:
                        return True  # Found position mapping
                        
                return grid_found and positions_found
                
            # Readable format: contains pattern like "R1C1V5B72I0"
            if content.startswith("R") and "C" in content and "V" in content and "B" in content and "I" in content:
                # Verify it's actually Sudoku readable format
                parts = content.split()
                if len(parts) > 0:
                    first_part = parts[0]
                    # Check pattern: R<num>C<num>V<num>B<num>I<num>
                    import re
                    pattern = r'R\d+C\d+V\d+B\d+I\d+'
                    if re.match(pattern, first_part):
                        # Additional check - should be mostly this pattern
                        valid_count = 0
                        for part in parts[:5]:  # Check first 5 parts
                            if re.match(pattern, part):
                                valid_count += 1
                        return valid_count >= 3  # At least 60% should match
            
            # Compact format: contains pattern like "1,2,3,72,0|4,5,6,101,1"
            if "|" in content and "," in content:
                parts = content.split("|")
                if len(parts) >= 2:  # Should have multiple parts
                    valid_parts = 0
                    for part in parts[:5]:  # Check first 5 parts
                        coords = part.split(",")
                        # Sudoku compact format has 5 elements: row,col,value,byte,index
                        if len(coords) == 5:
                            try:
                                # All should be integers, row/col should be 0-8
                                nums = [int(x) for x in coords]
                                if 0 <= nums[0] <= 8 and 0 <= nums[1] <= 8 and 1 <= nums[2] <= 9:
                                    valid_parts += 1
                            except ValueError:
                                pass
                    return valid_parts >= min(2, len(parts))  # At least 2 valid parts
            
            return False
            
        except Exception:
            return False
    
    def _is_chess_file(self, file_path):
        """
        Check if a file contains Chess encoded data by examining its content
        
        :param file_path: Path to the file to check
        :return: True if file contains Chess encoded data
        """
        try:
            # Skip Python files and other code files
            if file_path.endswith(('.py', '.js', '.cpp', '.c', '.h', '.java')):
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Check for Chess format patterns
            # Board format: contains "BOARD:" and "POSITIONS:" and "FEN:"
            if "BOARD:" in content and "POSITIONS:" in content and "FEN:" in content:
                # Additional validation - should contain chess piece symbols
                lines = content.split('\n')
                board_found = False
                positions_found = False
                fen_found = False
                
                for line in lines:
                    if line.strip() == "BOARD:":
                        board_found = True
                    elif line.startswith("FEN:"):
                        fen_found = True
                    elif line.startswith("POSITIONS:"):
                        positions_found = True
                    elif "Byte" in line and ":" in line and "=" in line and positions_found:
                        # Check for chess square notation pattern like "a1=♜S0"
                        if any(c in line for c in "abcdefgh") and any(c in line for c in "12345678"):
                            return True  # Found chess position mapping
                        
                return board_found and positions_found and fen_found
                
            # Only support compact format for Chess viewer (not readable format)
            # Compact format for chess: contains pattern like "1,2,r,0,72|4,5,n,1,101"
            # New format may start with "FEN:" line
            content_lines = content.strip().split('\n')
            
            # Check if it starts with FEN (new compact format)
            if content_lines[0].startswith("FEN:") and len(content_lines) > 1:
                # Check the positions line
                positions_line = content_lines[1]
                if "|" in positions_line and "," in positions_line:
                    parts = positions_line.split("|")
                    if len(parts) >= 2:  # Should have multiple parts
                        valid_parts = 0
                        for part in parts[:5]:  # Check first 5 parts
                            coords = part.split(",")
                            # Chess compact format has 5 elements: row,col,piece,sequence,index
                            if len(coords) == 5:
                                try:
                                    # Check if it's chess format (piece is not a number like in sudoku)
                                    row, col, piece, sequence, index = coords
                                    row_num, col_num = int(row), int(col)
                                    sequence_num, index_num = int(sequence), int(index)
                                    
                                    # Row/col should be 0-7 for chess (not 0-8 like sudoku)
                                    # Piece should be chess piece character
                                    if (0 <= row_num <= 7 and 0 <= col_num <= 7 and 
                                        piece in 'rnbqkpRNBQKP.' and 
                                        sequence_num >= 0 and index_num >= 0):
                                        valid_parts += 1
                                except (ValueError, IndexError):
                                    pass
                        return valid_parts >= min(2, len(parts))  # At least 2 valid parts
            
            # Old compact format (without FEN line)
            elif "|" in content and "," in content:
                parts = content.split("|")
                if len(parts) >= 2:  # Should have multiple parts
                    valid_parts = 0
                    for part in parts[:5]:  # Check first 5 parts
                        coords = part.split(",")
                        # Chess compact format has 5 elements: row,col,piece,sequence,index
                        if len(coords) == 5:
                            try:
                                # Check if it's chess format (piece is not a number like in sudoku)
                                row, col, piece, sequence, index = coords
                                row_num, col_num = int(row), int(col)
                                sequence_num, index_num = int(sequence), int(index)
                                
                                # Row/col should be 0-7 for chess (not 0-8 like sudoku)
                                # Piece should be chess piece character
                                if (0 <= row_num <= 7 and 0 <= col_num <= 7 and 
                                    piece in 'rnbqkpRNBQKP.' and 
                                    sequence_num >= 0 and index_num >= 0):
                                    valid_parts += 1
                            except (ValueError, IndexError):
                                pass
                    return valid_parts >= min(2, len(parts))  # At least 2 valid parts
            
            return False
            
        except Exception:
            return False
    
    def _open_sudoku_viewer(self, file_path):
        """
        Open Sudoku viewer for encoded Sudoku files
        
        :param file_path: Path to the Sudoku encoded file
        """
        try:
            # Import sudoku_viewer here to avoid circular imports
            from src.sudoku_viewer import show_sudoku_viewer
            
            # Show the Sudoku viewer
            show_sudoku_viewer(file_path, self.window)
            
        except Exception as e:
            # If Sudoku viewer fails, fall back to normal file opening
            messagebox.showerror("Sudoku Viewer Error", 
                               f"Could not open Sudoku viewer:\n{str(e)}\n\nOpening file normally...")
            self.open_file(file_path)
    
    def _open_chess_viewer(self, file_path):
        """
        Open Chess viewer for encoded Chess files
        
        :param file_path: Path to the Chess encoded file
        """
        try:
            # Import chess_viewer here to avoid circular imports
            from src.chess_viewer import show_chess_viewer
            
            # Show the Chess viewer
            show_chess_viewer(file_path, self.window)
            
        except Exception as e:
            # If Chess viewer fails, fall back to normal file opening
            messagebox.showerror("Chess Viewer Error", 
                               f"Could not open Chess viewer:\n{str(e)}\n\nOpening file normally...")
            self.open_file(file_path)
    
    def update_progress(self, current, total=None):
        """
        Update progress bar.
        
        :param current: Current value
        :param total: Total value (if different from max_value)
        """
        if self.is_cancelled:
            return
        
        max_val = total if total is not None else self.max_value
        percentage = min(100, int((current / max_val) * 100))
        
        # Update on the main GUI thread
        def update_gui():
            if not self.is_cancelled:
                self.progress["value"] = percentage
                self.percent_label.config(text=f"{percentage}%")
                self.info_label.config(text=f"Processing: {current}/{max_val} bytes")
                self.window.update()
        
        # Use after to update GUI from different thread
        if threading.current_thread() is not threading.main_thread():
            self.window.after(0, update_gui)
        else:
            update_gui()
    
    def set_indeterminate_mode(self, status_text=None):
        """
        Switch progress bar to indeterminate mode (loading).
        
        :param status_text: Status message to display
        """
        if self.is_cancelled:
            return
        
        def update_gui():
            if not self.is_cancelled:
                # Switch to indeterminate mode
                self.is_indeterminate = True
                self.progress.config(mode="indeterminate")
                self.progress.start(10)  # Start animation with 10ms speed
                
                # Hide percentage
                self.percent_label.config(text="")
                
                # Update message if provided
                if status_text:
                    self.info_label.config(text=status_text)
                    
                self.window.update()
        
        # Use after to update GUI from different thread
        if threading.current_thread() is not threading.main_thread():
            self.window.after(0, update_gui)
        else:
            update_gui()
            
    def update_additional_status(self, status_text):
        """
        Update additional status message and switch to indeterminate mode.
        
        :param status_text: Status message to display
        """
        if self.is_cancelled:
            return
        
        # If not in indeterminate mode, switch to it
        if not self.is_indeterminate:
            self.set_indeterminate_mode(status_text)
            return
            
        # If already in indeterminate mode, just update the message
        def update_gui():
            if not self.is_cancelled:
                self.info_label.config(text=status_text)
                self.window.update()
                
        # Use after to update GUI from different thread
        if threading.current_thread() is not threading.main_thread():
            self.window.after(0, update_gui)
        else:
            update_gui()
    
    def show_buttons(self, is_qr_mode=False, qr_content=None):
        """Display buttons after processing completes
        
        :param is_qr_mode: True if this is QR content display, False for normal file operations
        :param qr_content: The decoded content for export functionality
        """
        # Remove old buttons if any
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
        
        # For QR/Barcode mode, show OK and Export to TXT buttons
        if is_qr_mode:
            def export_to_txt():
                """Export the content to a TXT file"""
                try:
                    import os
                    from tkinter import messagebox
                    import datetime
                    
                    # Generate filename with timestamp
                    now = datetime.datetime.now()
                    filename = f"decoded_content_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}.txt"
                    
                    # Define output path (human_files directory)
                    human_files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "human_files")
                    output_path = os.path.join(human_files_dir, filename)
                    
                    # Write content to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(qr_content if qr_content else "")
                    
                    # Close current dialog
                    self.window.destroy()
                    
                    # Show success message with options
                    result = messagebox.askyesno(
                        "Export Successful", 
                        f"Content exported successfully to:\n{output_path}\n\nWould you like to open the file?",
                        icon="question"
                    )
                    
                    if result:
                        # Open the file
                        import subprocess
                        import platform
                        
                        if platform.system() == 'Windows':
                            os.startfile(output_path)
                        elif platform.system() == 'Darwin':  # macOS
                            subprocess.call(['open', output_path])
                        else:  # Linux and others
                            subprocess.call(['xdg-open', output_path])
                            
                except Exception as e:
                    from tkinter import messagebox
                    messagebox.showerror("Export Error", f"Failed to export content:\n{str(e)}")
            
            # OK button
            ok_btn = tk.Button(
                self.btn_frame, 
                text="OK", 
                command=self.window.destroy, 
                width=15,
                height=2,
                font=("Arial", 10, "bold")
            )
            ok_btn.pack(side="left", padx=8)
            
            # Export to TXT button
            export_btn = tk.Button(
                self.btn_frame, 
                text="Export to TXT", 
                command=export_to_txt, 
                width=15,
                height=2,
                font=("Arial", 10, "bold")
            )
            export_btn.pack(side="left", padx=8)
        else:
            # Normal mode: show Open File button if there's an output file
            if self.output_file:
                open_btn = tk.Button(
                    self.btn_frame, 
                    text="Open File", 
                    command=lambda: self.open_output_file(), 
                    width=15,
                    height=2,
                    font=("Arial", 10, "bold")
                )
                open_btn.pack(side="left", padx=8)
            
            # OK button to close the window
            ok_btn = tk.Button(
                self.btn_frame, 
                text="OK", 
                command=self.window.destroy, 
                width=15,
                height=2,
                font=("Arial", 10, "bold")
            )
            ok_btn.pack(side="left", padx=8)
        
        # Unpack the button frame first if it's already packed
        if self.btn_frame.winfo_ismapped():
            self.btn_frame.pack_forget()
            
        # Now pack it at the bottom
        self.btn_frame.pack(side="bottom", pady=15)
        
        # Update the window to ensure changes are visible
        self.window.update()
        
    def complete(self, success=True, error_msg=None, output_file=None, qr_content=None, barcode_content=None):
        """
        Mark the processing as completed
        
        :param success: True if processing was successful, False if error
        :param error_msg: Error message (if any)
        :param output_file: Path to the output file (if any)
        :param qr_content: QR code content for special QR display
        :param barcode_content: Barcode content for special Barcode display
        """
        self.output_file = output_file
        
        def finish():
            if not self.window.winfo_exists():
                return
            
            # Stop indeterminate animation if running
            if self.is_indeterminate:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self.is_indeterminate = False
                
            # Increase window size when completed to show more information and buttons
            self.window.geometry("500x300")  # Increased size for file name, full path and buttons
            
            # Clear previous widgets from the window's layout
            for widget in self.window.winfo_children():
                if widget != self.btn_frame and widget != self.info_label and widget != self.progress and widget != self.percent_label:
                    widget.destroy()
            
            if success:
                self.window.title("Success")
                self.progress["value"] = 100
                self.percent_label.config(text="100%")
                
                if qr_content is not None:
                    # Special handling for QR Code content
                    self.info_label.config(text="QR Code decoded successfully!")
                    
                    # Create a new frame for the QR content
                    content_info_frame = tk.Frame(self.window)
                    content_info_frame.pack(pady=(5,0), padx=10, fill="both", expand=True)
                    
                    # Display QR content instead of file path
                    content_text = f"Content: {qr_content}"
                    content_label = tk.Label(
                        content_info_frame, 
                        text=content_text,
                        font=("Arial", 10, "bold"),
                        fg="blue",
                        wraplength=430,
                        justify="left",
                        anchor="w"
                    )
                    content_label.pack(fill="x", anchor="w")
                    
                elif barcode_content is not None:
                    # Special handling for Barcode content
                    self.info_label.config(text="Barcode decoded successfully!")
                    
                    # Create a new frame for the Barcode content
                    content_info_frame = tk.Frame(self.window)
                    content_info_frame.pack(pady=(5,0), padx=10, fill="both", expand=True)
                    
                    # Display Barcode content instead of file path
                    content_text = f"Content: {barcode_content}"
                    content_label = tk.Label(
                        content_info_frame, 
                        text=content_text,
                        font=("Arial", 10, "bold"),
                        fg="green",  # Different color for barcode
                        wraplength=430,
                        justify="left",
                        anchor="w"
                    )
                    content_label.pack(fill="x", anchor="w")
                    
                elif output_file:
                    # Clear current info label
                    self.info_label.config(text="Processing completed!")
                    
                    # Create a new frame for the file path info
                    file_info_frame = tk.Frame(self.window)
                    file_info_frame.pack(pady=(5,0), padx=10, fill="both", expand=True)
                    
                    # Get file path info
                    base_name = os.path.basename(output_file)
                    
                    # Display full path in blue like the Image Note styling
                    path_text = f"Path: {output_file}"
                    path_label = tk.Label(
                        file_info_frame, 
                        text=path_text,
                        font=("Arial", 10, "bold"),
                        fg="blue",
                        wraplength=430,
                        justify="left",
                        anchor="w"
                    )
                    path_label.pack(fill="x", anchor="w")
                else:
                    self.info_label.config(text="Processing completed!")
            else:
                self.window.title("Error")
                self.progress["value"] = 0
                self.percent_label.config(text="Error")
                self.info_label.config(text=f"Error: {error_msg or 'Unknown error'}")
            
            self.completed = True
            
            # Turn off topmost so window doesn't block view
            self.window.attributes("-topmost", False)
            
            self.window.update()
            
            # Display buttons (will handle QR vs file mode differently)
            self.show_buttons(is_qr_mode=(qr_content is not None), qr_content=qr_content)
        
        if threading.current_thread() is not threading.main_thread():
            self.window.after(0, finish)
        else:
            finish()
    
    @staticmethod
    def show_success(title: str, filepath_or_content: str, is_qr_content=False, is_barcode_content=False):
        """
        Display success notification window with formatted filename and path
        shown clearly, or QR/Barcode content for QR/Barcode mode.
        
        :param title: Window title
        :param filepath_or_content: Path to the result file or QR/Barcode content
        :param is_qr_content: True if this is QR content, False if file path
        :param is_barcode_content: True if this is Barcode content, False if file path
        """
        dialog = tk.Toplevel()
        dialog.title(title)
        dialog.geometry("500x190")
        dialog.resizable(False, False)
        
        # Center window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Title notification
        title_label = tk.Label(dialog, text=f"{title}:", font=("Arial", 10))
        title_label.pack(pady=(10, 5), padx=10, anchor="w")
        
        # Button frame
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=(10, 5), side="bottom")
        
        # Information frame
        info_frame = tk.Frame(dialog)
        info_frame.pack(pady=5, padx=10, fill="both", expand=True)
        
        if is_qr_content:
            # Display QR content instead of file path
            content_text = f"Content: {filepath_or_content}"
            content_label = tk.Label(
                info_frame, 
                text=content_text,
                font=("Arial", 10, "bold"),
                fg="blue",
                wraplength=480,
                justify="left",
                anchor="w"
            )
            content_label.pack(fill="x", anchor="w")
        elif is_barcode_content:
            # Display Barcode content instead of file path
            content_text = f"Content: {filepath_or_content}"
            content_label = tk.Label(
                info_frame, 
                text=content_text,
                font=("Arial", 10, "bold"),
                fg="green",  # Different color for barcode
                wraplength=480,
                justify="left",
                anchor="w"
            )
            content_label.pack(fill="x", anchor="w")
        
        if is_qr_content or is_barcode_content:
            
            def close_dialog():
                dialog.destroy()
            
            def export_to_txt():
                """Export the content to a TXT file"""
                try:
                    # Import here to avoid circular import
                    import os
                    from tkinter import messagebox
                    import datetime
                    
                    # Generate filename with timestamp
                    now = datetime.datetime.now()
                    filename = f"decoded_content_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}.txt"
                    
                    # Define output path (human_files directory)
                    human_files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "human_files")
                    output_path = os.path.join(human_files_dir, filename)
                    
                    # Write content to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(filepath_or_content)
                    
                    # Close current dialog
                    dialog.destroy()
                    
                    # Show success message with options
                    result = messagebox.askyesno(
                        "Export Successful", 
                        f"Content exported successfully to:\n{output_path}\n\nWould you like to open the file?",
                        icon="question"
                    )
                    
                    if result:
                        # Open the file
                        import subprocess
                        import platform
                        
                        if platform.system() == 'Windows':
                            os.startfile(output_path)
                        elif platform.system() == 'Darwin':  # macOS
                            subprocess.call(['open', output_path])
                        else:  # Linux and others
                            subprocess.call(['xdg-open', output_path])
                            
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export content:\n{str(e)}")
            
            # Buttons for QR/Barcode content mode
            ok_btn = tk.Button(btn_frame, text="OK", command=close_dialog, width=10)
            ok_btn.pack(side="left", padx=5)
            
            export_btn = tk.Button(btn_frame, text="Export to TXT", command=export_to_txt, width=12)
            export_btn.pack(side="left", padx=5)
            
        else:
            # Normal file path handling
            filepath = filepath_or_content
            base_name = os.path.basename(filepath)
            
            # Truncate long filenames - show first 15 and last 10 chars + extension
            if len(base_name) > 30:
                name_part, ext = os.path.splitext(base_name)
                if len(name_part) > 25:
                    truncated_name = name_part[:15] + "..." + name_part[-10:] + ext
                    display_path = filepath.replace(base_name, truncated_name)
                else:
                    display_path = filepath
            else:
                display_path = filepath
                
            # Display full path in blue like the Image Note styling
            path_text = f"Path: {display_path}"
            path_label = tk.Label(
                info_frame, 
                text=path_text,
                font=("Arial", 10, "bold"),
                fg="blue",
                wraplength=480,
                justify="left",
                anchor="w"
            )
            path_label.pack(fill="x", anchor="w")
            
            def close_dialog():
                dialog.destroy()
            
            # OK Button
            ok_btn = tk.Button(btn_frame, text="OK", command=close_dialog, width=10)
            ok_btn.pack(side="left", padx=5)
            
            # Open File Button
            def open_file_func():
                try:
                    if sys.platform.startswith("darwin"):
                        subprocess.call(["open", filepath])
                    elif os.name == "nt":
                        os.startfile(filepath)
                    elif os.name == "posix":
                        subprocess.call(["xdg-open", filepath])
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file:\n{str(e)}")
            
            open_btn = tk.Button(btn_frame, text="Open File", command=open_file_func, width=10)
            open_btn.pack(side="left", padx=5)
        
        # Configure dialog
        dialog.transient()
        dialog.grab_set()
        dialog.wait_window()
