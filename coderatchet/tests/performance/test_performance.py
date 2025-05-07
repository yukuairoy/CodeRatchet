"""
Performance tests for CodeRatchet.
"""

import time

import psutil

from coderatchet.core.ratchet import (
    FullFileRatchetTest,
    RegexBasedRatchetTest,
    TwoLineRatchetTest,
)


def test_large_file_performance(tmp_path):
    """Test performance with large files."""
    # Create a large file with many lines
    test_file = tmp_path / "large.py"
    with open(test_file, "w") as f:
        for i in range(100000):  # 100K lines
            f.write(f"print('Line {i}')\n")

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Measure time and memory
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss

    test.collect_failures_from_file(test_file)

    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss

    # Should complete within 5 seconds
    assert end_time - start_time < 5.0

    # Memory usage should be reasonable (less than 100MB)
    memory_used = end_memory - start_memory
    assert memory_used < 100 * 1024 * 1024  # 100MB in bytes


def test_complex_regex_performance(tmp_path):
    """Test performance with complex regex patterns."""
    test_file = tmp_path / "complex.py"
    test_file.write_text(
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

    # Complex regex pattern
    test = RegexBasedRatchetTest(
        name="test",
        pattern=r"self\.(?:_[a-zA-Z_]+|[a-zA-Z_]+)\s*=\s*[^;]+",  # Must have assignment
        match_examples=["self._private = 'secret'", "self.value = 42"],
        non_match_examples=["self.method()", "self.prop"],
    )

    # Measure time
    start_time = time.time()

    test.collect_failures_from_file(test_file)

    end_time = time.time()

    # Should complete within 0.1 seconds
    assert end_time - start_time < 0.1


def test_multiple_files_performance(tmp_path):
    """Test performance with multiple files."""
    # Create multiple files
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    for i in range(100):  # 100 files
        file_path = src_dir / f"file_{i}.py"
        with open(file_path, "w") as f:
            for j in range(100):  # 100 lines per file
                f.write(f"print('File {i}, Line {j}')\n")

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Measure time and memory
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss

    for file_path in src_dir.glob("*.py"):
        test.collect_failures_from_file(file_path)

    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss

    # Should complete within 10 seconds
    assert end_time - start_time < 10.0

    # Memory usage should be reasonable (less than 200MB)
    memory_used = end_memory - start_memory
    assert memory_used < 200 * 1024 * 1024  # 200MB in bytes


def test_pattern_compilation_performance():
    """Test performance of regex pattern compilation."""
    # Create a test with many patterns
    patterns = [f"pattern{i}" for i in range(1000)]

    start_time = time.time()

    RegexBasedRatchetTest(
        name="test",
        pattern="|".join(patterns),
        match_examples=["pattern0"],
        non_match_examples=["not_a_pattern"],
    )

    end_time = time.time()

    # Pattern compilation should complete within 0.5 seconds
    assert end_time - start_time < 0.5


def test_two_line_ratchet_performance(tmp_path):
    """Test performance of two-line ratchet tests."""
    # Create a large file with many lines
    test_file = tmp_path / "large.py"
    with open(test_file, "w") as f:
        for i in range(100000):  # 100K lines
            f.write(f"print('Line {i}')\n")
            f.write(f"logging.info('Line {i}')\n")

    test = TwoLineRatchetTest(
        name="test",
        pattern="print\\(",
        last_line_pattern="logging\\.info\\(",
        match_examples=["print('Hello')", "logging.info('Hello')"],
        non_match_examples=["print('Hello')", "print('World')"],
    )

    # Measure time
    start_time = time.time()

    test.collect_failures_from_file(test_file)

    end_time = time.time()

    # Should complete within 5 seconds
    assert end_time - start_time < 5.0


def test_full_file_ratchet_performance(tmp_path):
    """Test performance of full file ratchet tests."""
    # Create a large file
    test_file = tmp_path / "large.py"
    content = "print('Hello')\n" * 100000  # 100K lines

    with open(test_file, "w") as f:
        f.write(content)

    test = FullFileRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Measure time
    start_time = time.time()

    test.collect_failures_from_file(test_file)

    end_time = time.time()

    # Should complete within 5 seconds
    assert end_time - start_time < 5.0
