"""
Multi-endpoint test execution management.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

from .models import TestResult


class MultiEndpointManager:
    """
    Run tests on multiple environments simultaneously.
    """

    def __init__(self):
        self.endpoints: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, List[TestResult]] = {}

    def add_endpoint(self, name: str, config: Dict[str, Any]):
        """
        Add an endpoint configuration.
        """
        self.endpoints[name] = config
        self.results[name] = []

    def remove_endpoint(self, name: str):
        """
        Remove an endpoint.
        """
        self.endpoints.pop(name, None)
        self.results.pop(name, None)

    async def run_test_on_all(
        self, test_func: Callable, test_name: str, *args, **kwargs
    ) -> Dict[str, TestResult]:
        """
        Run a test on all configured endpoints.
        """
        tasks = []
        for endpoint_name, config in self.endpoints.items():
            task = self._run_on_endpoint(
                test_func, test_name, endpoint_name, config, *args, **kwargs
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        endpoint_results = {}
        for endpoint_name, result in zip(self.endpoints.keys(), results):
            if isinstance(result, Exception):
                result = TestResult(
                    test_name=test_name,
                    endpoint=endpoint_name,
                    success=False,
                    duration=0.0,
                    timestamp=time.time(),
                    details={"error": str(result)},
                )
            endpoint_results[endpoint_name] = result
            self.results[endpoint_name].append(result)

        return endpoint_results

    async def _run_on_endpoint(
        self,
        test_func: Callable,
        test_name: str,
        endpoint_name: str,
        config: Dict[str, Any],
        *args,
        **kwargs,
    ) -> TestResult:
        """
        Run test on a specific endpoint.
        """
        start_time = time.time()
        try:
            result = await test_func(*args, endpoint_config=config, **kwargs)
            duration = time.time() - start_time

            return TestResult(
                test_name=test_name,
                endpoint=endpoint_name,
                success=True,
                duration=duration,
                timestamp=time.time(),
                details={"result": result},
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                endpoint=endpoint_name,
                success=False,
                duration=duration,
                timestamp=time.time(),
                details={"error": str(e)},
            )

    def get_results(self, endpoint: Optional[str] = None) -> List[TestResult]:
        """
        Get test results for an endpoint or all endpoints.
        """
        if endpoint:
            return self.results.get(endpoint, [])
        all_results = []
        for results in self.results.values():
            all_results.extend(results)
        return all_results

    def get_success_rate(self, endpoint: str) -> float:
        """
        Get success rate for an endpoint.
        """
        results = self.results.get(endpoint, [])
        if not results:
            return 0.0
        successful = sum(1 for r in results if r.success)
        return successful / len(results)
