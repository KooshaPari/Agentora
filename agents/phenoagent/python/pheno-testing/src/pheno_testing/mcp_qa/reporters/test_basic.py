"""Basic smoke test for reporter library.

Run this to verify all reporters can be imported and work with sample data.
"""

import sys
from pathlib import Path

# Sample test data
SAMPLE_RESULTS = [
    {
        "test_name": "test_workspace_list",
        "tool_name": "workspace_tool",
        "success": True,
        "duration_ms": 125.5,
        "cached": False,
    },
    {
        "test_name": "test_workspace_create",
        "tool_name": "workspace_tool",
        "success": True,
        "duration_ms": 250.0,
        "cached": False,
    },
    {
        "test_name": "test_entity_list",
        "tool_name": "entity_tool",
        "success": False,
        "duration_ms": 100.0,
        "error": "Connection refused",
        "request_params": {"entity_type": "organizations"},
        "response": None,
    },
    {
        "test_name": "test_entity_cached",
        "tool_name": "entity_tool",
        "success": True,
        "duration_ms": 5.0,
        "cached": True,
    },
    {
        "test_name": "test_query_search",
        "tool_name": "query_tool",
        "success": True,
        "duration_ms": 175.0,
        "skipped": False,
    },
    {
        "test_name": "test_query_aggregate",
        "tool_name": "query_tool",
        "success": False,
        "duration_ms": 50.0,
        "skipped": True,
        "skip_reason": "Not implemented yet",
    },
]

SAMPLE_METADATA = {
    "endpoint": "http://localhost:8000",
    "auth_status": "authenticated",
    "duration_seconds": 2.5,
}


def test_imports():
    """
    Test that all reporters can be imported.
    """
    print("Testing imports...")
    try:
        from pheno.testing.mcp_qa.reporters import (
            ConsoleReporter,
            DetailedErrorReporter,
            FunctionalityMatrixReporter,
            JSONReporter,
            MarkdownReporter,
            MultiReporter,
            TestReporter,
            create_standard_reporters,
        )

        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_console_reporter():
    """
    Test ConsoleReporter.
    """
    print("\nTesting ConsoleReporter...")
    try:
        from pheno.testing.mcp_qa.reporters import ConsoleReporter

        reporter = ConsoleReporter(title="Test Report", use_rich=False)
        reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)
        print("✓ ConsoleReporter works")
        return True
    except Exception as e:
        print(f"✗ ConsoleReporter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_json_reporter():
    """
    Test JSONReporter.
    """
    print("\nTesting JSONReporter...")
    try:
        import tempfile

        from pheno.testing.mcp_qa.reporters import JSONReporter

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        reporter = JSONReporter(output_path)
        reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)

        # Verify file was created
        path = Path(output_path)
        if path.exists():
            print(f"✓ JSONReporter created file: {output_path}")
            # Clean up
            path.unlink()
            return True
        else:
            print("✗ JSONReporter did not create file")
            return False
    except Exception as e:
        print(f"✗ JSONReporter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_markdown_reporter():
    """
    Test MarkdownReporter.
    """
    print("\nTesting MarkdownReporter...")
    try:
        import tempfile

        from pheno.testing.mcp_qa.reporters import MarkdownReporter

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            output_path = f.name

        reporter = MarkdownReporter(output_path)
        reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)

        # Verify file was created
        path = Path(output_path)
        if path.exists():
            print(f"✓ MarkdownReporter created file: {output_path}")
            # Clean up
            path.unlink()
            return True
        else:
            print("✗ MarkdownReporter did not create file")
            return False
    except Exception as e:
        print(f"✗ MarkdownReporter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_matrix_reporter():
    """
    Test FunctionalityMatrixReporter.
    """
    print("\nTesting FunctionalityMatrixReporter...")
    try:
        import tempfile

        from pheno.testing.mcp_qa.reporters import FunctionalityMatrixReporter

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            output_path = f.name

        reporter = FunctionalityMatrixReporter(output_path)
        reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)

        # Verify file was created
        path = Path(output_path)
        if path.exists():
            print(f"✓ FunctionalityMatrixReporter created file: {output_path}")
            # Clean up
            path.unlink()
            return True
        else:
            print("✗ FunctionalityMatrixReporter did not create file")
            return False
    except Exception as e:
        print(f"✗ FunctionalityMatrixReporter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_error_reporter():
    """
    Test DetailedErrorReporter.
    """
    print("\nTesting DetailedErrorReporter...")
    try:
        from pheno.testing.mcp_qa.reporters import DetailedErrorReporter

        reporter = DetailedErrorReporter(verbose=True, use_rich=False)
        reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)
        print("✓ DetailedErrorReporter works")
        return True
    except Exception as e:
        print(f"✗ DetailedErrorReporter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_multi_reporter():
    """
    Test MultiReporter.
    """
    print("\nTesting MultiReporter...")
    try:
        from pheno.testing.mcp_qa.reporters import ConsoleReporter, MultiReporter

        # Use console reporter only to avoid file creation
        reporter = MultiReporter([ConsoleReporter(use_rich=False)])
        reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)
        print("✓ MultiReporter works")
        return True
    except Exception as e:
        print(f"✗ MultiReporter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_standard_reporters():
    """
    Test create_standard_reporters().
    """
    print("\nTesting create_standard_reporters()...")
    try:
        import shutil
        import tempfile

        from pheno.testing.mcp_qa.reporters import create_standard_reporters

        # Create temp directory
        temp_dir = tempfile.mkdtemp()

        try:
            reporters = create_standard_reporters(
                output_dir=temp_dir, console_title="Test Suite", verbose_errors=False
            )

            # Should have 5 reporters
            if len(reporters) == 5:
                print(f"✓ Created {len(reporters)} reporters")
                # Run them
                for reporter in reporters:
                    reporter.report(SAMPLE_RESULTS, SAMPLE_METADATA)
                print("✓ All standard reporters executed successfully")
                return True
            else:
                print(f"✗ Expected 5 reporters, got {len(reporters)}")
                return False
        finally:
            # Clean up
            shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"✗ create_standard_reporters failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """
    Run all tests.
    """
    print("=" * 80)
    print("MCP QA Reporters - Basic Smoke Test")
    print("=" * 80)

    tests = [
        test_imports,
        test_console_reporter,
        test_json_reporter,
        test_markdown_reporter,
        test_matrix_reporter,
        test_error_reporter,
        test_multi_reporter,
        test_standard_reporters,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
