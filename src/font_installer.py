# src/font_installer.py
"""
Font Installation Utility
Automatically installs project fonts to system when needed
"""

import os
import sys
import shutil
import platform
from pathlib import Path

def get_system_fonts_dir():
    """Get the system fonts directory based on OS"""
    system = platform.system()
    
    if system == "Windows":
        return "C:/Windows/Fonts/"
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Fonts/")
    elif system == "Linux":
        # Try user fonts first, fallback to system
        user_fonts = os.path.expanduser("~/.local/share/fonts/")
        if os.path.exists(os.path.dirname(user_fonts)) or os.access(os.path.expanduser("~/.local/share/"), os.W_OK):
            os.makedirs(user_fonts, exist_ok=True)
            return user_fonts
        else:
            return "/usr/share/fonts/"
    else:
        return None

def get_project_fonts_dir():
    """Get the project fonts directory"""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(current_dir, "fonts")

def is_font_installed(font_name):
    """Check if a font is already installed in the system"""
    system_fonts_dir = get_system_fonts_dir()
    if not system_fonts_dir or not os.path.exists(system_fonts_dir):
        return False
    
    font_path = os.path.join(system_fonts_dir, font_name)
    return os.path.exists(font_path)

def install_font_to_system(font_name, source_path, silent=True):
    """Install a font file to the system fonts directory"""
    try:
        system_fonts_dir = get_system_fonts_dir()
        if not system_fonts_dir:
            if not silent:
                print(f"Unsupported operating system for automatic font installation")
            return False
        
        if not os.path.exists(source_path):
            if not silent:
                print(f"Source font file not found: {source_path}")
            return False
        
        target_path = os.path.join(system_fonts_dir, font_name)
        
        # Check if already installed
        if os.path.exists(target_path):
            if not silent:
                print(f"Font already installed: {font_name}")
            return True
        
        # Create fonts directory if it doesn't exist (Linux/macOS)
        os.makedirs(system_fonts_dir, exist_ok=True)
        
        # Copy font file
        shutil.copy2(source_path, target_path)
        
        if not silent:
            print(f"✓ Font installed successfully: {font_name}")
            print(f"  From: {source_path}")
            print(f"  To: {target_path}")
        
        return True
        
    except PermissionError:
        if not silent:
            print(f"⚠️  Permission denied - cannot install font to system directory")
            print(f"   Please run as administrator or install font manually")
            print(f"   Source: {source_path}")
        return False
    except Exception as e:
        if not silent:
            print(f"✗ Failed to install font: {str(e)}")
        return False

def ensure_firacode_available(silent=True):
    """Ensure FiraCode font is available for the application"""
    project_fonts_dir = get_project_fonts_dir()
    
    # Priority list of FiraCode font files to try
    firacode_files = [
        "FiraCode-Regular.ttf",
        "FiraCode.ttf",
        "firacode-regular.ttf"
    ]
    
    results = {
        "project_available": False,
        "system_installed": False,
        "installation_attempted": False,
        "installation_success": False,
        "font_path": None
    }
    
    # Check if any FiraCode font exists in project
    for font_file in firacode_files:
        project_font_path = os.path.join(project_fonts_dir, font_file)
        if os.path.exists(project_font_path):
            results["project_available"] = True
            results["font_path"] = project_font_path
            
            # Check if it's installed in system
            if is_font_installed(font_file):
                results["system_installed"] = True
                if not silent:
                    print(f"✓ FiraCode already installed in system: {font_file}")
            else:
                # Try to install to system
                results["installation_attempted"] = True
                success = install_font_to_system(font_file, project_font_path, silent)
                results["installation_success"] = success
            
            break
    
    if not results["project_available"]:
        if not silent:
            print(f"⚠️  FiraCode font not found in project fonts directory")
            print(f"   Please ensure FiraCode-Regular.ttf is in: {project_fonts_dir}")
    
    return results

def get_font_installation_info():
    """Get comprehensive font installation information"""
    info = {
        "system": platform.system(),
        "system_fonts_dir": get_system_fonts_dir(),
        "project_fonts_dir": get_project_fonts_dir(),
        "firacode_status": ensure_firacode_available(silent=True)
    }
    
    return info

def print_font_status():
    """Print detailed font installation status"""
    print("Font Installation Status")
    print("=" * 40)
    
    info = get_font_installation_info()
    
    print(f"Operating System: {info['system']}")
    print(f"System Fonts Directory: {info['system_fonts_dir']}")
    print(f"Project Fonts Directory: {info['project_fonts_dir']}")
    print()
    
    status = info['firacode_status']
    print("FiraCode Font Status:")
    
    if status['project_available']:
        print(f"✓ Available in project: {status['font_path']}")
    else:
        print("✗ Not found in project")
    
    if status['system_installed']:
        print("✓ Installed in system fonts")
    elif status['installation_attempted']:
        if status['installation_success']:
            print("✓ Successfully installed to system")
        else:
            print("✗ Failed to install to system (permission denied)")
            print("  → Font will still work from project directory")
    else:
        print("- Not installed in system (using project font)")
    
    print()
    print("Font Priority Order:")
    print("1. System-installed FiraCode (if available)")
    print("2. Project FiraCode fonts/ directory")
    print("3. Fallback to Consolas/Courier (Windows)")
    print("4. Default system fonts")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print_font_status()
    elif len(sys.argv) > 1 and sys.argv[1] == "--install":
        print("Attempting to install FiraCode font...")
        results = ensure_firacode_available(silent=False)
        if results['installation_success']:
            print("\n🎉 FiraCode font installed successfully!")
        elif results['project_available']:
            print("\n✓ FiraCode font is available in project directory")
        else:
            print("\n⚠️  FiraCode font not found - please download manually")
    else:
        # Silent check by default
        ensure_firacode_available(silent=True)
