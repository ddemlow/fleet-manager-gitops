import os
import requests

api_key = os.getenv('SC_FM_APIKEY')
headers = {'api-key': api_key, 'accept': 'application/json'}

# Check for pagination - try different approaches
all_apps = []
page = 1
limit = 50  # Try to get more per page

# First try with limit parameter
url = f'https://api.scalecomputing.com/api/v2/deployment-applications?limit={limit}'
response = requests.get(url, headers=headers)
data = response.json()
apps = data.get('items', [])
all_apps.extend(apps)

print(f"Initial request: {len(apps)} apps")

# If we got fewer than expected, try pagination
if len(apps) < limit and 'next' in data:
    print("Found 'next' field, trying pagination...")
    while 'next' in data and data['next']:
        response = requests.get(data['next'], headers=headers)
        data = response.json()
        apps = data.get('items', [])
        all_apps.extend(apps)
        print(f"Next page: {len(apps)} apps")

# Alternative: try offset-based pagination
if len(all_apps) < 40:  # You mentioned 40 in UI
    print("Trying offset-based pagination...")
    offset = len(all_apps)
    while offset < 100:  # Reasonable limit
        url = f'https://api.scalecomputing.com/api/v2/deployment-applications?limit={limit}&offset={offset}'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            break
        data = response.json()
        apps = data.get('items', [])
        if not apps:  # No more apps
            break
        all_apps.extend(apps)
        print(f"Offset {offset}: {len(apps)} apps")
        offset += len(apps)

print(f"\nTotal apps found: {len(all_apps)}")
print("\nAll applications:")
for app in all_apps:
    print(f"- {app.get('name')}")

# Look specifically for nginx3
nginx3_apps = [app for app in all_apps if 'nginx3' in app.get('name', '').lower()]
print(f"\nNginx3 apps found: {len(nginx3_apps)}")
for app in nginx3_apps:
    print(f"- {app.get('name')} (ID: {app.get('id')})")
