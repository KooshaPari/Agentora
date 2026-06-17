"""
Load testing utilities for MCP servers.
"""

import asyncio
import time
from typing import Any, Dict, List


class LoadTester:
    """
    Load tester for MCP tools.
    """

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.results: List[Dict[str, Any]] = []

    async def run_load_test(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        num_requests: int = 100,
        concurrency: int = 10,
    ) -> Dict[str, Any]:
        """Run load test on a tool.

        Args:
            tool_name: Name of tool to test
            arguments: Tool arguments
            num_requests: Total number of requests
            concurrency: Number of concurrent requests

        Returns:
            Dict with performance metrics

        Usage:
            load_tester = LoadTester(mcp_client)
            results = await load_tester.run_load_test(
                "chat",
                {"prompt": "test"},
                num_requests=1000,
                concurrency=50
            )
            print(f"Average response time: {results['avg_time']}")
        """
        start_time = time.time()
        results = []

        # Create batches for concurrency
        batches = [
            list(range(i, min(i + concurrency, num_requests)))
            for i in range(0, num_requests, concurrency)
        ]

        for batch in batches:
            tasks = [self._single_request(tool_name, arguments) for _ in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate metrics
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if not (isinstance(r, dict) and r.get("success"))]

        response_times = [r.get("_duration", 0) for r in successful]

        return {
            "total_requests": num_requests,
            "successful": len(successful),
            "failed": len(failed),
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
        }

    async def _single_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute single request with timing.
        """
        start = time.time()
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            result["_duration"] = time.time() - start
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "_duration": time.time() - start,
            }
