#!/usr/bin/env python3
"""
Simple end-to-end test of the HTML generation system
Run this to verify everything is working
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

def test_system():
    print("=" * 80)
    print("TESTING HTML GENERATION SYSTEM")
    print("=" * 80)
    
    # Test 1: Health check
    print("\n1️⃣  Testing health check...")
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200, "Health check failed"
    health = response.json()
    print(f"   ✓ Server healthy: {health['status']}")
    print(f"   ✓ Active sessions: {health['sessions_active']}")
    
    # Test 2: Create session
    print("\n2️⃣  Creating session...")
    response = requests.post(f"{BASE_URL}/api/session/create")
    assert response.status_code == 200, "Session creation failed"
    session_data = response.json()
    session_id = session_data['session_id']
    print(f"   ✓ Session created: {session_id[:12]}...")
    
    # Test 3: Get session state (should be empty)
    print("\n3️⃣  Checking initial state...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}/state")
    assert response.status_code == 200, "Get state failed"
    print("   ✓ State retrieved successfully")
    
    # Test 4: Send message
    print("\n4️⃣  Sending message ('flower shop')...")
    print("   ⏳ Waiting for AI to generate HTML (30-60 seconds)...")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={
            "session_id": session_id,
            "message": "flower shop"
        },
        timeout=120  # 2 minute timeout
    )
    elapsed = time.time() - start_time
    
    assert response.status_code == 200, f"Message send failed: {response.status_code}"
    data = response.json()
    
    assert data['success'], f"Response not successful: {data.get('error')}"
    print(f"   ✓ AI generated response in {elapsed:.1f} seconds")
    print(f"   ✓ Response: {data['response']}")
    
    # Test 5: Check progress
    print("\n5️⃣  Checking generation progress...")
    progress = data['state']['progress']
    print(f"   ✓ Requirements: {'✅' if progress['requirements'] else '❌'}")
    print(f"   ✓ UX Design: {'✅' if progress['ux_design'] else '❌'}")
    print(f"   ✓ Aesthetics: {'✅' if progress['aesthetics'] else '❌'}")
    print(f"   ✓ HTML Generated: {'✅' if progress['html_generation'] else '❌'}")
    print(f"   ✓ Validation: {'✅' if progress['validation'] else '❌'}")
    
    # Test 6: Verify HTML content
    print("\n6️⃣  Checking HTML content...")
    html_content = data['state']['html_content']
    assert html_content, "No HTML content generated"
    assert '<!DOCTYPE html>' in html_content, "Missing DOCTYPE"
    assert '<html' in html_content, "Missing html tag"
    assert '</html>' in html_content, "Missing closing html tag"
    assert 'flower' in html_content.lower() or 'shop' in html_content.lower(), "Website content doesn't mention 'flower shop'"
    
    size_kb = len(html_content) / 1024
    print(f"   ✓ HTML generated: {size_kb:.2f} KB")
    print(f"   ✓ Contains DOCTYPE: ✅")
    print(f"   ✓ Valid HTML structure: ✅")
    
    # Test 7: Get preview
    print("\n7️⃣  Testing preview endpoint...")
    response = requests.get(
        f"{BASE_URL}/api/preview/html",
        params={"session_id": session_id}
    )
    assert response.status_code == 200, "Preview failed"
    preview = response.json()
    assert preview['html_content'] == html_content, "Preview content mismatch"
    print("   ✓ Preview content matches generated HTML")
    
    # Test 8: Download HTML
    print("\n8️⃣  Testing download endpoint...")
    response = requests.post(
        f"{BASE_URL}/api/download/html",
        params={"session_id": session_id}
    )
    assert response.status_code == 200, "Download failed"
    download_data = response.json()
    assert download_data['success'], "Download not successful"
    assert download_data['filename'], "No filename provided"
    print(f"   ✓ Download ready: {download_data['filename']}")
    print(f"   ✓ File size: {len(download_data['content']) / 1024:.2f} KB")
    
    # Test 9: Get messages
    print("\n9️⃣  Getting message history...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}/messages")
    assert response.status_code == 200, "Get messages failed"
    messages = response.json()
    assert messages['count'] >= 2, "Should have at least 2 messages (user + bot)"
    print(f"   ✓ Message count: {messages['count']}")
    print(f"   ✓ First message: {messages['messages'][0]['role']} - '{messages['messages'][0]['content'][:50]}...'")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   - Session ID: {session_id}")
    print(f"   - Generation time: {elapsed:.1f} seconds")
    print(f"   - HTML size: {size_kb:.2f} KB")
    print(f"   - Messages: {messages['count']}")
    print(f"\n🎉 System is working correctly!")
    print(f"\n📱 Access UI at: http://localhost:5000")
    print(f"📚 API docs at: http://localhost:5000/docs")
    
    return True

if __name__ == "__main__":
    try:
        success = test_system()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at http://localhost:5000")
        print("   Make sure the server is running: uvicorn app:app --reload")
        sys.exit(1)
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
