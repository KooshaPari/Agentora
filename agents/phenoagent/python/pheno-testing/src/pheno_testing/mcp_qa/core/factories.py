"""Test Factories for Creating Test Instances.

Provides factories for:
- Individual test creation from parameter specs
- Test suite assembly
- Parameter permutation generation
- Data generation for test cases
"""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .patterns import IntegrationPattern, ToolTestPattern, UserStoryPattern

if TYPE_CHECKING:
    pass


class TestFactory:
    """
    Factory for creating individual tests from specifications.
    """

    @staticmethod
    def create_tool_test(
        tool_name: str,
        test_name: str,
        params: Dict[str, Any],
        expected_fields: Optional[List[str]] = None,
    ) -> Callable:
        """Create a tool test function from specification.

        Args:
            tool_name: MCP tool name
            test_name: Test function name
            params: Tool parameters to test
            expected_fields: Expected fields in response (for validation)

        Returns:
            Async test function

        Example:
            test = TestFactory.create_tool_test(
                tool_name="entity_tool",
                test_name="test_list_organizations",
                params={"entity_type": "organization", "operation": "list"},
                expected_fields=["organizations", "total"]
            )
        """
        pattern = ToolTestPattern(tool_name, expected_fields or [])

        async def test_func(client_adapter):
            return await pattern.execute(client_adapter, params)

        test_func.__name__ = test_name
        test_func.__doc__ = f"Test {tool_name} with params: {params}"

        return test_func

    @staticmethod
    def create_user_story_test(
        story_name: str,
        steps: List[Dict[str, Any]],
    ) -> Callable:
        """Create a user story test function.

        Args:
            story_name: User story name
            steps: List of workflow steps

        Returns:
            Async test function

        Example:
            test = TestFactory.create_user_story_test(
                story_name="Create Organization and Project",
                steps=[
                    {
                        "tool": "entity_tool",
                        "params": {"entity_type": "organization", "operation": "create", "data": {...}},
                        "description": "Create organization",
                        "save_to_context": "org_id",
                        "validation": lambda r, ctx: "id" in r.get("response", {})
                    },
                    {
                        "tool": "entity_tool",
                        "params": {"entity_type": "project", "operation": "create", "data": {"organization_id": "$context.org_id", ...}},
                        "description": "Create project",
                        "validation": lambda r, ctx: r.get("success")
                    }
                ]
            )
        """
        pattern = UserStoryPattern(story_name, steps)

        async def test_func(client_adapter):
            return await pattern.execute(client_adapter)

        test_func.__name__ = f"test_story_{story_name.lower().replace(' ', '_')}"
        test_func.__doc__ = f"User story: {story_name}"

        return test_func

    @staticmethod
    def create_integration_test(
        test_name: str,
        tools: List[str],
        workflow: Callable,
    ) -> Callable:
        """Create an integration test function.

        Args:
            test_name: Test name
            tools: List of tools used in integration
            workflow: Async workflow function(client_adapter) -> Dict

        Returns:
            Async test function
        """
        pattern = IntegrationPattern(tools, workflow)

        async def test_func(client_adapter):
            return await pattern.execute(client_adapter)

        test_func.__name__ = test_name
        test_func.__doc__ = f"Integration test: {', '.join(tools)}"

        return test_func


