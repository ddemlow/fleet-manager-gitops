#!/usr/bin/env python3
"""
Test API connection and permissions
"""

import os
import requests

def test_api_connection():
    fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    api_key = os.getenv('SC_FM_APIKEY')
    
    print(f"🔍 API URL: {fm_api_url}")
    print(f"🔍 API Key length: {len(api_key) if api_key else 0}")
    
    if not api_key:
        print("❌ SC_FM_APIKEY not found")
        return False
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Test with a simple GET request
    print("🧪 Testing API connection...")
    try:
        response = requests.get(f"{fm_api_url}/deployments", headers=headers, timeout=10)
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API connection successful")
            data = response.json()
            print(f"📋 Found {len(data.get('items', []))} deployments")
            return True
        else:
            print(f"❌ API connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API connection error: {e}")
        return False

if __name__ == "__main__":
    test_api_connection()
