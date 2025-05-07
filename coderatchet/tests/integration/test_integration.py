"""
Integration tests for the coderatchet package.
"""

import subprocess
from unittest.mock import patch

from coderatchet.core.config import get_ratchet_tests
from coderatchet.core.ratchet import RegexBasedRatchetTest, TwoLineRatchetTest
from coderatchet.core.recent_failures import get_recently_broken_ratchets
from coderatchet.core.utils import get_ratchet_test_files, write_ratchet_counts


def test_end_to_end_ratchet_workflow(tmp_path):
    """Test the complete ratchet workflow from test creation to failure detection."""
    # Create test file with violations
    test_file = tmp_path / "test.py"
    test_file.write_text(
        """
print('Hello')
print('World')
print('Test')
import os
"""
    )

    # Initialize git repository and commit the file
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Create ratchet tests
    print_test = RegexBasedRatchetTest(
        name="no_print",
        pattern="print\\(",
        description="No print statements allowed",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )

    import_test = RegexBasedRatchetTest(
        name="no_import",
        pattern="^import\\s+",
        description="No direct imports allowed",
        match_examples=("import os",),
        non_match_examples=("from os import path",),
    )

    # Test recent failures detection
    with patch(
        "coderatchet.core.config.get_ratchet_tests",
        return_value={print_test, import_test},
    ), patch(
        "coderatchet.core.recent_failures.get_ratchet_tests",
        return_value={print_test, import_test},
    ), patch(
        "coderatchet.core.recent_failures.get_ratchet_test_files",
        return_value=[test_file],
    ):
        failures = get_recently_broken_ratchets(limit=10, include_commits=False)
        assert len(failures) == 4  # Three print statements and one import

    # Test ratchet count management
    write_ratchet_counts({"no_print": 3})
    # Create a new test instance to pick up the updated allowed_count
    print_test = RegexBasedRatchetTest(
        name="no_print",
        pattern="print\\(",
        description="No print statements allowed",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )
    assert print_test.allowed_count == 3


def test_ratchet_comparison(tmp_path):
    """Test comparing ratchets between different states."""
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)

    # Configure git
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create test file with initial state
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Hello')")

    # Add and commit initial state
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial state"], cwd=tmp_path, check=True)

    # Update test file with current state
    test_file.write_text(
        """
print('Hello')
print('World')
"""
    )

    # Add and commit current state
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Current state"], cwd=tmp_path, check=True)

    # Create ratchet test
    test = RegexBasedRatchetTest(
        name="no_print",
        pattern="print\\(",
        description="No print statements allowed",
    )

    # Test file collection
    files = get_ratchet_test_files([tmp_path])
    assert len(files) == 1  # Should find the test file

    # Test failure detection
    test.clear_failures()
    for file in files:
        test.collect_failures_from_file(file)
    assert len(test.failures) == 2  # Two print statements


def test_security_integration(tmp_path):
    """Test integration of security-related ratchets."""
    # Create test files with potential security issues
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "config.py").write_text(
        """
API_KEY = "sk_test_1234567890abcdef"
DB_URL = "postgres://user:pass@localhost:5432/db"
"""
    )

    (src_dir / "utils.py").write_text(
        """
def run_command(cmd):
    import subprocess
    subprocess.run(cmd, shell=True)  # Potential command injection
"""
    )

    # Create security ratchets
    api_key_test = RegexBasedRatchetTest(
        name="no_api_keys",
        pattern=r'["\']sk_[a-zA-Z0-9_]+["\']',
        description="No API keys in code",
        match_examples=("'sk_test_1234567890abcdef'", '"sk_test_1234567890abcdef"'),
        non_match_examples=("api_key = None", "sk_test_1234567890abcdef"),
    )

    db_url_test = RegexBasedRatchetTest(
        name="no_db_urls",
        pattern=r'["\']postgres://[^"\']+["\']',
        description="No database URLs in code",
        match_examples=("'postgres://user:pass@localhost:5432/db'",),
        non_match_examples=("db_url = None",),
    )

    command_injection_test = RegexBasedRatchetTest(
        name="no_command_injection",
        pattern=r"subprocess\.run\([^)]+shell=True[^)]*\)",
        description="No shell=True in subprocess.run",
        match_examples=("subprocess.run(cmd, shell=True)",),
        non_match_examples=("subprocess.run(cmd)",),
    )

    # Test for security issues
    for test in [api_key_test, db_url_test, command_injection_test]:
        test.clear_failures()
        for file in [src_dir / "config.py", src_dir / "utils.py"]:
            test.collect_failures_from_file(file)

    # Verify failures
    api_key_failures = api_key_test.failures
    assert len(api_key_failures) == 1
    assert "sk_test_1234567890abcdef" in api_key_failures[0].line_contents

    db_url_failures = db_url_test.failures
    assert len(db_url_failures) == 1
    assert "postgres://" in db_url_failures[0].line_contents

    command_failures = command_injection_test.failures
    assert len(command_failures) == 1
    assert "shell=True" in command_failures[0].line_contents


def test_complex_ratchet_scenarios(tmp_path):
    """Test complex ratchet scenarios with multiple test types."""
    # Create a complex test project
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "main.py").write_text(
        """
    import os
    from pathlib import Path

    def process_file(filepath):
        with open(filepath) as f:
            content = f.read()
        return content

    def main():
        content = process_file("../../etc/passwd")  # Potential path traversal
        print(content)  # Print sensitive data
    """
    )

    # Create various ratchet tests
    path_traversal_test = RegexBasedRatchetTest(
        name="no_path_traversal",
        pattern=r"\.\./",
        description="No path traversal patterns",
        match_examples=("../../etc/passwd",),
        non_match_examples=("path/to/file",),
    )

    sensitive_data_test = RegexBasedRatchetTest(
        name="no_sensitive_data",
        pattern=r"passwd",
        description="No sensitive data in files",
        match_examples=("/etc/passwd",),
        non_match_examples=("password = None",),
    )

    print_sensitive_test = TwoLineRatchetTest(
        name="no_print_sensitive",
        pattern=r"passwd",
        last_line_pattern=r"print\(",
        description="No printing of sensitive data",
        match_examples=("content = read_passwd()", "print(content)"),
        non_match_examples=("content = 'safe'", "print(content)"),
    )

    # Test complex scenario detection
    files = get_ratchet_test_files([src_dir])
    violations = []

    for test in [path_traversal_test, sensitive_data_test, print_sensitive_test]:
        test.clear_failures()
        for file in files:
            test.collect_failures_from_file(file)
        violations.extend(test.failures)

    assert len(violations) == 3  # Should find all three violations
