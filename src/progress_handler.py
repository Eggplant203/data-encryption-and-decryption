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
        Open output file in default application and temporarily turn off topmost window attribute
        """
        if not self.output_file:
            return
        
        # Turn off topmost so the window doesn't block the opened application
        self.window.attributes("-topmost", False)
        
        # Open the file
        self.open_file(self.output_file)
        
        # After opening the file, allow the window to be closed
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
    
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
    
    def show_buttons(self):
        """Display buttons after processing completes"""
        # Remove old buttons if any
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
        
        # If there's an output file, add open file button
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
        
        # Display button frame at the bottom
        self.btn_frame.pack(side="bottom", pady=15)
        
    def complete(self, success=True, error_msg=None, output_file=None):
        """
        Mark the processing as completed
        
        :param success: True if processing was successful, False if error
        :param error_msg: Error message (if any)
        :param output_file: Path to the output file (if any)
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
            
            if success:
                self.window.title("Success")
                self.progress["value"] = 100
                self.percent_label.config(text="100%")
                
                if output_file:
                    # Clear current info label
                    self.info_label.config(text="Processing completed!")
                    
                    # Create frame to hold file info for better UI control
                    file_info_frame = tk.Frame(self.window)
                    file_info_frame.pack(before=self.btn_frame, pady=(5,0), padx=10, fill="both", expand=True)
                    
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
            
            # Display buttons
            self.show_buttons()
        
        if threading.current_thread() is not threading.main_thread():
            self.window.after(0, finish)
        else:
            finish()
    
    @staticmethod
    def show_success(title: str, filepath: str):
        """
        Display success notification window with formatted filename and path
        shown clearly.
        
        :param title: Window title
        :param filepath: Path to the result file
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
        
        # Get file path information
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
