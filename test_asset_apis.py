#!/usr/bin/env python3
"""
Test script for Asset Management APIs
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
BRAND_ID = "68ea3a010ea62ad7022bcf5b"
CAMPAIGN_ID = "f08c1f1cb35f9a8fa68e7984"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNjhlOWVhMzA0OTUwMTg0MzRkZTBhMGVjIiwiZW1haWwiOiJhc2h3aW5pbmFnYXJnb2plNzAzQGdtYWlsLmNvbSIsInB1cnBvc2UiOiJhY2Nlc3MiLCJleHAiOjE3NjExMDQ2MjAsImlhdCI6MTc2MTAxODIyMH0._1Au7buNrMsHzQ2C7usZfWiaHKk2fAXluHTOXLKEnNo"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_health():
    """Test health endpoint"""
    print("🔍 Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_get_assets():
    """Test get campaign assets"""
    print("\n🔍 Testing Get Campaign Assets...")
    try:
        url = f"{BASE_URL}/api/brands/{BRAND_ID}/campaigns/{CAMPAIGN_ID}/assets"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Get assets failed: {e}")
        return False

def test_get_asset_filters():
    """Test get asset filters"""
    print("\n🔍 Testing Get Asset Filters...")
    try:
        url = f"{BASE_URL}/api/brands/{BRAND_ID}/campaigns/{CAMPAIGN_ID}/assets/filters"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Get filters failed: {e}")
        return False

def test_get_asset_stats():
    """Test get asset statistics"""
    print("\n🔍 Testing Get Asset Statistics...")
    try:
        url = f"{BASE_URL}/api/brands/{BRAND_ID}/campaigns/{CAMPAIGN_ID}/assets/stats"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Get stats failed: {e}")
        return False

def test_search_assets():
    """Test search assets"""
    print("\n🔍 Testing Search Assets...")
    try:
        url = f"{BASE_URL}/api/brands/{BRAND_ID}/campaigns/{CAMPAIGN_ID}/assets/search"
        data = {
            "query": "test",
            "page": 1,
            "limit": 10
        }
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Search assets failed: {e}")
        return False

def test_get_brand_guidelines():
    """Test get brand guidelines"""
    print("\n🔍 Testing Get Brand Guidelines...")
    try:
        url = f"{BASE_URL}/api/brands/{BRAND_ID}/guidelines"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Get guidelines failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Asset Management API Tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"Brand ID: {BRAND_ID}")
    print(f"Campaign ID: {CAMPAIGN_ID}")
    
    tests = [
        test_health,
        test_get_assets,
        test_get_asset_filters,
        test_get_asset_stats,
        test_search_assets,
        test_get_brand_guidelines
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
            print("✅ PASSED")
        else:
            print("❌ FAILED")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()