class ParameterPermutationFactory:
    """
    Factory for generating parameter permutations.
    """

    @staticmethod
    def generate_permutations(
        base_params: Dict[str, Any], variations: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Generate all permutations of parameter variations.

        Args:
            base_params: Base parameters always included
            variations: Dict of parameter -> [value1, value2, ...]

        Returns:
            List of parameter dictionaries

        Example:
            permutations = ParameterPermutationFactory.generate_permutations(
                base_params={"operation": "list"},
                variations={
                    "limit": [10, 50, 100],
                    "offset": [0, 10]
                }
            )
            # Returns: [
            #   {"operation": "list", "limit": 10, "offset": 0},
            #   {"operation": "list", "limit": 10, "offset": 10},
            #   {"operation": "list", "limit": 50, "offset": 0},
            #   ...
            # ]
        """
        if not variations:
            return [base_params.copy()]

        result = [base_params.copy()]

        for param_name, values in variations.items():
            new_result = []
            for existing_params in result:
                for value in values:
                    new_params = existing_params.copy()
                    new_params[param_name] = value
                    new_result.append(new_params)
            result = new_result

        return result

    @staticmethod
    def generate_operation_variations(
        tool_name: str,
        operation: str,
        base_params: Dict[str, Any],
        param_matrix: Dict[str, List[Any]],
    ) -> List[Callable]:
        """Generate test functions for all parameter variations of an operation.

        Args:
            tool_name: Tool name
            operation: Operation name
            base_params: Base params for operation
            param_matrix: Parameter variations

        Returns:
            List of test functions

        Example:
            tests = ParameterPermutationFactory.generate_operation_variations(
                tool_name="entity_tool",
                operation="list",
                base_params={"entity_type": "organization", "operation": "list"},
                param_matrix={"limit": [10, 50], "format_type": ["detailed", "summary"]}
            )
            # Generates 4 tests (2 × 2 combinations)
        """
        permutations = ParameterPermutationFactory.generate_permutations(base_params, param_matrix)

        tests = []
        for i, params in enumerate(permutations):
            # Generate descriptive test name
            variation_desc = "_".join(
                [f"{k}_{v}" for k, v in params.items() if k not in base_params]
            )
            test_name = f"test_{operation}_{variation_desc or 'basic'}_{i}"

            test = TestFactory.create_tool_test(
                tool_name=tool_name, test_name=test_name, params=params, expected_fields=[]
            )

            tests.append(test)

        return tests


class TestSuiteFactory:
    """
    Factory for assembling complete test suites.
    """

    @staticmethod
    def create_crud_suite(tool_name: str, entity_types: List[str]) -> List[Callable]:
        """Create CRUD test suite for multiple entity types.

        Args:
            tool_name: Tool name (e.g., "entity_tool")
            entity_types: List of entity types to test

        Returns:
            List of test functions (list + read for each entity type)
        """
        tests = []

        for entity_type in entity_types:
            # List operation
            list_test = TestFactory.create_tool_test(
                tool_name=tool_name,
                test_name=f"test_list_{entity_type}",
                params={"entity_type": entity_type, "operation": "list"},
                expected_fields=["data", "total"],
            )
            tests.append(list_test)

        return tests

    @staticmethod
    def create_search_suite(
        tool_name: str, entity_types: List[str], search_terms: List[str]
    ) -> List[Callable]:
        """Create search test suite for multiple entities and search terms.

        Args:
            tool_name: Tool name (e.g., "query_tool")
            entity_types: Entity types to search
            search_terms: Search terms to test

        Returns:
            List of test functions
        """
        tests = []

        for search_term in search_terms:
            for entity_type in entity_types:
                test = TestFactory.create_tool_test(
                    tool_name=tool_name,
                    test_name=f"test_search_{entity_type}_{search_term.replace(' ', '_')}",
                    params={
                        "query_type": "search",
                        "entities": [entity_type],
                        "search_term": search_term,
                    },
                    expected_fields=["results"],
                )
                tests.append(test)

        return tests

    @staticmethod
    def create_rag_suite(
        tool_name: str, entity_types: List[str], rag_modes: List[str], queries: List[str]
    ) -> List[Callable]:
        """Create RAG search test suite for all mode × entity × query combinations.

        Args:
            tool_name: Tool name (e.g., "query_tool")
            entity_types: Entity types to search
            rag_modes: RAG modes to test
            queries: Search queries to test

        Returns:
            List of test functions
        """
        tests = []

        for mode in rag_modes:
            for entity_type in entity_types:
                for query in queries[:2]:  # Limit to 2 queries per combination
                    test = TestFactory.create_tool_test(
                        tool_name=tool_name,
                        test_name=f"test_rag_{mode}_{entity_type}_{hash(query) % 1000}",
                        params={
                            "query_type": "rag_search",
                            "entities": [entity_type],
                            "search_term": query,
                            "rag_mode": mode,
                        },
                        expected_fields=["results", "mode"],
                    )
                    tests.append(test)

        return tests
