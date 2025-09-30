"""
Setup script for Gemini API key configuration.
"""

import os
from pathlib import Path

def setup_gemini_api_key():
    """Setup Gemini API key in .env file"""
    
    print("🔧 Gemini API Setup")
    print("=" * 50)
    print()
    print("To use Gemini for data extraction, you need a Google AI API key.")
    print("Get your free API key from: https://makersuite.google.com/app/apikey")
    print()
    
    # Check if .env file exists
    env_file = Path(".env")
    
    if env_file.exists():
        print("📁 Found existing .env file")
        
        # Read current content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Check if GEMINI_API_KEY already exists
        if "GEMINI_API_KEY" in content:
            print("✅ GEMINI_API_KEY already exists in .env file")
            print("Current value:", os.environ.get("GEMINI_API_KEY", "Not set"))
            
            update = input("\nDo you want to update it? (y/n): ").lower().strip()
            if update != 'y':
                print("Setup cancelled.")
                return
        else:
            print("❌ GEMINI_API_KEY not found in .env file")
    else:
        print("📁 No .env file found, will create one")
    
    # Get API key from user
    print()
    api_key = input("Enter your Gemini API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Setup cancelled.")
        return
    
    # Update .env file
    if env_file.exists():
        # Read current content
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update or add GEMINI_API_KEY
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={api_key}\n"
                updated = True
                break
        
        if not updated:
            lines.append(f"GEMINI_API_KEY={api_key}\n")
        
        # Write back
        with open(env_file, 'w') as f:
            f.writelines(lines)
    else:
        # Create new .env file
        with open(env_file, 'w') as f:
            f.write(f"GEMINI_API_KEY={api_key}\n")
    
    print("✅ Gemini API key saved to .env file")
    print()
    print("🚀 You can now run the smart hybrid extractor!")
    print("   python3 test_smart_hybrid.py")
    print()
    print("💰 Cost Information:")
    print("   • Gemini 1.5 Flash: ~$0.0001 per 1K input tokens")
    print("   • Typical cost: ~$0.001-0.01 per scheme")
    print("   • For 244 schemes: ~$0.25-2.50 total (very affordable!)")
    print("   • Much cheaper than OpenAI GPT-4")

if __name__ == "__main__":
    setup_gemini_api_key()
