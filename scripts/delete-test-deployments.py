#!/usr/bin/env python3
"""
Delete test deployments and applications manually
"""

import os
import sys
import requests
import argparse

def delete_test_items():
    """Delete test deployments and applications"""
    
    fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
    api_key = os.getenv('SC_FM_APIKEY')
    
    if not api_key:
        print("❌ SC_FM_APIKEY environment variable not set")
        return False
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Items to delete
    items_to_delete = [
        {
            'type': 'deployment',
            'name': 'k0s-demo-test-dd_szt15b',
            'id': 'd89a566a-c734-409c-866b-d5e0c1b6ecf2'
        },
        {
            'type': 'deployment', 
            'name': 'k0s-demo-test-DDvsns',
            'id': 'ce195b31-1ea0-4b86-be2d-f832c8652076'
        },
        {
            'type': 'application',
            'name': 'k0s-demo-test',
            'id': 'e55472d7-d046-417e-a9f6-870b3179ed66'
        }
    ]
    
    print("🗑️  Deleting test deployments and applications...")
    
    for item in items_to_delete:
        if item['type'] == 'deployment':
            url = f"{fm_api_url}/deployments/{item['id']}"
        else:
            url = f"{fm_api_url}/deployment-applications/{item['id']}"
        
        print(f"🗑️  Deleting {item['type']}: {item['name']}")
        
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 204:
            print(f"✅ Deleted {item['type']}: {item['name']}")
        else:
            print(f"❌ Failed to delete {item['type']} {item['name']}: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text}")
    
    print("\n🎯 Cleanup complete!")

if __name__ == "__main__":
    delete_test_items()
