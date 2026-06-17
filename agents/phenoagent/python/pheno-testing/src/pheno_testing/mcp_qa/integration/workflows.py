"""
Workflow testing utilities.
"""

from typing import Any, Dict, List


class WorkflowTester:
    """
    Test multi-step workflows.
    """

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    async def execute_workflow(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a multi-step workflow and return results.
        """
        results = []
        for step in steps:
            tool = step["tool"]
            args = step.get("args", {})
            result = await self.mcp_client.call_tool(tool, args)
            results.append(result)
        return {"steps": results, "success": all(r.get("success") for r in results)}
