# Admin Debug Module
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import sys
import os
import subprocess


class KonamiCodeHandler:
    """Handle the secret Konami code sequence for debug access"""
    
    def __init__(self):
        # Full Konami code sequence
        self.sequence = [
            'Up', 'Up', 'Down', 'Down', 'Left', 'Right', 'Left', 'Right', 'b', 'a', 'Return'
        ]  
        self.current_sequence = []
        self.last_input_time = 0
        self.timeout = 2.5  # seconds timeout between inputs
        self.triggered = False
        self.debug_enabled = False
        self.pressed_keys = set()  # Track currently pressed keys
        self.processed_keys = set()  # Track keys that have been processed in current press cycle
        self.listening_mode = False  # Track if we're in listening mode
        self.listening_start_time = 0  # When listening mode started
        self.timeout_timer_id = None  # Timer ID for auto timeout
        
    def start_listening(self):
        """Start listening for Konami code sequence"""
        # Cancel any existing timeout timer
        if self.timeout_timer_id:
            self.timeout_timer_id.cancel()
            
        self.listening_mode = True
        self.listening_start_time = time.time()
        self.current_sequence = []
        self.last_input_time = self.listening_start_time
        self.pressed_keys.clear()
        self.processed_keys.clear()
        
        # Start timeout timer
        self._schedule_timeout()
        
        print("DEBUG: Started listening for Konami code sequence")
    
    def stop_listening(self, reason=""):
        """Stop listening for Konami code sequence"""
        if self.listening_mode:
            # Cancel timeout timer
            if self.timeout_timer_id:
                self.timeout_timer_id.cancel()
                self.timeout_timer_id = None
                
            self.listening_mode = False
            self.current_sequence = []
            self.last_input_time = 0
            self.listening_start_time = 0
            self.pressed_keys.clear()
            self.processed_keys.clear()
            print(f"DEBUG: Stopped listening for Konami code{' - ' + reason if reason else ''}")
    
    def _schedule_timeout(self):
        """Schedule a timeout check"""
        if self.timeout_timer_id:
            self.timeout_timer_id.cancel()
            
        def check_timeout():
            if self.listening_mode:
                current_time = time.time()
                time_since_last_input = current_time - self.last_input_time
                if time_since_last_input >= self.timeout:
                    print(f"DEBUG: Timeout exceeded ({time_since_last_input:.2f}s), stopping listening")
                    self.stop_listening("timeout")
                else:
                    # Schedule next check
                    remaining_time = self.timeout - time_since_last_input
                    self.timeout_timer_id = threading.Timer(remaining_time, check_timeout)
                    self.timeout_timer_id.start()
        
        self.timeout_timer_id = threading.Timer(self.timeout, check_timeout)
        self.timeout_timer_id.start()
    
    def is_listening(self):
        """Check if currently in listening mode"""
        return self.listening_mode
        
    def reset_sequence(self):
        """Reset the current sequence and stop listening"""
        self.stop_listening("sequence reset")
    
    def handle_key_press(self, key):
        """Handle key press - only count once per press cycle"""
        # Only process if we're in listening mode
        if not self.listening_mode:
            return False
            
        current_time = time.time()
        
        # If key is already pressed and processed, ignore
        if key in self.pressed_keys and key in self.processed_keys:
            return False
            
        # Add to pressed keys
        self.pressed_keys.add(key)
        
        # If already processed this key in current press cycle, ignore
        if key in self.processed_keys:
            return False
            
        # Mark as processed
        self.processed_keys.add(key)
        
        # Update last input time and reschedule timeout
        self.last_input_time = current_time
        
        # Log all key presses for debugging
        expected_key = self.sequence[len(self.current_sequence)] if len(self.current_sequence) < len(self.sequence) else 'none'
        print(f"DEBUG: Key pressed: '{key}' (expected: '{expected_key}', position: {len(self.current_sequence) + 1}/{len(self.sequence)})")
        
        # Check if this is the expected next key
        expected_index = len(self.current_sequence)
        if expected_index < len(self.sequence) and key == self.sequence[expected_index]:
            self.current_sequence.append(key)
            print(f"DEBUG: ✓ Correct key '{key}' at position {expected_index + 1}/{len(self.sequence)}")
            
            # Reschedule timeout for next key
            self._schedule_timeout()
            
            # Check if sequence is complete
            if len(self.current_sequence) == len(self.sequence):
                print("DEBUG: 🎉 Konami code completed!")
                self.triggered = True
                self.stop_listening("sequence completed")
                return True
        else:
            # Wrong key, stop listening
            if expected_index < len(self.sequence):
                expected_key = self.sequence[expected_index]
                print(f"DEBUG: ✗ Wrong key '{key}', expected '{expected_key}', stopping listening")
            else:
                print(f"DEBUG: ✗ Unexpected key '{key}', stopping listening")
            self.stop_listening("wrong key")
            
        return False
    
    def handle_key_release(self, key):
        """Handle key release - remove from pressed keys"""
        # Only process if we're in listening mode
        if not self.listening_mode:
            return
            
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
        if key in self.processed_keys:
            self.processed_keys.remove(key)
    
    def add_input(self, key):
        """Add a key input to the sequence - DEPRECATED, use handle_key_press instead"""
        return self.handle_key_press(key)
    
    def is_triggered(self):
        """Check if the Konami code was triggered"""
        return self.triggered
    
    def consume_trigger(self):
        """Consume the trigger (set it to False)"""
        self.triggered = False


