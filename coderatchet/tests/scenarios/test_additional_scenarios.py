"""
Additional scenario tests for the coderatchet system.
"""

from coderatchet.core.ratchet import (
    FullFileRatchetTest,
    RegexBasedRatchetTest,
    TwoLineRatchetTest,
    TwoPassRatchetTest,
)


def test_large_codebase_scenario(tmp_path):
    """Test ratchet performance with a large codebase."""
    # Create a large number of files
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create 100 Python files with various patterns
    for i in range(100):
        file_path = src_dir / f"module_{i}.py"
        content = f"""
def function_{i}():
    print('Hello {i}')  # Some print statements
    return True
"""
        file_path.write_text(content)

    # Create a ratchet test for print statements
    test = RegexBasedRatchetTest(
        name="no_print",
        pattern="print\\(",
        description="No print statements allowed",
    )

    # Test performance of collecting failures
    files = list(src_dir.glob("*.py"))
    test.clear_failures()
    for file in files:
        test.collect_failures_from_file(file)

    assert len(test.failures) == 100  # One print statement per file


def test_complex_pattern_scenario(tmp_path):
    """Test complex regex patterns in ratchets."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create files with complex patterns
    (src_dir / "complex.py").write_text(
        """
class ComplexClass:
    def __init__(self):
        self.value = 42
        self._private = "secret"
    
    def method(self):
        return self.value + 1
    
    @property
    def prop(self):
        return self._private
"""
    )

    # Create complex pattern tests
    class_test = RegexBasedRatchetTest(
        name="no_private_attributes",
        pattern="self\\._[a-zA-Z_]+",
        description="No private attributes",
        match_examples=["self._private"],
        non_match_examples=["self.value"],
    )

    property_test = TwoLineRatchetTest(
        name="no_property_private",
        pattern="@property",
        description="No properties accessing private attributes",
        match_examples=["@property", "return self._private"],
        non_match_examples=["@property", "return self.value"],
    )

    # Test complex pattern detection
    files = list(src_dir.glob("*.py"))
    violations = []

    for test in [class_test, property_test]:
        test.clear_failures()
        for file in files:
            test.collect_failures_from_file(file)
        violations.extend(test.failures)

    assert len(violations) == 3  # Should find three violations:
    # 1. self._private in __init__
    # 2. self._private in prop
    # 3. @property in prop


def test_multiple_ratchet_types_scenario(tmp_path):
    """Test interaction between different types of ratchets."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "mixed.py").write_text(
        """
import os
from pathlib import Path

def process_file(filepath):
    with open(filepath) as f:
        content = f.read()
    print(content)  # Print file content
    return content

def main():
    path = "../../etc/passwd"  # Path traversal
    content = process_file(path)
    print(content)  # Print sensitive data
"""
    )

    # Create various types of ratchets
    path_traversal = RegexBasedRatchetTest(
        name="no_path_traversal",
        pattern="\\.\\./",
        description="No path traversal",
    )

    print_sensitive = RegexBasedRatchetTest(
        name="no_print_sensitive",
        pattern="print\\(content\\)",
        description="No printing potentially sensitive data",
    )

    file_operations = FullFileRatchetTest(
        name="no_dangerous_operations",
        pattern="open\\([^)]+\\)",
        description="No dangerous file operations",
    )

    # Test multiple ratchet types
    files = list(src_dir.glob("*.py"))
    violations = []

    for test in [path_traversal, print_sensitive, file_operations]:
        test.clear_failures()
        for file in files:
            test.collect_failures_from_file(file)
        violations.extend(test.failures)

    assert len(violations) == 4  # Should find all violations:
    # 1. Path traversal: "../../etc/passwd"
    # 2. Print sensitive data: first print(content)
    # 3. Print sensitive data: second print(content)
    # 4. Dangerous file operation: open(filepath)


def test_two_pass_ratchet_scenario(tmp_path):
    """Test complex two-pass ratchet scenarios."""
    # Create test files
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create a file with classes that reference themselves
    test_file = src_dir / "classes.py"
    test_file.write_text(
        """class FirstClass:
    def method(self):
        self.FirstClass.method()  # Self reference

class SecondClass:
    def method(self):
        self.SecondClass.method()  # Self reference

class ThirdClass:
    def method(self):
        self.ThirdClass.method()  # Self reference
"""
    )

    # Create a first pass test to find class names
    first_pass = RegexBasedRatchetTest(
        name="class_finder",
        pattern=r"class\s+(\w+)",
        match_examples=["class MyClass:"],
        non_match_examples=["def my_function():"],
        description="Find class names",
    )

    # Create a two-pass test to check for self-references
    def to_second_pass(failure):
        class_name = failure.line_contents.split()[1].rstrip(":")
        return f"self\\.{class_name}\\.method\\(\\)"

    test = TwoPassRatchetTest(
        name="no_self_reference",
        first_pass=first_pass,
        second_pass_pattern=r"self\.\w+\.method\(\)",
        first_pass_failure_to_second_pass_regex_part=to_second_pass,
        first_pass_failure_filepath_for_testing="classes.py",
        match_examples=["self.MyClass.method()"],  # Only second pass examples
        non_match_examples=["other.MyClass.method()"],  # Only second pass non-examples
    )

    # Collect failures
    test.collect_failures_from_file(test_file)
    assert len(test.failures) == 3  # Should find 3 self-references
