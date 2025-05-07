"""
Real-world testing scenarios for the ratchet system.
"""

import os
import re
import subprocess
from pathlib import Path
from unittest.mock import patch

from coderatchet.core.config import get_ratchet_tests
from coderatchet.core.ratchet import (
    FullFileRatchetTest,
    RegexBasedRatchetTest,
    TwoPassRatchetTest,
)
from coderatchet.core.recent_failures import get_recently_broken_ratchets
from coderatchet.core.utils import get_ratchet_test_files


def test_real_world_git_scenarios(tmp_path):
    """Test real-world git scenarios with multiple commits and file changes."""
    # Save current directory
    original_dir = Path.cwd()
    try:
        # Change to temp directory
        os.chdir(tmp_path)

        # Initialize git repository
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text(
            """# Initial version
def hello():
    print("Hello World")
"""
        )

        # Add and commit initial files
        subprocess.run(["git", "add", "src"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        # Create a ratchet test for print statements
        test = RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            match_examples=("print('Hello')",),
            non_match_examples=("logging.info('Hello')",),
        )

        # Mock the ratchet tests function
        with patch(
            "coderatchet.core.recent_failures.get_ratchet_tests", return_value={test}
        ):
            # Test 1: Initial state - should have one violation
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1
            assert failures[0].line_contents == '    print("Hello World")'
            assert failures[0].commit_hash is not None

            # Test 2: Add more print statements in a new commit
            test_file.write_text(
                """# Updated version
def hello():
    print("Modified Hello World")  # Modified line to get new commit hash
    print("Another print")
    print("Yet another print")
"""
            )
            subprocess.run(["git", "add", "src"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "Add more print statements"], check=True
            )

            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 3
            assert all("print" in f.line_contents for f in failures)
            assert len({f.commit_hash for f in failures}) == 1  # All from same commit

            # Test 3: Fix some violations in a new commit
            test_file.write_text(
                """# Fixed version
def hello():
    logging.info("Hello World")  # Fixed
    print("Another print")  # Still broken
    logging.info("Yet another message")  # Fixed
"""
            )
            subprocess.run(["git", "add", "src"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "Fix some print statements"], check=True
            )

            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1
            assert (
                failures[0].line_contents
                == '    print("Another print")  # Still broken'
            )

            # Test 4: Add a new file with violations
            new_file = src_dir / "new_file.py"
            new_file.write_text(
                """# New file with violations
def new_func():
    print("New violation")
    print("Another violation")
"""
            )
            subprocess.run(["git", "add", "src"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "Add new file with violations"], check=True
            )

            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 3  # One from old file, two from new file
            assert len({f.filepath for f in failures}) == 2  # From two different files

            # Test 5: Rename a file with violations
            new_name = src_dir / "renamed.py"
            test_file.rename(new_name)
            subprocess.run(["git", "add", "src"], check=True)
            subprocess.run(["git", "commit", "-m", "Rename file"], check=True)

            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 3  # Same violations, different file path
            assert any(str(new_name) in f.filepath for f in failures)

            # Test 6: Delete a file with violations
            new_file.unlink()
            subprocess.run(["git", "add", "src"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "Delete file with violations"], check=True
            )

            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1  # Only the violation in renamed.py remains

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_real_world_complex_patterns(tmp_path):
    """Test complex regex patterns in real-world scenarios."""
    # Save current directory
    original_dir = Path.cwd()
    try:
        # Change to temp directory
        os.chdir(tmp_path)

        # Initialize git repository
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create test files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"

        # Write test content with paths
        test_file.write_text(
            """
# Test file with paths
unix_path = "/path/to/file"
windows_path = "C:\\Windows\\System32"
safe_path = os.path.join("path", "to", "file")
"""
        )

        # Create complex ratchet tests
        tests = [
            TwoPassRatchetTest(
                name="no_direct_dict_access",
                first_pass=RegexBasedRatchetTest(
                    name="no_direct_dict_access_first",
                    pattern=r"\[['\"].*?['\"]]",
                    match_examples=["data['key']", "config['setting']"],
                    non_match_examples=["data.get('key')"],
                ),
                second_pass_pattern=r"=\s*['\"].*?['\"]",  # Match string assignments
                match_examples=["data['key'] = 'value'", "config['setting'] = '123'"],
                non_match_examples=["data['key'] = None", "config['setting'] = 123"],
            ),
            FullFileRatchetTest(
                name="no_raw_sql",
                pattern=r"""(?xms)
                    ^\s*(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)  # SQL command at start of line
                    [\s\S]*?                                          # Any characters including newlines (non-greedy)
                    (?:FROM|WHERE|SET|VALUES|JOIN)                    # SQL clauses
                """,
                match_examples=[
                    "SELECT * FROM users",
                    "SELECT u.name, p.title\nFROM users u\nJOIN posts p ON u.id = p.user_id",
                ],
                non_match_examples=[
                    "db.query('SELECT * FROM users')",  # SQL in string literal
                    "cursor.execute('SELECT * FROM users')",  # SQL in string literal
                    "sql = 'SELECT * FROM users'",  # SQL in string literal
                ],
                regex_flags=re.VERBOSE | re.MULTILINE | re.DOTALL,
            ),
            RegexBasedRatchetTest(
                name="no_hardcoded_paths",
                pattern=r"""(?x)
                    \s*                # Optional whitespace at start of line
                    (?:unix|windows)_path\s*=\s*  # Variable assignment
                    ["\']              # Opening quote
                    (?:                # Non-capturing group for path start
                        /             # Unix-style path
                        |             # OR
                        [A-Z]:\\     # Windows drive letter and backslash
                    )
                    [a-zA-Z0-9_/\\.-]+  # Path characters including slashes and backslashes
                    ["\']              # Closing quote
                """,
                match_examples=(
                    '    unix_path = "/path/to/file"',
                    '    windows_path = "C:\\Windows\\System32"',
                ),
                non_match_examples=(
                    '    safe_path = os.path.join("path", "to", "file")',
                ),
            ),
        ]

        # Add test files to git
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add test files"], check=True)

        # Run tests
        for test in tests:
            test.collect_failures_from_file(test_file)
            if test.name == "no_direct_dict_access":
                assert len(test.failures) == 0  # No direct dict access violations
            elif test.name == "no_raw_sql":
                assert len(test.failures) == 0  # No raw SQL violations
            elif test.name == "no_hardcoded_paths":
                assert len(test.failures) == 2  # Should find both hardcoded paths
                # Verify the specific paths were found
                failure_contents = {f.line_contents.strip() for f in test.failures}
                assert 'unix_path = "/path/to/file"' in failure_contents
                assert 'windows_path = "C:\\Windows\\System32"' in failure_contents

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_real_world_performance(tmp_path):
    """Test performance with large files and many violations."""
    # Save current directory
    original_dir = Path.cwd()
    try:
        # Change to temp directory
        os.chdir(tmp_path)

        # Initialize git repository
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create test files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create a large file with many violations
        large_file = src_dir / "large.py"
        content = []
        for i in range(1000):  # 1000 lines
            if i % 10 == 0:  # Every 10th line has a violation
                content.append(f'    print("Violation {i}")')
            else:
                content.append(f"    # Line {i}")
        large_file.write_text("\n".join(content))

        # Create a ratchet test
        test = RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            match_examples=("print('Hello')",),
            non_match_examples=("logging.info('Hello')",),
            allowed_count=0,  # No print statements allowed
        )

        # Mock the ratchet tests function
        def mock_get_ratchet_tests(return_set=False):
            tests = [test]
            return set(tests) if return_set else tests

        with patch(
            "coderatchet.core.recent_failures.get_ratchet_tests",
            side_effect=mock_get_ratchet_tests,
        ):
            # Add and commit the large file
            subprocess.run(["git", "add", "src"], check=True)
            subprocess.run(["git", "commit", "-m", "Add large file"], check=True)

            # Print files found by get_ratchet_test_files
            files = get_ratchet_test_files(additional_dirs=[src_dir])
            print(f"Files found: {files}")

            # Test performance with limit
            failures = get_recently_broken_ratchets(
                limit=100,
                include_commits=True,
                additional_dirs=[src_dir],
            )
            assert len(failures) == 100  # Should respect the limit
            assert all("print" in f.line_contents for f in failures)

            # Test performance without limit
            failures = get_recently_broken_ratchets(
                limit=None,
                include_commits=True,
                additional_dirs=[src_dir],
            )
            assert len(failures) == 100  # Should find all violations
            assert all("print" in f.line_contents for f in failures)

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_complex_git_repository_scenarios(tmp_path):
    """Test with a complex git repository structure and history."""
    # Save current directory
    original_dir = Path.cwd()
    try:
        # Change to temp directory
        os.chdir(tmp_path)

        # Initialize git repository
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create a complex project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create initial files
        main_file = src_dir / "main.py"
        main_file.write_text(
            """# Initial version
def main():
    print("Hello World")
    return 0
"""
        )

        test_file = tests_dir / "test_main.py"
        test_file.write_text(
            """# Test file
def test_main():
    assert main() == 0
"""
        )

        # Initial commit
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        # Create a feature branch
        subprocess.run(["git", "checkout", "-b", "feature/new-feature"], check=True)

        # Add new feature with violations
        feature_file = src_dir / "feature.py"
        feature_file.write_text(
            """# New feature
def new_feature():
    print("Feature code")
    data = {"key": "value"}
    return data["key"]  # Direct dict access
"""
        )

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add new feature"], check=True)

        # Create another branch with fixes
        subprocess.run(["git", "checkout", "-b", "feature/fixes"], check=True)

        # Fix some violations
        feature_file.write_text(
            """# Fixed feature
def new_feature():
    logging.info("Feature code")  # Fixed print
    data = {"key": "value"}
    return data.get("key")  # Fixed dict access
"""
        )

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Fix violations"], check=True)

        # Merge back to main
        subprocess.run(["git", "checkout", "main"], check=True)
        subprocess.run(
            ["git", "merge", "feature/fixes", "--no-ff", "-m", "Merge fixes"],
            check=True,
        )

        # Create a ratchet test
        test = RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            match_examples=["print('Hello')"],
            non_match_examples=["logging.info('Hello')"],
        )

        # Mock the ratchet tests function
        with patch("coderatchet.core.config.get_ratchet_tests", return_value=[test]):
            # Test 1: Check main branch
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1  # Only the print in main.py

            # Test 2: Check feature branch
            subprocess.run(["git", "checkout", "feature/new-feature"], check=True)
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 2  # print in main.py and feature.py

            # Test 3: Check fixes branch
            subprocess.run(["git", "checkout", "feature/fixes"], check=True)
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1  # Only the print in main.py

            # Test 4: Check after merge
            subprocess.run(["git", "checkout", "main"], check=True)
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1  # Only the print in main.py

    finally:
        # Restore original directory
        os.chdir(original_dir)
