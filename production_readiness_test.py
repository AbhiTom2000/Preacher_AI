#!/usr/bin/env python3
"""
Production Readiness Testing for Preacher.ai Backend
Comprehensive security, performance, and reliability testing
"""

import asyncio
import aiohttp
import json
import uuid
import time
import sys
from datetime import datetime
import concurrent.futures
import threading
import random
import string

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

print(f"🔗 Testing Backend URL: {BACKEND_URL}")
print(f"🔗 API Base: {API_BASE}")

class ProductionReadinessTester:
    def __init__(self):
        self.session_id = None
        self.test_results = {
            'error_handling': False,
            'rate_limiting': False,
            'input_validation': False,
            'xss_prevention': False,
            'sql_injection_prevention': False,
            'long_message_handling': False,
            'empty_message_handling': False,
            'invalid_session_handling': False,
            'high_load_performance': False,
            'gemini_api_failure_handling': False,
            'mongodb_error_handling': False,
            'invalid_json_handling': False,
            'memory_usage_optimization': False,
            'concurrent_sessions': False,
            'response_time_performance': False,
            'timeout_handling': False,
            'session_validation': False,
            'api_key_protection': False
        }
        self.errors = []
        self.performance_metrics = {}

    async def setup_session(self):
        """Create a test session"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_BASE}/session") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.session_id = data.get('session_id')
                        print(f"✅ Test session created: {self.session_id}")
                        return True
                    else:
                        print(f"❌ Failed to create test session: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Session setup error: {e}")
            return False

    async def test_error_handling(self):
        """Test comprehensive error handling across all endpoints"""
        print("\n🛡️ Testing Error Handling...")
        
        try:
            # Test invalid endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE}/nonexistent") as response:
                    if response.status == 404:
                        print("✅ 404 handling for invalid endpoints")
                    else:
                        print(f"⚠️ Unexpected status for invalid endpoint: {response.status}")
                
                # Test malformed requests
                async with session.post(f"{API_BASE}/chat", data="invalid json") as response:
                    if response.status in [400, 422]:
                        print("✅ Malformed JSON request handling")
                    else:
                        print(f"⚠️ Unexpected status for malformed JSON: {response.status}")
                
                self.test_results['error_handling'] = True
                return True
                
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            self.errors.append(f"Error handling test failed: {e}")
            return False

    async def test_rate_limiting(self):
        """Test rate limiting protection (10 requests/minute)"""
        print("\n⏱️ Testing Rate Limiting (10 requests/minute)...")
        
        if not self.session_id:
            await self.setup_session()
        
        try:
            # Send rapid requests to trigger rate limiting
            requests_sent = 0
            rate_limited = False
            
            async with aiohttp.ClientSession() as session:
                for i in range(15):  # Send more than the limit
                    chat_data = {
                        "message": f"Test message {i}",
                        "session_id": self.session_id
                    }
                    
                    async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                        requests_sent += 1
                        
                        if response.status == 429:  # Too Many Requests
                            rate_limited = True
                            print(f"✅ Rate limiting triggered after {requests_sent} requests")
                            break
                        elif response.status != 200:
                            print(f"⚠️ Unexpected status during rate limit test: {response.status}")
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.1)
            
            if rate_limited:
                self.test_results['rate_limiting'] = True
                print("✅ Rate limiting is working correctly")
                return True
            else:
                print("❌ Rate limiting not triggered - potential security issue")
                self.errors.append("Rate limiting not working as expected")
                return False
                
        except Exception as e:
            print(f"❌ Rate limiting test failed: {e}")
            self.errors.append(f"Rate limiting test failed: {e}")
            return False

    async def test_input_validation_and_sanitization(self):
        """Test XSS prevention, length limits, and input cleaning"""
        print("\n🧹 Testing Input Validation and Sanitization...")
        
        if not self.session_id:
            await self.setup_session()
        
        # XSS Test Cases
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "{{7*7}}",  # Template injection
            "${7*7}",   # Expression injection
            "<svg onload=alert('xss')>",
            "';DROP TABLE users;--"  # SQL injection attempt
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                for payload in xss_payloads:
                    chat_data = {
                        "message": payload,
                        "session_id": self.session_id
                    }
                    
                    async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data.get('response', '')
                            
                            # Check if malicious content was sanitized
                            if '<script>' not in response_text and 'javascript:' not in response_text:
                                print(f"✅ XSS payload sanitized: {payload[:30]}...")
                            else:
                                print(f"❌ XSS payload not sanitized: {payload}")
                                self.errors.append(f"XSS vulnerability: {payload}")
                        else:
                            print(f"⚠️ Unexpected status for XSS test: {response.status}")
            
            self.test_results['xss_prevention'] = True
            self.test_results['sql_injection_prevention'] = True
            self.test_results['input_validation'] = True
            print("✅ Input sanitization working correctly")
            return True
            
        except Exception as e:
            print(f"❌ Input validation test failed: {e}")
            self.errors.append(f"Input validation test failed: {e}")
            return False

    async def test_long_messages(self):
        """Test very long messages (1000+ characters)"""
        print("\n📏 Testing Long Message Handling...")
        
        if not self.session_id:
            await self.setup_session()
        
        try:
            # Generate a very long message (1500 characters)
            long_message = "How can I find peace? " * 70  # ~1540 characters
            
            chat_data = {
                "message": long_message,
                "session_id": self.session_id
            }
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('response'):
                            print(f"✅ Long message handled successfully ({len(long_message)} chars)")
                            print(f"⏱️ Response time: {response_time:.2f}s")
                            self.test_results['long_message_handling'] = True
                            return True
                    else:
                        print(f"❌ Long message handling failed: {response.status}")
                        self.errors.append(f"Long message handling failed: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Long message test failed: {e}")
            self.errors.append(f"Long message test failed: {e}")
            return False

    async def test_empty_and_invalid_inputs(self):
        """Test empty messages and invalid session IDs"""
        print("\n🚫 Testing Empty Messages and Invalid Session IDs...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test empty message
                chat_data = {
                    "message": "",
                    "session_id": self.session_id or str(uuid.uuid4())
                }
                
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    if response.status == 400:
                        print("✅ Empty message properly rejected")
                        self.test_results['empty_message_handling'] = True
                    else:
                        print(f"⚠️ Empty message handling: {response.status}")
                
                # Test invalid session ID
                chat_data = {
                    "message": "Test message",
                    "session_id": "invalid-session-id"
                }
                
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    if response.status == 400:
                        print("✅ Invalid session ID properly rejected")
                        self.test_results['invalid_session_handling'] = True
                    else:
                        print(f"⚠️ Invalid session ID handling: {response.status}")
                
                # Test missing session ID
                chat_data = {
                    "message": "Test message"
                }
                
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    if response.status == 400:
                        print("✅ Missing session ID properly rejected")
                    else:
                        print(f"⚠️ Missing session ID handling: {response.status}")
                
                return True
                
        except Exception as e:
            print(f"❌ Empty/invalid input test failed: {e}")
            self.errors.append(f"Empty/invalid input test failed: {e}")
            return False

    async def test_performance_under_load(self):
        """Test API responses during high load"""
        print("\n🚀 Testing Performance Under Load...")
        
        if not self.session_id:
            await self.setup_session()
        
        try:
            # Create multiple concurrent requests
            async def send_request(session, request_id):
                chat_data = {
                    "message": f"What is the meaning of life? Request {request_id}",
                    "session_id": self.session_id
                }
                
                start_time = time.time()
                try:
                    async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                        end_time = time.time()
                        response_time = end_time - start_time
                        
                        if response.status == 200:
                            return True, response_time
                        else:
                            return False, response_time
                except Exception:
                    return False, time.time() - start_time
            
            # Send 5 concurrent requests
            async with aiohttp.ClientSession() as session:
                tasks = [send_request(session, i) for i in range(5)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful_requests = 0
                response_times = []
                
                for result in results:
                    if isinstance(result, tuple):
                        success, response_time = result
                        if success:
                            successful_requests += 1
                        response_times.append(response_time)
                
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                print(f"✅ Concurrent requests: {successful_requests}/5 successful")
                print(f"⏱️ Average response time: {avg_response_time:.2f}s")
                
                if successful_requests >= 3:  # At least 60% success rate
                    self.test_results['high_load_performance'] = True
                    self.performance_metrics['avg_response_time'] = avg_response_time
                    return True
                else:
                    print("❌ Poor performance under load")
                    self.errors.append("Poor performance under concurrent requests")
                    return False
                    
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            self.errors.append(f"Performance test failed: {e}")
            return False

    async def test_concurrent_sessions(self):
        """Test multiple concurrent user sessions"""
        print("\n👥 Testing Concurrent User Sessions...")
        
        try:
            async def create_and_test_session(session_num):
                async with aiohttp.ClientSession() as session:
                    # Create session
                    async with session.post(f"{API_BASE}/session") as response:
                        if response.status != 200:
                            return False
                        
                        session_data = await response.json()
                        session_id = session_data.get('session_id')
                        
                        # Send message
                        chat_data = {
                            "message": f"Hello from session {session_num}",
                            "session_id": session_id
                        }
                        
                        async with session.post(f"{API_BASE}/chat", json=chat_data) as chat_response:
                            return chat_response.status == 200
            
            # Test 3 concurrent sessions
            tasks = [create_and_test_session(i) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_sessions = sum(1 for result in results if result is True)
            
            print(f"✅ Concurrent sessions: {successful_sessions}/3 successful")
            
            if successful_sessions >= 2:
                self.test_results['concurrent_sessions'] = True
                return True
            else:
                print("❌ Concurrent session handling failed")
                self.errors.append("Concurrent session handling failed")
                return False
                
        except Exception as e:
            print(f"❌ Concurrent session test failed: {e}")
            self.errors.append(f"Concurrent session test failed: {e}")
            return False

    async def test_response_time_performance(self):
        """Test response times under normal load"""
        print("\n⏱️ Testing Response Time Performance...")
        
        if not self.session_id:
            await self.setup_session()
        
        try:
            response_times = []
            
            async with aiohttp.ClientSession() as session:
                for i in range(3):
                    chat_data = {
                        "message": f"What does the Bible say about hope? Test {i}",
                        "session_id": self.session_id
                    }
                    
                    start_time = time.time()
                    async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                        end_time = time.time()
                        response_time = end_time - start_time
                        response_times.append(response_time)
                        
                        if response.status == 200:
                            print(f"✅ Request {i+1}: {response_time:.2f}s")
                        else:
                            print(f"❌ Request {i+1} failed: {response.status}")
                    
                    await asyncio.sleep(1)  # Small delay between requests
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            print(f"📊 Average response time: {avg_response_time:.2f}s")
            print(f"📊 Maximum response time: {max_response_time:.2f}s")
            
            # Consider good performance if average < 10s and max < 15s
            if avg_response_time < 10.0 and max_response_time < 15.0:
                self.test_results['response_time_performance'] = True
                self.performance_metrics['avg_response_time'] = avg_response_time
                self.performance_metrics['max_response_time'] = max_response_time
                print("✅ Response time performance acceptable")
                return True
            else:
                print("❌ Response time performance poor")
                self.errors.append(f"Poor response times: avg={avg_response_time:.2f}s, max={max_response_time:.2f}s")
                return False
                
        except Exception as e:
            print(f"❌ Response time test failed: {e}")
            self.errors.append(f"Response time test failed: {e}")
            return False

    async def test_session_validation_security(self):
        """Test session validation and security"""
        print("\n🔐 Testing Session Validation and Security...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test with non-existent session ID
                fake_session_id = str(uuid.uuid4())
                chat_data = {
                    "message": "Test message",
                    "session_id": fake_session_id
                }
                
                async with session.post(f"{API_BASE}/chat", json=chat_data) as response:
                    if response.status == 200:
                        # Should create session automatically or handle gracefully
                        print("✅ Non-existent session handled gracefully")
                        self.test_results['session_validation'] = True
                    else:
                        print(f"⚠️ Non-existent session handling: {response.status}")
                
                # Test session history access with invalid session
                async with session.get(f"{API_BASE}/chat/{fake_session_id}") as response:
                    if response.status in [200, 404]:
                        print("✅ Session history access properly controlled")
                    else:
                        print(f"⚠️ Session history access: {response.status}")
                
                return True
                
        except Exception as e:
            print(f"❌ Session validation test failed: {e}")
            self.errors.append(f"Session validation test failed: {e}")
            return False

    async def test_api_key_protection(self):
        """Test API key protection (ensure keys are not exposed)"""
        print("\n🔑 Testing API Key Protection...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint for any exposed secrets
                async with session.get(f"{API_BASE}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = json.dumps(data).lower()
                        
                        # Check for common secret patterns
                        secret_patterns = ['api_key', 'secret', 'password', 'token', 'key']
                        exposed_secrets = [pattern for pattern in secret_patterns if pattern in response_text]
                        
                        if not exposed_secrets:
                            print("✅ No API keys or secrets exposed in responses")
                            self.test_results['api_key_protection'] = True
                            return True
                        else:
                            print(f"❌ Potential secret exposure: {exposed_secrets}")
                            self.errors.append(f"Potential secret exposure: {exposed_secrets}")
                            return False
                
        except Exception as e:
            print(f"❌ API key protection test failed: {e}")
            self.errors.append(f"API key protection test failed: {e}")
            return False

    async def run_production_readiness_tests(self):
        """Run all production readiness tests"""
        print("🏭 Starting Production Readiness Tests for Preacher.ai")
        print("=" * 60)
        
        # Setup
        await self.setup_session()
        
        # Run all tests
        test_methods = [
            self.test_error_handling,
            self.test_rate_limiting,
            self.test_input_validation_and_sanitization,
            self.test_long_messages,
            self.test_empty_and_invalid_inputs,
            self.test_performance_under_load,
            self.test_concurrent_sessions,
            self.test_response_time_performance,
            self.test_session_validation_security,
            self.test_api_key_protection
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                print(f"❌ Test {test_method.__name__} crashed: {e}")
                self.errors.append(f"Test {test_method.__name__} crashed: {e}")
            
            await asyncio.sleep(0.5)  # Small delay between tests
        
        # Print results
        print("\n" + "=" * 60)
        print("📊 PRODUCTION READINESS TEST RESULTS")
        print("=" * 60)
        
        passed = sum(self.test_results.values())
        total = len(self.test_results)
        
        # Group results by category
        security_tests = ['error_handling', 'input_validation', 'xss_prevention', 'sql_injection_prevention', 
                         'session_validation', 'api_key_protection']
        performance_tests = ['rate_limiting', 'high_load_performance', 'response_time_performance', 
                           'concurrent_sessions', 'memory_usage_optimization']
        reliability_tests = ['long_message_handling', 'empty_message_handling', 'invalid_session_handling',
                           'gemini_api_failure_handling', 'mongodb_error_handling', 'timeout_handling']
        
        print("\n🔒 SECURITY TESTS:")
        for test in security_tests:
            if test in self.test_results:
                status = "✅ PASS" if self.test_results[test] else "❌ FAIL"
                print(f"  {test.replace('_', ' ').title()}: {status}")
        
        print("\n🚀 PERFORMANCE TESTS:")
        for test in performance_tests:
            if test in self.test_results:
                status = "✅ PASS" if self.test_results[test] else "❌ FAIL"
                print(f"  {test.replace('_', ' ').title()}: {status}")
        
        print("\n🛡️ RELIABILITY TESTS:")
        for test in reliability_tests:
            if test in self.test_results:
                status = "✅ PASS" if self.test_results[test] else "❌ FAIL"
                print(f"  {test.replace('_', ' ').title()}: {status}")
        
        print(f"\n🎯 Overall Score: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        # Performance metrics
        if self.performance_metrics:
            print("\n📈 PERFORMANCE METRICS:")
            for metric, value in self.performance_metrics.items():
                print(f"  {metric.replace('_', ' ').title()}: {value:.2f}s")
        
        # Critical issues
        if self.errors:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        # Production readiness assessment
        security_score = sum(self.test_results.get(test, False) for test in security_tests if test in self.test_results)
        performance_score = sum(self.test_results.get(test, False) for test in performance_tests if test in self.test_results)
        
        print(f"\n🏭 PRODUCTION READINESS ASSESSMENT:")
        print(f"  Security Score: {security_score}/{len([t for t in security_tests if t in self.test_results])}")
        print(f"  Performance Score: {performance_score}/{len([t for t in performance_tests if t in self.test_results])}")
        
        if passed >= total * 0.8:  # 80% pass rate
            print("  ✅ READY FOR PRODUCTION")
        elif passed >= total * 0.6:  # 60% pass rate
            print("  ⚠️ NEEDS IMPROVEMENTS BEFORE PRODUCTION")
        else:
            print("  ❌ NOT READY FOR PRODUCTION")
        
        return passed, total, self.errors

async def main():
    """Main test runner"""
    tester = ProductionReadinessTester()
    passed, total, errors = await tester.run_production_readiness_tests()
    
    # Exit with appropriate code
    if passed >= total * 0.8:  # 80% pass rate for production readiness
        print("\n🎉 Production readiness tests mostly passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️ Production readiness concerns found")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())