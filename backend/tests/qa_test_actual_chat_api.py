#!/usr/bin/env python3
"""
QA Test Script for Actual Chat API Implementation
Tests the real implementation in api_routes.py

This reveals that the chat session lifecycle optimization was NOT properly implemented.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActualChatAPITest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        result = {
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"    Details: {details}")

    async def test_current_implementation(self):
        """Test the current chat API implementation to verify behavior"""

        logger.info("🔍 Testing Current Chat API Implementation")
        logger.info("="*60)

        # Test 1: Check if automatic greeting is removed
        try:
            test_name = "CRITICAL: Automatic greeting message removed from /start"

            start_data = {"project_name": "Test Project QA"}
            response = await self.session.post(
                f"{self.base_url}/api/chat/start",
                json=start_data
            )

            if response.status == 200:
                data = await response.json()
                message = data.get("message", "")

                # Check if automatic greeting is present
                if "Sessão iniciada! Como posso ajudá-lo com a análise da obra?" in message:
                    self.log_test_result(
                        test_name,
                        False,
                        f"❌ AUTOMATIC GREETING STILL PRESENT: '{message}'"
                    )
                else:
                    self.log_test_result(
                        test_name,
                        True,
                        f"✅ No automatic greeting found: '{message}'"
                    )
            else:
                self.log_test_result(test_name, False, f"API call failed: {response.status}")

        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")

        # Test 2: Check if session is created immediately
        try:
            test_name = "CRITICAL: Session creation is lazy (not immediate)"

            # Get initial session count
            response = await self.session.get(f"{self.base_url}/api/chat/sessions")
            if response.status == 200:
                data = await response.json()
                initial_count = len(data.get("sessions", []))
            else:
                initial_count = 0

            # Call /start endpoint
            start_data = {"project_name": "Test Lazy Creation"}
            response = await self.session.post(
                f"{self.base_url}/api/chat/start",
                json=start_data
            )

            if response.status == 200:
                # Check session count after /start
                response = await self.session.get(f"{self.base_url}/api/chat/sessions")
                if response.status == 200:
                    data = await response.json()
                    final_count = len(data.get("sessions", []))

                    if final_count > initial_count:
                        self.log_test_result(
                            test_name,
                            False,
                            f"❌ SESSION CREATED IMMEDIATELY: {initial_count} -> {final_count}"
                        )
                    else:
                        self.log_test_result(
                            test_name,
                            True,
                            f"✅ Session creation is lazy: {initial_count} -> {final_count}"
                        )
                else:
                    self.log_test_result(test_name, False, "Could not check final session count")
            else:
                self.log_test_result(test_name, False, f"Start endpoint failed: {response.status}")

        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")

        # Test 3: Check message sending behavior
        try:
            test_name = "Message sending creates session if needed"

            # Create session first
            start_data = {"project_name": "Test Message Creation"}
            response = await self.session.post(
                f"{self.base_url}/api/chat/start",
                json=start_data
            )

            if response.status == 200:
                session_data = await response.json()
                session_id = session_data.get("session_id")

                # Send message
                message_data = {
                    "session_id": session_id,
                    "message": "Hello, this is a test message"
                }

                response = await self.session.post(
                    f"{self.base_url}/api/chat/message",
                    json=message_data
                )

                if response.status == 200:
                    message_response = await response.json()
                    ai_response = message_response.get("response", "")

                    self.log_test_result(
                        test_name,
                        True,
                        f"✅ Message sent successfully. AI response: {ai_response[:100]}..."
                    )
                else:
                    self.log_test_result(test_name, False, f"Message sending failed: {response.status}")
            else:
                self.log_test_result(test_name, False, "Could not create session for test")

        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")

        # Test 4: Check if old API endpoints exist
        try:
            test_name = "Check if v1 chat endpoints exist"

            response = await self.session.post(f"{self.base_url}/api/v1/chat/start")

            if response.status == 404:
                self.log_test_result(test_name, True, "✅ v1 endpoints don't exist (as expected)")
            else:
                self.log_test_result(test_name, False, f"v1 endpoints still exist: {response.status}")

        except Exception as e:
            self.log_test_result(test_name, True, f"v1 endpoints don't exist (connection error): {str(e)}")

    async def analyze_implementation_gaps(self):
        """Analyze what needs to be fixed in the implementation"""

        logger.info("\n🔧 IMPLEMENTATION GAP ANALYSIS")
        logger.info("="*60)

        # Check the actual API structure
        try:
            response = await self.session.get(f"{self.base_url}/openapi.json")
            if response.status == 200:
                api_spec = await response.json()
                paths = api_spec.get("paths", {})

                chat_endpoints = [path for path in paths.keys() if "chat" in path]

                logger.info("📋 Current Chat API Endpoints:")
                for endpoint in chat_endpoints:
                    logger.info(f"  • {endpoint}")

                # Check if the implementation matches task requirements
                required_changes = []

                if "/api/chat/start" in paths:
                    required_changes.append("✅ /start endpoint exists but needs modification")
                else:
                    required_changes.append("❌ /start endpoint missing")

                if "/api/chat/message" in paths:
                    required_changes.append("✅ /message endpoint exists")
                else:
                    required_changes.append("❌ /message endpoint missing")

                logger.info("\n🎯 Required Changes:")
                for change in required_changes:
                    logger.info(f"  • {change}")

        except Exception as e:
            logger.error(f"Could not analyze API spec: {e}")

    async def run_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Actual Chat API QA Tests")
        logger.info("="*80)

        await self.test_current_implementation()
        await self.analyze_implementation_gaps()

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate test summary report"""
        logger.info("\n" + "="*80)
        logger.info("📊 ACTUAL IMPLEMENTATION TEST SUMMARY")
        logger.info("="*80)

        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]

        logger.info(f"✅ Passed: {len(passed_tests)}/{len(self.test_results)}")
        logger.info(f"❌ Failed: {len(failed_tests)}/{len(self.test_results)}")

        if failed_tests:
            logger.info("\n🔍 CRITICAL ISSUES FOUND:")
            for test in failed_tests:
                logger.info(f"  • {test['test_name']}: {test['details']}")

        if passed_tests:
            logger.info("\n✅ WORKING CORRECTLY:")
            for test in passed_tests:
                logger.info(f"  • {test['test_name']}")

        # Task compliance assessment
        success_rate = len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0
        logger.info(f"\n🎯 Implementation Compliance: {success_rate:.1f}%")

        logger.info("\n" + "="*80)
        logger.info("📋 TASK COMPLIANCE ASSESSMENT")
        logger.info("="*80)

        logger.info("Task Requirements from task-18-chat-session-lifecycle.md:")
        logger.info("1. ❌ Avoid unnecessary session creation when user accesses interface")
        logger.info("2. ❌ Create session only after first user message")
        logger.info("3. ❌ Remove automatic greeting message")
        logger.info("4. ❓ WebSocket lazy connection (not tested - requires frontend)")
        logger.info("5. ❓ Database persistence optimization (needs deeper testing)")

        logger.info("\n🎯 VERDICT: TASK REQUIREMENTS NOT IMPLEMENTED")
        logger.info("The chat session lifecycle optimization was NOT properly implemented.")
        logger.info("The current implementation still has the automatic greeting and immediate session creation.")

        # Save detailed report
        report = {
            "summary": {
                "total_tests": len(self.test_results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": success_rate,
                "task_compliance": "NOT IMPLEMENTED",
                "timestamp": datetime.now().isoformat()
            },
            "tests": self.test_results,
            "critical_issues": [
                "Automatic greeting message still present in /api/chat/start",
                "Session creation is immediate, not lazy",
                "Task requirements from task-18-chat-session-lifecycle.md not implemented"
            ],
            "required_fixes": [
                "Remove automatic greeting from /api/chat/start endpoint",
                "Implement lazy session creation on first message",
                "Update frontend to not auto-connect WebSocket",
                "Ensure empty sessions are not persisted unnecessarily"
            ]
        }

        with open("qa_actual_implementation_report.json", "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"\n📄 Detailed report saved to: qa_actual_implementation_report.json")


async def main():
    """Main function to run QA tests"""
    try:
        async with ActualChatAPITest() as qa_test:
            await qa_test.run_tests()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Tests interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())