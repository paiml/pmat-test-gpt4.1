
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import pfind


def make_tree(base):
    os.makedirs(os.path.join(base, "dir1"), exist_ok=True)
    with open(os.path.join(base, "file1.txt"), "w") as f:
        f.write("hello")
    with open(os.path.join(base, "dir1", "file2.log"), "w") as f:
        f.write("world")


def test_traverse_files_and_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        make_tree(tmp)
        results = list(pfind.traverse(tmp))
        assert any("file1.txt" in p for p in results)
        assert any("file2.log" in p for p in results)
        assert any("dir1" in p for p in results)


def test_traverse_name_filter():
    with tempfile.TemporaryDirectory() as tmp:
        make_tree(tmp)
        results = list(pfind.traverse(tmp, name="*.log"))
        assert all(p.endswith(".log") for p in results)


def test_traverse_type_file():
    with tempfile.TemporaryDirectory() as tmp:
        make_tree(tmp)
        results = list(pfind.traverse(tmp, type_="f"))
        assert all(os.path.isfile(p) for p in results)


def test_traverse_type_dir():
    with tempfile.TemporaryDirectory() as tmp:
        make_tree(tmp)
        results = list(pfind.traverse(tmp, type_="d"))
        assert all(os.path.isdir(p) for p in results)


def test_traverse_size_filter():
    with tempfile.TemporaryDirectory() as tmp:
        make_tree(tmp)
        # file1.txt is 5 bytes, file2.log is 5 bytes
        results = [p for p in pfind.traverse(tmp, size="+1") if os.path.isfile(p)]
        assert len(results) > 0
        results = [p for p in pfind.traverse(tmp, size="+100") if os.path.isfile(p)]
        assert len(results) == 0