class DebugWindow:
    """Debug window for admin functions"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.start_time = time.time()  # Track start time for uptime command
        
    def show(self):
        """Show the debug window"""
        if self.window is not None:
            # Window already exists, just bring it to front
            self.window.lift()
            self.window.focus_force()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("Debug Console - Admin Access")
        self.window.geometry("800x600")
        
        # Make it modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"800x600+{x}+{y}")
        
        self.create_widgets()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def create_widgets(self):
        """Create the debug window widgets"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # System Info Tab
        sys_frame = ttk.Frame(notebook)
        notebook.add(sys_frame, text="System Info")
        self.create_system_info_tab(sys_frame)
        
        # Files Tab  
        files_frame = ttk.Frame(notebook)
        notebook.add(files_frame, text="Files")
        self.create_files_tab(files_frame)
        
        # Debug Log Tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Debug Log")
        self.create_debug_log_tab(log_frame)
        
        # Tools Tab
        tools_frame = ttk.Frame(notebook)
        notebook.add(tools_frame, text="Tools")
        self.create_tools_tab(tools_frame)
        
        # Performance Monitoring Tab
        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="Performance")
        self.create_performance_tab(perf_frame)
        
        # Mode Testing Tab
        test_frame = ttk.Frame(notebook)
        notebook.add(test_frame, text="Mode Testing")
        self.create_mode_testing_tab(test_frame)
        
        # Security Audit Tab
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Security")
        self.create_security_tab(security_frame)
        
    def create_system_info_tab(self, parent):
        """Create system information tab"""
        # Create scrolled text widget
        text_widget = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 10))
        text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Get system info
        info = []
        info.append("=== SYSTEM INFORMATION ===")
        info.append(f"Python Version: {sys.version}")
        info.append(f"Platform: {sys.platform}")
        info.append(f"Current Working Directory: {os.getcwd()}")
        info.append(f"Python Path: {sys.executable}")
        info.append("")
        
        info.append("=== ENVIRONMENT VARIABLES ===")
        for key, value in sorted(os.environ.items()):
            info.append(f"{key}: {value}")
        
        info.append("")
        info.append("=== PYTHON MODULES ===")
        for module_name in sorted(sys.modules.keys()):
            module = sys.modules[module_name]
            if hasattr(module, '__file__') and module.__file__:
                info.append(f"{module_name}: {module.__file__}")
            else:
                info.append(f"{module_name}: <built-in>")
        
        # Insert all info
        text_widget.insert("1.0", "\n".join(info))
        # Don't set to disabled so admin can edit if needed
        # text_widget.config(state="disabled")
        
    def create_files_tab(self, parent):
        """Create files management tab"""
        # File listing
        tk.Label(parent, text="Workspace Files:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        files_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 9), height=15)
        files_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Get file listing
        file_info = []
        for root, dirs, files in os.walk("."):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            
            level = root.replace(".", "").count(os.sep)
            indent = "  " * level
            file_info.append(f"{indent}{os.path.basename(root)}/")
            
            sub_indent = "  " * (level + 1)
            for file in sorted(files):
                if not file.endswith(".pyc"):
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        file_info.append(f"{sub_indent}{file} ({size} bytes)")
                    except:
                        file_info.append(f"{sub_indent}{file} (size unknown)")
        
        files_text.insert("1.0", "\n".join(file_info))
        # Don't set to disabled so admin can view and edit
        # files_text.config(state="disabled")
        
        # Refresh button
        def refresh_files():
            files_text.delete("1.0", "end")
            # Re-create file listing
            file_info = []
            for root, dirs, files in os.walk("."):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                
                level = root.replace(".", "").count(os.sep)
                indent = "  " * level
                file_info.append(f"{indent}{os.path.basename(root)}/")
                
                sub_indent = "  " * (level + 1)
                for file in sorted(files):
                    if not file.endswith(".pyc"):
                        file_path = os.path.join(root, file)
                        try:
                            size = os.path.getsize(file_path)
                            file_info.append(f"{sub_indent}{file} ({size} bytes)")
                        except:
                            file_info.append(f"{sub_indent}{file} (size unknown)")
            
            files_text.insert("1.0", "\n".join(file_info))
            # Don't disable so it remains editable
            
        tk.Button(parent, text="Refresh File List", command=refresh_files).pack(pady=5)
        
    def create_debug_log_tab(self, parent):
        """Create debug log tab"""
        tk.Label(parent, text="Debug Log:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add some initial log entries
        initial_log = [
            "[DEBUG] Debug window opened",
            "[INFO] Admin access granted via Konami code",
            "[SYSTEM] Debug mode activated",
        ]
        
        for entry in initial_log:
            self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} {entry}\n")
        
        # Auto-scroll to bottom
        self.log_text.see("end")
        
        # Clear log button
        def clear_log():
            self.log_text.delete("1.0", "end")
            self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [SYSTEM] Log cleared\n")
        
        def toggle_monitoring():
            """Toggle real-time monitoring"""
            if hasattr(self, 'monitoring_active') and self.monitoring_active:
                self.monitoring_active = False
                monitor_btn.config(text="Start Monitoring")
                self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [SYSTEM] Real-time monitoring stopped\n")
            else:
                self.monitoring_active = True
                monitor_btn.config(text="Stop Monitoring")
                self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [SYSTEM] Real-time monitoring started\n")
                self.start_monitoring()
        
        def export_log():
            """Export log to file"""
            try:
                log_content = self.log_text.get("1.0", "end-1c")
                filename = f"debug_log_{time.strftime('%Y%m%d_%H%M%S')}.txt"
                filepath = os.path.join("machine_files", filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                
                messagebox.showinfo("Export Success", f"Log exported to: {filepath}")
                self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [SYSTEM] Log exported to {filepath}\n")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not export log: {e}")
        
        log_buttons = tk.Frame(parent)
        log_buttons.pack(fill="x", padx=5, pady=5)
            
        tk.Button(log_buttons, text="Clear Log", command=clear_log).pack(side="left", padx=2)
        monitor_btn = tk.Button(log_buttons, text="Start Monitoring", command=toggle_monitoring)
        monitor_btn.pack(side="left", padx=2)
        tk.Button(log_buttons, text="Export Log", command=export_log).pack(side="left", padx=2)
        
        # Initialize monitoring state
        self.monitoring_active = False
        
    def create_tools_tab(self, parent):
        """Create tools tab"""
        # Tools section
        tk.Label(parent, text="Debug Tools:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        tools_frame = tk.Frame(parent)
        tools_frame.pack(fill="x", padx=5, pady=5)
        
        def show_memory_usage():
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                messagebox.showinfo("Memory Usage", 
                    f"RSS Memory: {memory_info.rss / 1024 / 1024:.2f} MB\n"
                    f"VMS Memory: {memory_info.vms / 1024 / 1024:.2f} MB")
            except ImportError:
                messagebox.showinfo("Memory Usage", "psutil module not available")
        
        def force_garbage_collect():
            import gc
            collected = gc.collect()
            messagebox.showinfo("Garbage Collection", f"Collected {collected} objects")
        
        def show_thread_info():
            thread_count = threading.active_count()
            thread_list = threading.enumerate()
            thread_info = f"Active threads: {thread_count}\n\nThread details:\n"
            for i, thread in enumerate(thread_list, 1):
                thread_info += f"{i}. {thread.name} ({'alive' if thread.is_alive() else 'dead'})\n"
            
            messagebox.showinfo("Thread Information", thread_info)
        
        def open_viewers():
            """Open Chess and Sudoku viewers for testing"""
            try:
                from src.chess_viewer import show_chess_viewer
                from src.sudoku_viewer import show_sudoku_viewer
                from tkinter import filedialog
                
                def open_chess():
                    # Try to find encoded chess files first in both directories
                    chess_files = []
                    for search_dir in ["machine_files", "human_files"]:
                        if os.path.exists(search_dir):
                            for root, dirs, files in os.walk(search_dir):
                                for file in files:
                                    if ("chess" in file.lower() and "encoded" in file.lower()) or \
                                       (file.lower().endswith('.txt') and self.is_chess_encoded_file(os.path.join(root, file))):
                                        chess_files.append(os.path.join(root, file))
                    
                    if chess_files:
                        # Use the first encoded chess file found
                        show_chess_viewer(chess_files[0], self.window)
                        self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [VIEWER] Opened Chess viewer with: {chess_files[0]}\n")
                        self.log_text.see("end")
                        viewer_window.destroy()  # Close the viewer selection dialog
                    else:
                        # Let user select a file
                        file_path = filedialog.askopenfilename(
                            parent=self.window,
                            title="Select Chess encoded file",
                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
                        )
                        if file_path:
                            show_chess_viewer(file_path, self.window)
                            self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [VIEWER] Opened Chess viewer with: {file_path}\n")
                            self.log_text.see("end")
                            viewer_window.destroy()  # Close the viewer selection dialog
                        else:
                            messagebox.showinfo("Info", "No chess file selected. Create a chess-encoded file first.")
                
                def open_sudoku():
                    # Try to find encoded sudoku files first in both directories
                    sudoku_files = []
                    for search_dir in ["machine_files", "human_files"]:
                        if os.path.exists(search_dir):
                            for root, dirs, files in os.walk(search_dir):
                                for file in files:
                                    if ("sudoku" in file.lower() and "encoded" in file.lower()) or \
                                       (file.lower().endswith('.txt') and self.is_sudoku_encoded_file(os.path.join(root, file))):
                                        sudoku_files.append(os.path.join(root, file))
                    
                    if sudoku_files:
                        # Use the first encoded sudoku file found
                        show_sudoku_viewer(sudoku_files[0], self.window)
                        self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [VIEWER] Opened Sudoku viewer with: {sudoku_files[0]}\n")
                        self.log_text.see("end")
                        viewer_window.destroy()  # Close the viewer selection dialog
                    else:
                        # Let user select a file
                        file_path = filedialog.askopenfilename(
                            parent=self.window,
                            title="Select Sudoku encoded file",
                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
                        )
                        if file_path:
                            show_sudoku_viewer(file_path, self.window)
                            self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [VIEWER] Opened Sudoku viewer with: {file_path}\n")
                            self.log_text.see("end")
                            viewer_window.destroy()  # Close the viewer selection dialog
                        else:
                            messagebox.showinfo("Info", "No sudoku file selected. Create a sudoku-encoded file first.")
                
                def create_test_files():
                    """Create sample test files for viewers"""
                    try:
                        # Ensure machine_files directory exists
                        if not os.path.exists("machine_files"):
                            os.makedirs("machine_files")
                        
                        test_data = "Hello, World! This is test data for debug viewers."
                        
                        # Create hidden chess test file with FEN (machine use)
                        from src import chess_mode
                        chess_encoded = chess_mode.encode(test_data.encode('utf-8'), 
                                                        chess_fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
                        chess_path = os.path.join("machine_files", ".debug_chess_test.txt")
                        with open(chess_path, 'w', encoding='utf-8') as f:
                            f.write(chess_encoded)
                        
                        # Create hidden sudoku test file with seed (machine use)
                        from src import sudoku_mode
                        sudoku_encoded = sudoku_mode.encode(test_data.encode('utf-8'), 
                                                          grid_seed='12345')
                        sudoku_path = os.path.join("machine_files", ".debug_sudoku_test.txt")
                        with open(sudoku_path, 'w', encoding='utf-8') as f:
                            f.write(sudoku_encoded)
                        
                        messagebox.showinfo("Success", f"Created hidden debug test files:\n- {chess_path}\n- {sudoku_path}")
                        self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [FILE] Created hidden debug test files in machine_files/\n")
                        self.log_text.see("end")
                        
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not create test files: {e}")
                        self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [ERROR] Failed to create test files: {e}\n")
                        self.log_text.see("end")
                
                # Create viewer selection dialog
                viewer_window = tk.Toplevel(self.window)
                viewer_window.title("Open Viewers")
                viewer_window.geometry("320x180")
                viewer_window.transient(self.window)
                viewer_window.grab_set()
                
                # Center the window
                viewer_window.update_idletasks()
                x = (viewer_window.winfo_screenwidth() // 2) - (320 // 2)
                y = (viewer_window.winfo_screenheight() // 2) - (180 // 2)
                viewer_window.geometry(f"320x180+{x}+{y}")
                
                tk.Label(viewer_window, text="Select viewer to open:", font=("Arial", 10, "bold")).pack(pady=10)
                
                button_frame = tk.Frame(viewer_window)
                button_frame.pack(pady=10)
                
                tk.Button(button_frame, text="Chess Viewer", command=open_chess, width=12).pack(side="left", padx=5)
                tk.Button(button_frame, text="Sudoku Viewer", command=open_sudoku, width=12).pack(side="left", padx=5)
                
                tk.Label(viewer_window, text="No encoded files found?", font=("Arial", 9)).pack(pady=(10,2))
                tk.Button(viewer_window, text="Create Test Files", command=create_test_files, width=20).pack(pady=2)
                
            except ImportError as e:
                messagebox.showerror("Error", f"Could not import viewers: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Viewer error: {e}")
        
        def analyze_project_structure():
            """Analyze and display project structure"""
            structure_info = []
            structure_info.append("=== PROJECT STRUCTURE ANALYSIS ===\n")
            
            # Count files by type
            file_counts = {}
            total_size = 0
            
            for root, dirs, files in os.walk("."):
                # Skip hidden directories and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if not file.startswith('.') and not file.endswith('.pyc'):
                        ext = os.path.splitext(file)[1].lower() or 'no_ext'
                        file_counts[ext] = file_counts.get(ext, 0) + 1
                        
                        try:
                            file_path = os.path.join(root, file)
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
            
            structure_info.append(f"Total project size: {total_size / 1024 / 1024:.2f} MB\n")
            structure_info.append("Files by extension:")
            
            for ext, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True):
                structure_info.append(f"  {ext}: {count} files")
            
            # Show in a new window
            info_window = tk.Toplevel(self.window)
            info_window.title("Project Structure Analysis")
            info_window.geometry("500x400")
            
            info_text = scrolledtext.ScrolledText(info_window, wrap=tk.WORD, font=("Consolas", 10))
            info_text.pack(fill="both", expand=True, padx=10, pady=10)
            info_text.insert("1.0", "\n".join(structure_info))
            # Keep it editable for admin to add notes
            # info_text.config(state="disabled")
        
        def test_all_modes():
            """Quick test all encryption modes"""
            test_window = tk.Toplevel(self.window)
            test_window.title("Mode Compatibility Test")
            test_window.geometry("600x500")
            
            test_text = scrolledtext.ScrolledText(test_window, wrap=tk.WORD, font=("Consolas", 9))
            test_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            test_data = b"Hello, World! Test data 123."
            modes_to_test = [
                ('Base64', 'base64_mode'),
                ('Base32', 'base32_mode'),
                ('Hex', 'hex_mode'),
                ('Binary', 'binary_mode'),
            ]
            
            test_text.insert("end", f"Testing {len(modes_to_test)} modes with data: {test_data}\n\n")
            
            for mode_name, module_name in modes_to_test:
                try:
                    import importlib
                    module = importlib.import_module(f"src.{module_name}")
                    
                    # Test encode
                    encoded = module.encode(test_data)
                    test_text.insert("end", f"✓ {mode_name}: Encode successful\n")
                    
                    # Test decode
                    decoded = module.decode(encoded)
                    if decoded == test_data:
                        test_text.insert("end", f"✓ {mode_name}: Round-trip successful\n")
                    else:
                        test_text.insert("end", f"✗ {mode_name}: Round-trip FAILED\n")
                        
                except Exception as e:
                    test_text.insert("end", f"✗ {mode_name}: ERROR - {str(e)}\n")
                
                test_text.see("end")
                test_window.update()  # Update display immediately
        
        def open_directories():
            """Quick access to open important directories"""
            dir_window = tk.Toplevel(self.window)
            dir_window.title("Quick Directory Access")
            dir_window.geometry("300x200")
            dir_window.transient(self.window)
            
            tk.Label(dir_window, text="Open Directory:", font=("Arial", 10, "bold")).pack(pady=10)
            
            def open_dir(path):
                if os.path.exists(path):
                    try:
                        if sys.platform == "win32":
                            os.startfile(path)
                        elif sys.platform == "darwin":
                            subprocess.run(["open", path])
                        else:
                            subprocess.run(["xdg-open", path])
                    except:
                        messagebox.showerror("Error", f"Could not open directory: {path}")
                else:
                    messagebox.showwarning("Warning", f"Directory does not exist: {path}")
            
            dirs = [
                ("Human Files", "human_files"),
                ("Machine Files", "machine_files"),
                ("Source Code", "src"),
                ("Project Root", "."),
            ]
            
            for name, path in dirs:
                btn = tk.Button(dir_window, text=name, 
                               command=lambda p=path: open_dir(p))
                btn.pack(pady=2, padx=20, fill="x")
        
        tk.Button(tools_frame, text="Memory Usage", command=show_memory_usage).pack(side="left", padx=2)
        tk.Button(tools_frame, text="Garbage Collect", command=force_garbage_collect).pack(side="left", padx=2)
        tk.Button(tools_frame, text="Thread Info", command=show_thread_info).pack(side="left", padx=2)
        
        # Second row of tool buttons
        tools_frame2 = tk.Frame(parent)
        tools_frame2.pack(fill="x", padx=5, pady=5)
        
        tk.Button(tools_frame2, text="Open Viewers", command=open_viewers).pack(side="left", padx=2)
        tk.Button(tools_frame2, text="Project Analysis", command=analyze_project_structure).pack(side="left", padx=2)
        tk.Button(tools_frame2, text="Test All Modes", command=test_all_modes).pack(side="left", padx=2)
        tk.Button(tools_frame2, text="Quick Directories", command=open_directories).pack(side="left", padx=2)
        
        # Command execution
        tk.Label(parent, text="Debug Command Console:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(20,0))
        
        command_frame = tk.Frame(parent)
        command_frame.pack(fill="x", padx=5, pady=5)
        
        command_entry = tk.Entry(command_frame, font=("Consolas", 10))
        command_entry.pack(side="left", fill="x", expand=True)
        
        result_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 9), height=8)
        result_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add initial help message
        result_text.insert("end", "🎮 Debug Command Console initialized\n")
        result_text.insert("end", "💡 Type /help to see available commands\n")
        result_text.insert("end", "🐍 Or enter Python code directly\n\n")
        
        def execute_command():
            command = command_entry.get().strip()
            if not command:
                return
                
            result_text.insert("end", f">>> {command}\n")
            
            # Check if it's a debug command (starts with /)
            if command.startswith('/'):
                self.handle_debug_command(command, result_text)
            else:
                # Execute as Python code
                try:
                    import contextlib
                    from io import StringIO
                    
                    # Capture stdout
                    old_stdout = sys.stdout
                    sys.stdout = captured_output = StringIO()
                    
                    try:
                        # Execute the command
                        exec(command)
                        output = captured_output.getvalue()
                        if output:
                            result_text.insert("end", output)
                        else:
                            result_text.insert("end", "(no output)\n")
                    except Exception as e:
                        result_text.insert("end", f"Error: {str(e)}\n")
                    finally:
                        sys.stdout = old_stdout
                        
                except Exception as e:
                    result_text.insert("end", f"Execution error: {str(e)}\n")
            
            # Clear command and scroll to bottom
            command_entry.delete(0, "end")
            result_text.see("end")
        
        tk.Button(command_frame, text="Execute", command=execute_command).pack(side="right", padx=(5, 0))
        
        # Bind Enter key to execute command
        command_entry.bind("<Return>", lambda e: execute_command())
        
    def create_performance_tab(self, parent):
        """Create performance monitoring tab"""
        tk.Label(parent, text="Performance Monitor:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        # Performance metrics display
        perf_frame = tk.Frame(parent)
        perf_frame.pack(fill="x", padx=5, pady=5)
        
        # Memory usage display
        memory_frame = tk.LabelFrame(perf_frame, text="Memory Usage", font=("Arial", 10, "bold"))
        memory_frame.pack(fill="x", pady=2)
        
        self.memory_label = tk.Label(memory_frame, text="Memory info will appear here", font=("Consolas", 9))
        self.memory_label.pack(padx=5, pady=5)
        
        # CPU usage (if available)
        cpu_frame = tk.LabelFrame(perf_frame, text="System Info", font=("Arial", 10, "bold"))
        cpu_frame.pack(fill="x", pady=2)
        
        self.cpu_label = tk.Label(cpu_frame, text="System info will appear here", font=("Consolas", 9))
        self.cpu_label.pack(padx=5, pady=5)
        
        # File processing stats
        stats_frame = tk.LabelFrame(perf_frame, text="Processing Statistics", font=("Arial", 10, "bold"))
        stats_frame.pack(fill="x", pady=2)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, wrap=tk.WORD, font=("Consolas", 9), height=8)
        self.stats_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Buttons for performance tools
        perf_buttons = tk.Frame(parent)
        perf_buttons.pack(fill="x", padx=5, pady=5)
        
        def refresh_performance():
            self.update_performance_info()
        
        def clear_stats():
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("end", f"{time.strftime('[%H:%M:%S]')} Statistics cleared\n")
        
        def run_memory_profiler():
            self.run_memory_analysis()
        
        tk.Button(perf_buttons, text="Refresh Info", command=refresh_performance).pack(side="left", padx=2)
        tk.Button(perf_buttons, text="Clear Stats", command=clear_stats).pack(side="left", padx=2)
        tk.Button(perf_buttons, text="Memory Profile", command=run_memory_profiler).pack(side="left", padx=2)
        
        # Initialize performance info
        self.update_performance_info()
    
    def create_mode_testing_tab(self, parent):
        """Create mode testing tab"""
        tk.Label(parent, text="Encryption Mode Testing:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        # Mode selection
        mode_frame = tk.Frame(parent)
        mode_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(mode_frame, text="Select Mode:").pack(side="left")
        
        self.test_mode_var = tk.StringVar()
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.test_mode_var, state="readonly")
        mode_combo['values'] = ['Base32', 'Base64', 'Base85', 'Base91', 'Barcode', 'Binary', 'Braille', 'Chess', 'Emoji', 'Hex', 'Image', 'QR Code', 'Sound', 'Sudoku', 'UUID', 'Zero-Width']
        mode_combo.pack(side="left", padx=(5,0), fill="x", expand=True)
        
        # Test data input
        tk.Label(parent, text="Test Data:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(10,0))
        
        test_input_frame = tk.Frame(parent)
        test_input_frame.pack(fill="x", padx=5, pady=5)
        
        self.test_input = tk.Text(test_input_frame, height=3, font=("Consolas", 9))
        self.test_input.pack(fill="both", expand=True)
        self.test_input.insert("1.0", "Hello, World! This is a test message.")
        
        # Test results
        tk.Label(parent, text="Test Results:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(10,0))
        
        self.test_results = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 9), height=10)
        self.test_results.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Test buttons
        test_buttons = tk.Frame(parent)
        test_buttons.pack(fill="x", padx=5, pady=5)
        
        def run_encode_test():
            self.run_mode_test("encode")
        
        def run_decode_test():
            self.run_mode_test("decode")
        
        def run_round_trip_test():
            self.run_mode_test("round_trip")
        
        def benchmark_mode():
            self.run_mode_benchmark()
        
        tk.Button(test_buttons, text="Test Encode", command=run_encode_test).pack(side="left", padx=2)
        tk.Button(test_buttons, text="Test Decode", command=run_decode_test).pack(side="left", padx=2)
        tk.Button(test_buttons, text="Round Trip Test", command=run_round_trip_test).pack(side="left", padx=2)
        tk.Button(test_buttons, text="Benchmark", command=benchmark_mode).pack(side="left", padx=2)
    
    def create_security_tab(self, parent):
        """Create security audit tab"""
        tk.Label(parent, text="Security Analysis:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        # Security checks
        security_frame = tk.LabelFrame(parent, text="Security Checks", font=("Arial", 10, "bold"))
        security_frame.pack(fill="x", padx=5, pady=5)
        
        security_buttons = tk.Frame(security_frame)
        security_buttons.pack(fill="x", padx=5, pady=5)
        
        def check_file_permissions():
            self.check_file_security()
        
        def analyze_key_strength():
            self.analyze_encryption_keys()
        
        def scan_temp_files():
            self.scan_temporary_files()
        
        def check_mode_security():
            self.check_mode_vulnerabilities()
        
        tk.Button(security_buttons, text="File Permissions", command=check_file_permissions).pack(side="left", padx=2)
        tk.Button(security_buttons, text="Key Strength", command=analyze_key_strength).pack(side="left", padx=2)
        tk.Button(security_buttons, text="Temp Files", command=scan_temp_files).pack(side="left", padx=2)
        tk.Button(security_buttons, text="Mode Security", command=check_mode_security).pack(side="left", padx=2)
        
        # Security results
        tk.Label(parent, text="Security Report:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(10,0))
        
        self.security_results = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 9))
        self.security_results.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add initial security tips
        security_tips = [
            "=== SECURITY RECOMMENDATIONS ===",
            "• Always use strong encryption keys (min 12 characters)",
            "• Regularly clear temporary files",
            "• Verify file permissions on sensitive directories",
            "• Use different keys for different data types",
            "• Monitor for unusual file access patterns",
            "",
            "Click buttons above to run security checks..."
        ]
        
        for tip in security_tips:
            self.security_results.insert("end", tip + "\n")
    
    def update_performance_info(self):
        """Update performance monitoring information"""
        try:
            import psutil
            process = psutil.Process()
            
            # Memory info
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            memory_text = (f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB | "
                         f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB | "
                         f"Usage: {memory_percent:.1f}%")
            self.memory_label.config(text=memory_text)
            
            # System info
            cpu_percent = process.cpu_percent()
            thread_count = threading.active_count()
            system_text = (f"CPU: {cpu_percent:.1f}% | "
                         f"Threads: {thread_count} | "
                         f"PID: {process.pid}")
            self.cpu_label.config(text=system_text)
            
            # Log performance stats
            timestamp = time.strftime('[%H:%M:%S]')
            stats_entry = (f"{timestamp} MEM: {memory_info.rss / 1024 / 1024:.1f}MB "
                         f"CPU: {cpu_percent:.1f}% Threads: {thread_count}\n")
            self.stats_text.insert("end", stats_entry)
            self.stats_text.see("end")
            
        except ImportError:
            self.memory_label.config(text="psutil not available - install for detailed monitoring")
            self.cpu_label.config(text="System monitoring unavailable")
    
    def run_memory_analysis(self):
        """Run detailed memory analysis"""
        try:
            import gc
            import sys
            
            # Force garbage collection
            collected = gc.collect()
            
            # Get object counts
            obj_count = len(gc.get_objects())
            
            # Memory usage
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_text = f"Current Memory: {memory_mb:.2f} MB"
            except ImportError:
                memory_text = "Memory details unavailable (install psutil)"
            
            # Update stats
            timestamp = time.strftime('[%H:%M:%S]')
            analysis = (f"{timestamp} MEMORY ANALYSIS:\n"
                       f"  - Collected {collected} objects via GC\n"
                       f"  - Total objects in memory: {obj_count}\n"
                       f"  - {memory_text}\n"
                       f"  - Reference count optimization available\n\n")
            
            self.stats_text.insert("end", analysis)
            self.stats_text.see("end")
            
        except Exception as e:
            self.stats_text.insert("end", f"{time.strftime('[%H:%M:%S]')} Memory analysis error: {e}\n")
    
    def run_mode_test(self, test_type):
        """Run encryption mode test"""
        mode_name = self.test_mode_var.get()
        test_data = self.test_input.get("1.0", "end-1c")
        
        if not mode_name or not test_data:
            self.test_results.insert("end", f"{time.strftime('[%H:%M:%S]')} Please select mode and enter test data\n")
            return
        
        timestamp = time.strftime('[%H:%M:%S]')
        self.test_results.insert("end", f"\n{timestamp} Testing {mode_name} - {test_type.upper()}\n")
        self.test_results.insert("end", f"Input data: {test_data[:50]}{'...' if len(test_data) > 50 else ''}\n")
        
        try:
            # Import the mode dynamically
            mode_modules = {
                'Base32': 'base32_mode',
                'Base64': 'base64_mode',
                'Base85': 'base85_mode',
                'Base91': 'base91_mode',
                'Barcode': 'barcode_mode',
                'Binary': 'binary_mode',
                'Braille': 'braille_mode',
                'Chess': 'chess_mode',
                'Emoji': 'emoji_mode',
                'Hex': 'hex_mode',
                'Image': 'image_mode',
                'QR Code': 'qr_code_mode',
                'Sound': 'sound_mode',
                'Sudoku': 'sudoku_mode',
                'UUID': 'uuid_mode',
                'Zero-Width': 'zero_width_mode'
            }
            
            if mode_name not in mode_modules:
                self.test_results.insert("end", f"ERROR: Mode {mode_name} not supported for testing\n")
                return
            
            # Import the module
            import importlib
            mode_module = importlib.import_module(f"src.{mode_modules[mode_name]}")
            
            test_bytes = test_data.encode('utf-8')
            
            if test_type in ["encode", "round_trip"]:
                # Test encoding
                start_time = time.time()
                encoded = mode_module.encode(test_bytes)
                encode_time = time.time() - start_time
                
                self.test_results.insert("end", f"✓ Encode successful ({encode_time:.3f}s)\n")
                self.test_results.insert("end", f"Encoded length: {len(str(encoded))}\n")
                self.test_results.insert("end", f"Compression ratio: {len(str(encoded))/len(test_data):.2f}x\n")
                
                if test_type == "round_trip":
                    # Test decoding
                    start_time = time.time()
                    decoded = mode_module.decode(encoded)
                    decode_time = time.time() - start_time
                    
                    if decoded == test_bytes:
                        self.test_results.insert("end", f"✓ Round trip successful ({decode_time:.3f}s)\n")
                        self.test_results.insert("end", f"Data integrity: VERIFIED\n")
                    else:
                        self.test_results.insert("end", f"✗ Round trip FAILED - data mismatch\n")
            
        except Exception as e:
            self.test_results.insert("end", f"✗ Test FAILED: {str(e)}\n")
        
        self.test_results.see("end")
    
    def run_mode_benchmark(self):
        """Run performance benchmark for selected mode"""
        mode_name = self.test_mode_var.get()
        if not mode_name:
            self.test_results.insert("end", f"{time.strftime('[%H:%M:%S]')} Please select a mode first\n")
            return
        
        timestamp = time.strftime('[%H:%M:%S]')
        self.test_results.insert("end", f"\n{timestamp} BENCHMARK - {mode_name}\n")
        
        # Import the required modules
        from src import gui
        
        # Get the actual mode module
        mode_module = None
        if mode_name in gui.MODES:
            mode_module = gui.MODES[mode_name]
        else:
            self.test_results.insert("end", f"{time.strftime('[%H:%M:%S]')} Mode '{mode_name}' not found\n")
            return
        
        # Test with different data sizes
        test_sizes = [100, 1000, 10000, 50000]  # bytes
        
        self.test_results.insert("end", f"{time.strftime('[%H:%M:%S]')} Testing encoding performance...\n")
        
        for size in test_sizes:
            test_data_str = "A" * size
            test_data_bytes = test_data_str.encode('utf-8')
            
            try:
                # Time the encoding operation
                start = time.perf_counter()
                
                # Use proper encoding method with signature inspection
                import inspect
                sig = inspect.signature(mode_module.encode)
                
                # Prepare encoding parameters based on function signature
                encode_params = {}
                
                # Add encoding parameter if supported
                if 'encoding' in sig.parameters:
                    encode_params['encoding'] = 'utf-8'
                
                # Handle special cases for modes that need extra parameters
                if mode_name == 'Chess':
                    encode_params['chess_fen'] = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
                elif mode_name == 'Sudoku':
                    encode_params['grid_seed'] = '123456789'
                
                # Determine if mode expects bytes or string data
                first_param = list(sig.parameters.keys())[0]
                param_annotation = sig.parameters[first_param].annotation
                
                # Use bytes for modes that expect bytes, string for others
                if (param_annotation == bytes or 
                    mode_name in ['Base32', 'Base64', 'Base85', 'Base91', 'Binary', 'Hex', 'Braille', 'Sound', 'Image', 'Zero-Width', 'Emoji', 'UUID']):
                    test_data_to_use = test_data_bytes
                else:
                    test_data_to_use = test_data_str
                    
                # Call encode with appropriate parameters
                if encode_params:
                    encoded_result = mode_module.encode(test_data_to_use, **encode_params)
                else:
                    encoded_result = mode_module.encode(test_data_to_use)
                    
                end = time.perf_counter()
                
                encode_time = (end - start) * 1000  # Convert to milliseconds
                
                # Test decoding if available
                decode_time = 0
                if hasattr(mode_module, 'decode'):
                    try:
                        start = time.perf_counter()
                        
                        # Use proper decoding method
                        decode_sig = inspect.signature(mode_module.decode)
                        decode_params = {}
                        
                        if 'encoding' in decode_sig.parameters:
                            decode_params['encoding'] = 'utf-8'
                        
                        # Add same special parameters for decode
                        if mode_name == 'Chess' and 'chess_fen' in decode_sig.parameters:
                            decode_params['chess_fen'] = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
                        elif mode_name == 'Sudoku' and 'grid_seed' in decode_sig.parameters:
                            decode_params['grid_seed'] = '123456789'
                            
                        if decode_params:
                            decoded_result = mode_module.decode(encoded_result, **decode_params)
                        else:
                            decoded_result = mode_module.decode(encoded_result)
                            
                        end = time.perf_counter()
                        decode_time = (end - start) * 1000
                    except Exception as decode_error:
                        decode_time = -1  # Decode failed
                
                # Calculate throughput (KB/s for better readability)
                throughput_kbs = (size / 1024) / ((encode_time / 1000) if encode_time > 0 else 0.001)
                
                if decode_time >= 0:
                    self.test_results.insert("end", f"Size {size:>6}B: Encode {encode_time:>7.2f}ms, Decode {decode_time:>7.2f}ms, Throughput {throughput_kbs:>8.2f}KB/s\n")
                else:
                    self.test_results.insert("end", f"Size {size:>6}B: Encode {encode_time:>7.2f}ms, Decode FAILED, Throughput {throughput_kbs:>8.2f}KB/s\n")
                    
            except Exception as e:
                self.test_results.insert("end", f"Size {size:>6}B: ERROR - {str(e)[:70]}\n")
        
        self.test_results.insert("end", f"{time.strftime('[%H:%M:%S]')} Benchmark completed\n")
        self.test_results.see("end")
    
    def check_file_security(self):
        """Check file system security"""
        timestamp = time.strftime('[%H:%M:%S]')
        self.security_results.insert("end", f"\n{timestamp} FILE SECURITY CHECK\n")
        
        try:
            # Check important directories
            dirs_to_check = ["machine_files", "human_files", "src"]
            
            for dir_name in dirs_to_check:
                if os.path.exists(dir_name):
                    stat_info = os.stat(dir_name)
                    permissions = oct(stat_info.st_mode)[-3:]
                    self.security_results.insert("end", f"✓ {dir_name}/: permissions {permissions}\n")
                else:
                    self.security_results.insert("end", f"⚠ {dir_name}/: directory not found\n")
            
            # Check for sensitive files
            sensitive_patterns = [".key", ".secret", ".private", "password"]
            found_sensitive = []
            
            for root, dirs, files in os.walk("."):
                for file in files:
                    for pattern in sensitive_patterns:
                        if pattern in file.lower():
                            found_sensitive.append(os.path.join(root, file))
            
            if found_sensitive:
                self.security_results.insert("end", f"⚠ Found {len(found_sensitive)} potentially sensitive files\n")
                for f in found_sensitive[:5]:  # Show first 5
                    self.security_results.insert("end", f"  - {f}\n")
            else:
                self.security_results.insert("end", "✓ No obvious sensitive files found\n")
                
        except Exception as e:
            self.security_results.insert("end", f"✗ File security check failed: {e}\n")
        
        self.security_results.see("end")
    
    def analyze_encryption_keys(self):
        """Analyze encryption key strength"""
        timestamp = time.strftime('[%H:%M:%S]')
        self.security_results.insert("end", f"\n{timestamp} KEY STRENGTH ANALYSIS\n")
        
        # Key strength guidelines
        guidelines = [
            "✓ Key length recommendations:",
            "  - Minimum: 12 characters",
            "  - Recommended: 16+ characters", 
            "  - Strong: 32+ characters with mixed case, numbers, symbols",
            "",
            "✓ Key complexity should include:",
            "  - Uppercase and lowercase letters",
            "  - Numbers (0-9)",
            "  - Special characters (!@#$%^&*)",
            "  - Avoid dictionary words",
            "",
            "⚠ Avoid common patterns:",
            "  - Sequential characters (123, abc)",
            "  - Repeated characters (aaa, 111)",
            "  - Personal information (names, dates)",
        ]
        
        for line in guidelines:
            self.security_results.insert("end", line + "\n")
        
        self.security_results.see("end")
    
    def scan_temporary_files(self):
        """Scan for temporary files that might contain sensitive data"""
        timestamp = time.strftime('[%H:%M:%S]')
        self.security_results.insert("end", f"\n{timestamp} TEMPORARY FILES SCAN\n")
        
        try:
            import tempfile
            
            temp_dirs = [tempfile.gettempdir(), os.getcwd()]
            temp_patterns = [".tmp", ".temp", "~", ".bak", ".cache"]
            
            found_temps = []
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir):
                        # Limit search depth to avoid system directories
                        level = root.replace(temp_dir, '').count(os.sep)
                        if level < 3:
                            for file in files:
                                for pattern in temp_patterns:
                                    if file.endswith(pattern):
                                        file_path = os.path.join(root, file)
                                        try:
                                            size = os.path.getsize(file_path)
                                            if size > 0:  # Only report non-empty files
                                                found_temps.append((file_path, size))
                                        except:
                                            pass
            
            if found_temps:
                self.security_results.insert("end", f"⚠ Found {len(found_temps)} temporary files:\n")
                for file_path, size in found_temps[:10]:  # Show first 10
                    self.security_results.insert("end", f"  - {file_path} ({size} bytes)\n")
                if len(found_temps) > 10:
                    self.security_results.insert("end", f"  ... and {len(found_temps) - 10} more\n")
                
                self.security_results.insert("end", "\n💡 Consider cleaning temporary files regularly\n")
            else:
                self.security_results.insert("end", "✓ No significant temporary files found\n")
                
        except Exception as e:
            self.security_results.insert("end", f"✗ Temp files scan failed: {e}\n")
        
        self.security_results.see("end")
    
    def check_mode_vulnerabilities(self):
        """Check for potential vulnerabilities in encryption modes"""
        timestamp = time.strftime('[%H:%M:%S]')
        self.security_results.insert("end", f"\n{timestamp} MODE SECURITY ANALYSIS\n")
        
        vulnerabilities = [
            "🔍 SECURITY ANALYSIS BY MODE:",
            "",
            "HIGH SECURITY:",
            "✓ Base64/32/85/91: Standard encoding, secure with XOR key",
            "✓ Binary/Hex: Direct representation, secure with key",
            "",
            "MEDIUM SECURITY:",
            "⚠ Chess/Sudoku: Pattern-based, may reveal data structure",
            "⚠ Braille: Visual patterns could be recognizable",
            "⚠ Emoji: May stand out in communications",
            "",
            "LOW SECURITY (STEGANOGRAPHY):",
            "⚠ Image: Visible files, may attract attention",
            "⚠ QR Code: Scannable by anyone with QR reader",
            "⚠ Sound: Audio files may be analyzed",
            "⚠ Barcode: Similar to QR, easily scannable",
            "",
            "RECOMMENDATIONS:",
            "• Always use XOR encryption key for sensitive data",
            "• Combine multiple modes for extra security",
            "• Use obfuscated filenames",
            "• Consider file size implications",
            "• Test round-trip integrity regularly",
        ]
        
        for line in vulnerabilities:
            self.security_results.insert("end", line + "\n")
        
        self.security_results.see("end")
    
    def start_monitoring(self):
        """Start real-time system monitoring"""
        if hasattr(self, 'monitoring_active') and self.monitoring_active:
            try:
                # Check memory usage
                try:
                    import psutil
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()
                    
                    if memory_mb > 100:  # Alert if memory > 100MB
                        self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [MONITOR] ⚠ High memory usage: {memory_mb:.1f}MB\n")
                        self.log_text.see("end")
                    
                    if cpu_percent > 50:  # Alert if CPU > 50%
                        self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [MONITOR] ⚠ High CPU usage: {cpu_percent:.1f}%\n")
                        self.log_text.see("end")
                        
                except ImportError:
                    pass
                
                # Check file system changes
                self.check_file_changes()
                
                # Schedule next monitoring check
                self.window.after(5000, self.start_monitoring)  # Check every 5 seconds
                
            except Exception as e:
                self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [MONITOR] Error: {e}\n")
                self.monitoring_active = False
    
    def check_file_changes(self):
        """Check for file system changes"""
        try:
            if not hasattr(self, 'last_file_check'):
                self.last_file_check = time.time()
                return
            
            # Check human_files and machine_files directories for new files
            for dir_name in ['human_files', 'machine_files']:
                if os.path.exists(dir_name):
                    for file in os.listdir(dir_name):
                        file_path = os.path.join(dir_name, file)
                        if os.path.isfile(file_path):
                            mtime = os.path.getmtime(file_path)
                            if mtime > self.last_file_check:
                                self.log_text.insert("end", f"{time.strftime('[%H:%M:%S]')} [MONITOR] 📁 File activity: {file_path}\n")
                                self.log_text.see("end")
            
            self.last_file_check = time.time()
            
        except Exception as e:
            pass  # Silently ignore file checking errors
    
    def handle_debug_command(self, command, result_text):
        """Handle debug commands that start with /"""
        cmd_parts = command[1:].split()  # Remove / and split
        cmd_name = cmd_parts[0].lower() if cmd_parts else ""
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        timestamp = time.strftime('[%H:%M:%S]')
        
        if cmd_name == "help":
            result_text.insert("end", "🎮 DEBUG COMMANDS:\n")
            result_text.insert("end", "/help                - Show this help menu\n")
            result_text.insert("end", "/status              - Show system status\n")
            result_text.insert("end", "/memory              - Display memory usage\n")
            result_text.insert("end", "/threads             - List active threads\n")
            result_text.insert("end", "/files [dir]         - List files in directory\n")
            result_text.insert("end", "/clear               - Clear console output\n")
            result_text.insert("end", "/time                - Show current time\n")
            result_text.insert("end", "/modes               - List available encoding modes\n")
            result_text.insert("end", "/test <mode>         - Quick test an encoding mode\n")
            result_text.insert("end", "/env [var]           - Show environment variables\n")
            result_text.insert("end", "/gc                  - Run garbage collection\n")
            result_text.insert("end", "/pid                 - Show process ID\n")
            result_text.insert("end", "/uptime              - Show application uptime\n")
            result_text.insert("end", "/log <msg>           - Add message to debug log\n")
            result_text.insert("end", "/version             - Show Python version\n")
            result_text.insert("end", "\n💡 You can also execute Python code directly!\n")
            
        elif cmd_name == "status":
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                thread_count = threading.active_count()
                
                result_text.insert("end", f"📊 SYSTEM STATUS {timestamp}\n")
                result_text.insert("end", f"Memory: {memory_mb:.1f} MB\n")
                result_text.insert("end", f"CPU: {cpu_percent:.1f}%\n")
                result_text.insert("end", f"Threads: {thread_count}\n")
                result_text.insert("end", f"PID: {process.pid}\n")
            except ImportError:
                result_text.insert("end", "System status unavailable (install psutil)\n")
            except Exception as e:
                result_text.insert("end", f"Status error: {e}\n")
                
        elif cmd_name == "memory":
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                result_text.insert("end", f"🧠 MEMORY INFO {timestamp}\n")
                result_text.insert("end", f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB\n")
                result_text.insert("end", f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB\n")
                result_text.insert("end", f"Percent: {process.memory_percent():.1f}%\n")
            except ImportError:
                result_text.insert("end", "Memory info unavailable (install psutil)\n")
            except Exception as e:
                result_text.insert("end", f"Memory error: {e}\n")
                
        elif cmd_name == "threads":
            thread_list = threading.enumerate()
            result_text.insert("end", f"🧵 ACTIVE THREADS ({len(thread_list)}) {timestamp}\n")
            for i, thread in enumerate(thread_list, 1):
                status = "alive" if thread.is_alive() else "dead"
                result_text.insert("end", f"{i:2d}. {thread.name} ({status})\n")
                
        elif cmd_name == "files":
            directory = args[0] if args else "."
            try:
                if os.path.exists(directory):
                    files = os.listdir(directory)
                    result_text.insert("end", f"📁 FILES IN '{directory}' ({len(files)} items) {timestamp}\n")
                    for item in sorted(files)[:20]:  # Limit to first 20
                        full_path = os.path.join(directory, item)
                        if os.path.isdir(full_path):
                            result_text.insert("end", f"  📁 {item}/\n")
                        else:
                            try:
                                size = os.path.getsize(full_path)
                                result_text.insert("end", f"  📄 {item} ({size} bytes)\n")
                            except:
                                result_text.insert("end", f"  📄 {item}\n")
                    if len(files) > 20:
                        result_text.insert("end", f"  ... and {len(files) - 20} more items\n")
                else:
                    result_text.insert("end", f"Directory '{directory}' not found\n")
            except Exception as e:
                result_text.insert("end", f"Files error: {e}\n")
                
        elif cmd_name == "clear":
            result_text.delete("1.0", "end")
            result_text.insert("end", f"{timestamp} Console cleared. Type /help for commands.\n")
            
        elif cmd_name == "time":
            import datetime
            now = datetime.datetime.now()
            result_text.insert("end", f"🕐 CURRENT TIME\n")
            result_text.insert("end", f"Date: {now.strftime('%Y-%m-%d')}\n")
            result_text.insert("end", f"Time: {now.strftime('%H:%M:%S')}\n")
            result_text.insert("end", f"Timestamp: {now.timestamp()}\n")
            
        elif cmd_name == "modes":
            modes = [
                "Base64", "Base32", "Base85", "Base91", "Binary", "Hex",
                "Chess", "Sudoku", "Braille", "Emoji", "QR Code", "Image",
                "Sound", "Barcode", "UUID", "Zero-Width"
            ]
            result_text.insert("end", f"🎯 ENCODING MODES ({len(modes)}) {timestamp}\n")
            for i, mode in enumerate(modes, 1):
                result_text.insert("end", f"{i:2d}. {mode}\n")
                
        elif cmd_name == "test":
            if not args:
                result_text.insert("end", "Usage: /test <mode_name>\nExample: /test base64\n")
            else:
                mode_name = args[0].lower()
                test_data = b"Hello Debug Test!"
                
                try:
                    # Map mode names to modules
                    mode_map = {
                        'base64': 'base64_mode',
                        'base32': 'base32_mode', 
                        'hex': 'hex_mode',
                        'binary': 'binary_mode',
                        'braille': 'braille_mode',
                        'emoji': 'emoji_mode'
                    }
                    
                    if mode_name in mode_map:
                        import importlib
                        module = importlib.import_module(f"src.{mode_map[mode_name]}")
                        
                        # Test encode/decode
                        encoded = module.encode(test_data)
                        decoded = module.decode(encoded)
                        
                        result_text.insert("end", f"🧪 TEST {mode_name.upper()} {timestamp}\n")
                        result_text.insert("end", f"Input: {test_data}\n")
                        result_text.insert("end", f"Encoded: {str(encoded)[:50]}{'...' if len(str(encoded)) > 50 else ''}\n")
                        
                        if decoded == test_data:
                            result_text.insert("end", "✅ Round-trip: SUCCESS\n")
                        else:
                            result_text.insert("end", "❌ Round-trip: FAILED\n")
                    else:
                        result_text.insert("end", f"Mode '{mode_name}' not supported for quick test\n")
                        result_text.insert("end", "Supported: base64, base32, hex, binary, braille, emoji\n")
                        
                except Exception as e:
                    result_text.insert("end", f"Test error: {e}\n")
                    
        elif cmd_name == "env":
            if args:
                # Show specific environment variable
                var_name = args[0].upper()
                value = os.environ.get(var_name, "Not found")
                result_text.insert("end", f"🌍 ENVIRONMENT VARIABLE {timestamp}\n")
                result_text.insert("end", f"{var_name}: {value}\n")
            else:
                # Show all environment variables
                env_vars = list(os.environ.keys())
                result_text.insert("end", f"🌍 ENVIRONMENT VARIABLES ({len(env_vars)}) {timestamp}\n")
                for var in sorted(env_vars)[:10]:  # Show first 10
                    result_text.insert("end", f"{var}: {os.environ[var][:50]}{'...' if len(os.environ[var]) > 50 else ''}\n")
                if len(env_vars) > 10:
                    result_text.insert("end", f"... and {len(env_vars) - 10} more variables\n")
                    
        elif cmd_name == "gc":
            import gc
            collected = gc.collect()
            result_text.insert("end", f"🗑️ GARBAGE COLLECTION {timestamp}\n")
            result_text.insert("end", f"Collected {collected} objects\n")
            result_text.insert("end", f"Total objects: {len(gc.get_objects())}\n")
            
        elif cmd_name == "pid":
            import os
            result_text.insert("end", f"🔢 PROCESS INFO {timestamp}\n")
            result_text.insert("end", f"PID: {os.getpid()}\n")
            result_text.insert("end", f"Parent PID: {os.getppid()}\n")
            
        elif cmd_name == "uptime":
            if hasattr(self, 'start_time'):
                uptime = time.time() - self.start_time
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                result_text.insert("end", f"⏱️ APPLICATION UPTIME {timestamp}\n")
                result_text.insert("end", f"Uptime: {hours}h {minutes}m {seconds}s\n")
            else:
                result_text.insert("end", "Uptime tracking not available\n")
                
        elif cmd_name == "log":
            if args:
                message = " ".join(args)
                if hasattr(self, 'log_text'):
                    self.log_text.insert("end", f"{timestamp} [CMD] {message}\n")
                    self.log_text.see("end")
                result_text.insert("end", f"📝 Message logged: {message}\n")
            else:
                result_text.insert("end", "Usage: /log <message>\n")
                
        elif cmd_name == "version":
            result_text.insert("end", f"🐍 PYTHON VERSION {timestamp}\n")
            result_text.insert("end", f"Version: {sys.version}\n")
            result_text.insert("end", f"Platform: {sys.platform}\n")
            result_text.insert("end", f"Executable: {sys.executable}\n")
            
        else:
            result_text.insert("end", f"Unknown command: {cmd_name}\n")
            result_text.insert("end", "Type /help for available commands\n")
        
        result_text.insert("end", "\n")
    
    def is_chess_encoded_file(self, filepath):
        """Check if a file contains chess-encoded data"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(100)  # Read first 100 chars
                return 'FEN:' in content
        except:
            return False
    
    def is_sudoku_encoded_file(self, filepath):
        """Check if a file contains sudoku-encoded data"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(100)  # Read first 100 chars
                return 'SUD:' in content or 'Sudoku Grid' in content or 'Grid Seed' in content
        except:
            return False
        
    def on_close(self):
        """Handle window close"""
        # Stop monitoring if active
        if hasattr(self, 'monitoring_active'):
            self.monitoring_active = False
        
        self.window.destroy()
        self.window = None


# Global instances
konami_handler = KonamiCodeHandler()
debug_window = None


def init_debug_system(root_window):
    """Initialize the debug system with the main window"""
    global debug_window
    debug_window = DebugWindow(root_window)


def handle_key_event(event):
    """Handle key events for Konami code detection - DEPRECATED"""
    return handle_key_press_event(event)

def handle_key_press_event(event):
    """Handle KeyPress events for Konami code detection"""
    key = event.keysym
    
    # Only process if we don't already have the debug window open
    if debug_window and debug_window.window is not None:
        return
    
    # Only process if we're in listening mode
    if not konami_handler.is_listening():
        return
    
    # Add the key to the sequence
    if konami_handler.handle_key_press(key):
        # Konami code completed!
        print("DEBUG: Opening debug window...")
        if debug_window:
            debug_window.show()
        else:
            print("DEBUG: Debug window not initialized!")

def handle_key_release_event(event):
    """Handle KeyRelease events for Konami code detection"""
    key = event.keysym
    
    # Only process if we don't already have the debug window open
    if debug_window and debug_window.window is not None:
        return
    
    # Only process if we're in listening mode
    if not konami_handler.is_listening():
        return
    
    # Handle key release
    konami_handler.handle_key_release(key)


def setup_konami_code_listener(widget):
    """Setup Konami code listener on a widget"""
    widget.bind("<Key>", handle_key_event)
    # Make sure the widget can receive key events
    widget.focus_set()


def log_debug_message(message):
    """Log a debug message to the debug window if it's open"""
    if debug_window and debug_window.window is not None and hasattr(debug_window, 'log_text'):
        timestamp = time.strftime('[%H:%M:%S]')
        debug_window.log_text.insert("end", f"{timestamp} [DEBUG] {message}\n")
        debug_window.log_text.see("end")
    
    # Also print to console
    print(f"DEBUG: {message}")


def log_file_operation(operation_type, filename, mode=None, success=True, error_msg=None):
    """Log file operations for monitoring"""
    if debug_window and debug_window.window is not None and hasattr(debug_window, 'log_text'):
        timestamp = time.strftime('[%H:%M:%S]')
        status = "✓" if success else "✗"
        mode_text = f" [{mode}]" if mode else ""
        
        if success:
            message = f"{timestamp} [FILE] {status} {operation_type}: {filename}{mode_text}"
        else:
            message = f"{timestamp} [FILE] {status} {operation_type} FAILED: {filename}{mode_text} - {error_msg}"
        
        debug_window.log_text.insert("end", f"{message}\n")
        debug_window.log_text.see("end")


def log_performance_metric(metric_name, value, unit=""):
    """Log performance metrics"""
    if debug_window and debug_window.window is not None and hasattr(debug_window, 'log_text'):
        timestamp = time.strftime('[%H:%M:%S]')
        message = f"{timestamp} [PERF] {metric_name}: {value}{unit}"
        debug_window.log_text.insert("end", f"{message}\n")
        debug_window.log_text.see("end")
