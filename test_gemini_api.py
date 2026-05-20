#!/usr/bin/env python3
"""
Test script for verifying Gemini API key functionality.
"""
import os
import sys

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Error: google-generativeai package not installed")
    print("Install it with: pip install google-generativeai")
    sys.exit(1)


def test_gemini_api(api_key: str = None):
    """Test if the Gemini API key is valid and working."""
    
    # Get API key from parameter or environment variable
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("No API key found")
        return False
    
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # List available models to verify API access
        print("\n📋 Available models:")
        models = genai.list_models()
        model_count = 0
        for model in models:
            if 'gemini' in model.name.lower():
                print(f"  ✓ {model.name}")
                model_count += 1
        
        if model_count == 0:
            print("  ⚠️  No Gemini models found")
            return False
        
        # Test a simple generation
        print("\n🤖 Testing text generation...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("What are the top 5 strategies for effective ad recommendations?")
        
        print(f"\n✅ Response received:")
        print(f"  {response.text}")
        
        print("\n" + "=" * 50)
        print("✅ SUCCESS: Your Gemini API key is working!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: API key test failed")
        print(f"Error: {str(e)}")
        print("\nPossible issues:")
        print("  • Invalid API key")
        print("  • API key not activated")
        print("  • Network connectivity issues")
        print("  • API quota exceeded")
        print("\nGet your API key at: https://makersuite.google.com/app/apikey")
        return False


if __name__ == "__main__":
    # Get API key from command line argument if provided
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = test_gemini_api(api_key)
    sys.exit(0 if success else 1)
