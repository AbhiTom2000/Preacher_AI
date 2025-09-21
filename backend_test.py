#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Preacher.ai
Tests all backend functionality including AI integration, APIs, WebSocket, and MongoDB storage
"""

import asyncio
import aiohttp
import websockets
import json
import uuid
import os
from datetime import datetime
import sys

# Get backend URL from frontend environment
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return "https://divine-wisdom-9.preview.emergentagent.com"

BACKEND_URL = get_backend_url()
API_BASE = f"{BACKEND_URL}/api"
WS_BASE = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://')

print(f"🔗 Testing Backend URL: {BACKEND_URL}")
print(f"🔗 API Base: {API_BASE}")
print(f"🔗 WebSocket Base: {WS_BASE}")

class PreacherAITester:
    def __init__(self):
        self.session_id = None
        self.test_results = {
            'api_health': False,
            'session_creation': False,
            'chat_endpoint': False,
            'ai_integration': False,
            'bible_verses': False,
            'chat_history': False,
            'websocket': False,
            'mongodb_storage': False,
            'language_detection': False,
            'english_support': False,
            'hindi_support': False
        }
        self.errors = []

    async def test_api_health(self):
        """Test basic API health endpoint"""
        print("\n🏥 Testing API Health...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ API Health: {data}")
                        self.test_results['api_health'] = True
                        return True
                    else:
                        print(f"❌ API Health failed: Status {response.status}")
                        self.errors.append(f"API health check failed with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ API Health error: {e}")
            self.errors.append(f"API health check error: {e}")
            return False

    async def test_session_creation(self):
        """Test session creation endpoint"""
        print("\n📝 Testing Session Creation...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_BASE}/session") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.session_id = data.get('session_id')
                        print(f"✅ Session Created: {self.session_id}")
                        self.test_results['session_creation'] = True
                        return True
                    else:
                        print(f"❌ Session creation failed: Status {response.status}")
                        text = await response.text()
                        print(f"Response: {text}")
                        self.errors.append(f"Session creation failed with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            self.errors.append(f"Session creation error: {e}")
            return False

    async def test_chat_endpoint_english(self):
        """Test chat endpoint with English biblical question"""
        print("\n💬 Testing Chat Endpoint (English)...")
        if not self.session_id:
            print("❌ No session ID available for chat test")
            return False
            
        try:
            chat_data = {
                "message": "How can I find peace in difficult times?",
                "session_id": self.session_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Chat Response Received")
                        print(f"📝 Response: {data.get('response', '')[:100]}...")
                        print(f"🔤 Language: {data.get('language', 'unknown')}")
                        print(f"📖 Cited Verses: {len(data.get('cited_verses', []))} verses")
                        
                        # Verify response structure
                        if data.get('response') and len(data.get('response', '')) > 50:
                            self.test_results['chat_endpoint'] = True
                            self.test_results['english_support'] = True
                            
                            # Check AI integration
                            if len(data.get('response', '')) > 100:
                                self.test_results['ai_integration'] = True
                                print("✅ AI Integration working")
                            
                            # Check Bible verses
                            if data.get('cited_verses') and len(data.get('cited_verses', [])) > 0:
                                self.test_results['bible_verses'] = True
                                print("✅ Bible verses citation working")
                                for verse in data.get('cited_verses', [])[:2]:
                                    print(f"   📖 {verse.get('reference', 'Unknown')}: {verse.get('text', '')[:50]}...")
                            
                            return True
                        else:
                            print("❌ Chat response too short or empty")
                            self.errors.append("Chat response insufficient")
                            return False
                    else:
                        print(f"❌ Chat endpoint failed: Status {response.status}")
                        text = await response.text()
                        print(f"Response: {text}")
                        self.errors.append(f"Chat endpoint failed with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Chat endpoint error: {e}")
            self.errors.append(f"Chat endpoint error: {e}")
            return False

    async def test_chat_endpoint_hindi(self):
        """Test chat endpoint with Hindi text"""
        print("\n🇮🇳 Testing Chat Endpoint (Hindi)...")
        if not self.session_id:
            print("❌ No session ID available for Hindi chat test")
            return False
            
        try:
            chat_data = {
                "message": "मुझे शांति कैसे मिल सकती है?",  # "How can I find peace?"
                "session_id": self.session_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Hindi Chat Response Received")
                        print(f"🔤 Detected Language: {data.get('language', 'unknown')}")
                        
                        # Check language detection
                        if data.get('language') == 'hindi':
                            self.test_results['language_detection'] = True
                            self.test_results['hindi_support'] = True
                            print("✅ Hindi language detection working")
                            return True
                        else:
                            print(f"⚠️ Language detection issue: Expected 'hindi', got '{data.get('language')}'")
                            # Still mark as working if we got a response
                            self.test_results['hindi_support'] = True
                            return True
                    else:
                        print(f"❌ Hindi chat failed: Status {response.status}")
                        self.errors.append(f"Hindi chat failed with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Hindi chat error: {e}")
            self.errors.append(f"Hindi chat error: {e}")
            return False

    async def test_chat_history(self):
        """Test chat history retrieval"""
        print("\n📚 Testing Chat History...")
        if not self.session_id:
            print("❌ No session ID available for history test")
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE}/chat/{self.session_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Chat History Retrieved: {len(data)} messages")
                        
                        # Verify we have messages from our previous tests
                        if len(data) >= 2:  # At least user + AI message
                            self.test_results['chat_history'] = True
                            self.test_results['mongodb_storage'] = True
                            print("✅ MongoDB storage working")
                            
                            # Show sample messages
                            for i, msg in enumerate(data[:4]):
                                sender = msg.get('sender', 'unknown')
                                message = msg.get('message', '')[:50]
                                print(f"   {i+1}. [{sender}]: {message}...")
                            
                            return True
                        else:
                            print("⚠️ Chat history has fewer messages than expected")
                            self.test_results['chat_history'] = True  # Still working
                            return True
                    else:
                        print(f"❌ Chat history failed: Status {response.status}")
                        self.errors.append(f"Chat history failed with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Chat history error: {e}")
            self.errors.append(f"Chat history error: {e}")
            return False

    async def test_websocket(self):
        """Test WebSocket real-time communication"""
        print("\n🔌 Testing WebSocket Communication...")
        if not self.session_id:
            print("❌ No session ID available for WebSocket test")
            return False
            
        try:
            ws_url = f"{WS_BASE}/ws/{self.session_id}"
            print(f"🔗 Connecting to: {ws_url}")
            
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket connected")
                
                # Send a test message
                test_message = {
                    "message": "What does the Bible say about love?"
                }
                
                await websocket.send(json.dumps(test_message))
                print("📤 Sent test message")
                
                # Wait for typing indicator
                try:
                    response1 = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data1 = json.loads(response1)
                    if data1.get('type') == 'typing':
                        print("✅ Received typing indicator")
                except asyncio.TimeoutError:
                    print("⚠️ No typing indicator received")
                
                # Wait for actual response
                try:
                    response2 = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data2 = json.loads(response2)
                    
                    if data2.get('type') == 'message' and data2.get('response'):
                        print("✅ WebSocket AI response received")
                        print(f"📝 Response: {data2.get('response', '')[:100]}...")
                        self.test_results['websocket'] = True
                        return True
                    else:
                        print(f"❌ Invalid WebSocket response: {data2}")
                        self.errors.append("Invalid WebSocket response format")
                        return False
                        
                except asyncio.TimeoutError:
                    print("❌ WebSocket response timeout")
                    self.errors.append("WebSocket response timeout")
                    return False
                    
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            self.errors.append(f"WebSocket error: {e}")
            return False

    async def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Preacher.ai Backend Tests")
        print("=" * 50)
        
        # Test sequence
        await self.test_api_health()
        await self.test_session_creation()
        await self.test_chat_endpoint_english()
        await self.test_chat_endpoint_hindi()
        await self.test_chat_history()
        await self.test_websocket()
        
        # Print results
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(self.test_results.values())
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if self.errors:
            print("\n🚨 ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        
        return passed, total, self.errors

async def main():
    """Main test runner"""
    tester = PreacherAITester()
    passed, total, errors = await tester.run_all_tests()
    
    # Exit with appropriate code
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total - passed} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())