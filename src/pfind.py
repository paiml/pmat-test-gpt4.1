import argparse
import fnmatch
import os
import sys
from typing import Iterator, Optional


def parse_size_expr(expr: str):
    if not expr:
        return None
    import re

    match = re.match(r"([+-]?)(\d+)([kKmMgG]?)", expr)
    if not match:
        raise ValueError(f"Invalid size expression: {expr}")
    sign, num, unit = match.groups()
    num = int(num)
    factor = 1
    if unit.lower() == "k":
        factor = 1024
    elif unit.lower() == "m":
        factor = 1024**2
    elif unit.lower() == "g":
        factor = 1024**3
    return sign, num * factor


def match_size(size: int, expr: Optional[str]) -> bool:
    if not expr:
        return True
    sign, value = parse_size_expr(expr)
    if sign == "+":
        return size > value
    elif sign == "-":
        return size < value
    else:
        return size == value


def traverse(
    root: str,
    name: Optional[str] = None,
    type_: Optional[str] = None,
    size: Optional[str] = None,
) -> Iterator[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        if type_ in (None, "d"):
            for d in dirnames:
                path = os.path.join(dirpath, d)
                if name and not fnmatch.fnmatch(d, name):
                    continue
                # Do not apply size filter to directories (to match find behavior)
                yield path
        if type_ in (None, "f"):
            for f in filenames:
                path = os.path.join(dirpath, f)
                if name and not fnmatch.fnmatch(f, name):
                    continue
                if size and not match_size(os.path.getsize(path), size):
                    continue
                yield path


def main():
    parser = argparse.ArgumentParser(description="Python find-like CLI tool.")
    parser.add_argument("path", nargs="?", default=".", help="Root path to search.")
    parser.add_argument("-n", "--name", help="Filter by filename (supports wildcards)")
    parser.add_argument("-t", "--type", choices=["f", "d"], help="Type: f=file, d=dir")
    parser.add_argument("-s", "--size", help="Filter by size (e.g., +10k, -1M)")
    args = parser.parse_args()
    try:
        for p in traverse(args.path, args.name, args.type, args.size):
            print(p)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
