#!/usr/bin/env python3
"""Debug script to check all registered routes"""
import sys
sys.path.insert(0, 'src')

from fastapi import FastAPI
from fastapi.routing import APIRoute

# Import the app
from main import app

print("=" * 60)
print("REGISTERED ROUTES IN FASTAPI APP")
print("=" * 60)

# Get all routes
routes = []
for route in app.routes:
    if isinstance(route, APIRoute):
        routes.append({
            'path': route.path,
            'methods': route.methods,
            'name': route.name
        })

# Sort by path
routes.sort(key=lambda x: x['path'])

# Group by path prefix
auth_routes = [r for r in routes if '/auth' in r['path']]
api_routes = [r for r in routes if '/api' in r['path']]
other_routes = [r for r in routes if '/auth' not in r['path'] and '/api' not in r['path']]

print("\n📌 AUTH ROUTES:")
if auth_routes:
    for route in auth_routes:
        print(f"  {', '.join(route['methods']):6} {route['path']:40} [{route['name']}]")
else:
    print("  ❌ No auth routes found!")

print("\n📌 API ROUTES:")
for route in api_routes[:10]:  # Show first 10
    print(f"  {', '.join(route['methods']):6} {route['path']:40} [{route['name']}]")

print("\n📌 OTHER ROUTES:")
for route in other_routes[:10]:  # Show first 10
    print(f"  {', '.join(route['methods']):6} {route['path']:40} [{route['name']}]")

print("\n" + "=" * 60)
print(f"Total routes registered: {len(routes)}")
print("=" * 60)

# Check if auth router is imported
try:
    from src.presentation.auth_routes import router as auth_router
    print("\n✅ Auth router imported successfully")
    print(f"   Routes in auth router: {len(auth_router.routes)}")
    for route in auth_router.routes:
        if isinstance(route, APIRoute):
            print(f"   - {', '.join(route.methods):6} {route.path}")
except Exception as e:
    print(f"\n❌ Failed to import auth router: {e}")