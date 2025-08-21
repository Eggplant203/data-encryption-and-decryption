# install_fonts.py - Manual font installation script
"""
Manual Font Installation Script
Run this script to install FiraCode fonts to your system
"""

import sys
import os
sys.path.append('src')

def main():
    print("FiraCode Font Installer")
    print("=" * 30)
    
    try:
        from font_installer import ensure_firacode_available, print_font_status
        
        # Show current status
        print("Current Font Status:")
        print_font_status()
        
        # Ask user for installation
        print("\n" + "=" * 50)
        print("Installation Options:")
        print("1. Attempt automatic installation (may require admin rights)")
        print("2. Show manual installation instructions")
        print("3. Test current font setup")
        print("4. Exit")
        
        while True:
            try:
                choice = input("\nSelect option (1-4): ").strip()
                
                if choice == "1":
                    print("\nAttempting automatic installation...")
                    result = ensure_firacode_available(silent=False)
                    
                    if result['installation_success']:
                        print("\n🎉 SUCCESS! FiraCode installed to system.")
                        print("The application will now use system-installed FiraCode font.")
                    elif result['project_available']:
                        print("\n✅ FiraCode is available in project directory.")
                        print("The application will use project FiraCode font.")
                        print("(System installation failed due to permissions)")
                    else:
                        print("\n❌ FiraCode not found in project directory.")
                        print("Please ensure fonts/FiraCode-Regular.ttf exists.")
                    break
                
                elif choice == "2":
                    print("\n📋 Manual Installation Instructions:")
                    print("=" * 40)
                    print("1. Navigate to the 'fonts' directory in this project")
                    print("2. Find 'FiraCode-Regular.ttf' file")
                    print("3. Right-click on the font file")
                    print("4. Select 'Install' or 'Install for all users'")
                    print("5. Restart the application")
                    print("\nAlternatively:")
                    print("- Copy FiraCode-Regular.ttf to C:/Windows/Fonts/ (Windows)")
                    print("- Copy to ~/Library/Fonts/ (macOS)")
                    print("- Copy to ~/.local/share/fonts/ (Linux)")
                    break
                
                elif choice == "3":
                    print("\nTesting font setup...")
                    
                    # Test font loading
                    try:
                        sys.path.append('src')
                        from barcode_mode import encode, save_barcode_image
                        
                        # Create test barcode
                        test_data = encode(
                            "TEST",
                            custom_text_content="Font Test: Hello World 123!",
                            font_size=16
                        )
                        
                        save_success = save_barcode_image(test_data, "machine_files/font_test.png")
                        
                        if save_success:
                            print("✅ Font test PASSED")
                            print("   Test barcode created: machine_files/font_test.png")
                            print("   Please check the image to verify font rendering")
                        else:
                            print("❌ Font test FAILED")
                    
                    except Exception as e:
                        print(f"❌ Font test ERROR: {e}")
                    break
                
                elif choice == "4":
                    print("Exiting...")
                    break
                
                else:
                    print("Invalid choice. Please enter 1-4.")
            
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
    
    except ImportError as e:
        print(f"❌ Error: Could not import font installer: {e}")
        print("Please ensure all required files are present.")

if __name__ == "__main__":
    main()
