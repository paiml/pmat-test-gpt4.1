#!/usr/bin/env python3
"""
A minimal Python CLI that mimics the basic functionality of the Unix `find` tool.
Supports a subset of options, tests, and actions, all in a single file, no dependencies.
"""
import os
import sys
import stat
import fnmatch
import argparse
import pwd
import grp
import time
from datetime import datetime, timedelta

VERSION = "pyfind 1.0"

# --- Utility functions ---
def parse_size(size_str):
    """Parse a size string like 10k, 2M, 3G, etc."""
    units = {'b': 1, 'c': 1, 'w': 2, 'k': 1024, 'M': 1024**2, 'G': 1024**3}
    if size_str[-1] in units:
        return int(size_str[:-1]) * units[size_str[-1]]
    return int(size_str)

def match_pattern(name, pattern, case_sensitive=True):
    if not case_sensitive:
        name = name.lower()
        pattern = pattern.lower()
    return fnmatch.fnmatch(name, pattern)

def n_compare(val, nstr):
    """Compare val to nstr, which can be +N, -N, or N."""
    if nstr.startswith('+'):
        return val > int(nstr[1:])
    elif nstr.startswith('-'):
        return val < int(nstr[1:])
    else:
        return val == int(nstr)

# --- Expression evaluation ---
class Expr:
    def __call__(self, path, st):
        return True

class And(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def __call__(self, path, st):
        return self.left(path, st) and self.right(path, st)

class Or(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def __call__(self, path, st):
        return self.left(path, st) or self.right(path, st)

class Not(Expr):
    def __init__(self, expr):
        self.expr = expr
    def __call__(self, path, st):
        return not self.expr(path, st)

class Name(Expr):
    def __init__(self, pattern):
        self.pattern = pattern
    def __call__(self, path, st):
        return match_pattern(os.path.basename(path), self.pattern)

class Iname(Expr):
    def __init__(self, pattern):
        self.pattern = pattern
    def __call__(self, path, st):
        return match_pattern(os.path.basename(path), self.pattern, case_sensitive=False)

class Type(Expr):
    def __init__(self, t):
        self.t = t
    def __call__(self, path, st):
        t = self.t
        if t == 'f':
            return stat.S_ISREG(st.st_mode)
        elif t == 'd':
            return stat.S_ISDIR(st.st_mode)
        elif t == 'l':
            return stat.S_ISLNK(st.st_mode)
        elif t == 'b':
            return stat.S_ISBLK(st.st_mode)
        elif t == 'c':
            return stat.S_ISCHR(st.st_mode)
        elif t == 'p':
            return stat.S_ISFIFO(st.st_mode)
        elif t == 's':
            return stat.S_ISSOCK(st.st_mode)
        return False

class User(Expr):
    def __init__(self, user):
        self.uid = int(user) if user.isdigit() else pwd.getpwnam(user).pw_uid
    def __call__(self, path, st):
        return st.st_uid == self.uid

class Group(Expr):
    def __init__(self, group):
        self.gid = int(group) if group.isdigit() else grp.getgrnam(group).gr_gid
    def __call__(self, path, st):
        return st.st_gid == self.gid

class Size(Expr):
    def __init__(self, size):
        self.size = size
    def __call__(self, path, st):
        # st_size in bytes
        return n_compare(st.st_size, self.size)

class Mtime(Expr):
    def __init__(self, n):
        self.n = n
    def __call__(self, path, st):
        days = int(self.n.lstrip('+-'))
        now = time.time()
        mtime = st.st_mtime
        age_days = int((now - mtime) // 86400)
        return n_compare(age_days, self.n)

class Atime(Expr):
    def __init__(self, n):
        self.n = n
    def __call__(self, path, st):
        days = int(self.n.lstrip('+-'))
        now = time.time()
        atime = st.st_atime
        age_days = int((now - atime) // 86400)
        return n_compare(age_days, self.n)

class Ctime(Expr):
    def __init__(self, n):
        self.n = n
    def __call__(self, path, st):
        days = int(self.n.lstrip('+-'))
        now = time.time()
        ctime = st.st_ctime
        age_days = int((now - ctime) // 86400)
        return n_compare(age_days, self.n)

class TrueExpr(Expr):
    def __call__(self, path, st):
        return True

class FalseExpr(Expr):
    def __call__(self, path, st):
        return False

# --- Actions ---
def action_print(path, st):
    print(path)
    return True

def action_print0(path, st):
    print(path, end='\0')
    return True

def action_delete(path, st):
    try:
        if stat.S_ISDIR(st.st_mode):
            os.rmdir(path)
        else:
            os.remove(path)
        return True
    except Exception as e:
        print(f"delete failed: {e}", file=sys.stderr)
        return False

# --- Expression parser ---
def parse_expr(args):
    """Parse a list of args into an expression tree and actions."""
    # Only a subset of find's syntax is supported for brevity
    expr = TrueExpr()
    actions = [action_print]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '-name':
            expr = And(expr, Name(args[i+1]))
            i += 2
        elif arg == '-iname':
            expr = And(expr, Iname(args[i+1]))
            i += 2
        elif arg == '-type':
            expr = And(expr, Type(args[i+1]))
            i += 2
        elif arg == '-user':
            expr = And(expr, User(args[i+1]))
            i += 2
        elif arg == '-group':
            expr = And(expr, Group(args[i+1]))
            i += 2
        elif arg == '-size':
            expr = And(expr, Size(args[i+1]))
            i += 2
        elif arg == '-mtime':
            expr = And(expr, Mtime(args[i+1]))
            i += 2
        elif arg == '-atime':
            expr = And(expr, Atime(args[i+1]))
            i += 2
        elif arg == '-ctime':
            expr = And(expr, Ctime(args[i+1]))
            i += 2
        elif arg == '-print':
            actions = [action_print]
            i += 1
        elif arg == '-print0':
            actions = [action_print0]
            i += 1
        elif arg == '-delete':
            actions = [action_delete]
            i += 1
        elif arg == '-true':
            expr = And(expr, TrueExpr())
            i += 1
        elif arg == '-false':
            expr = And(expr, FalseExpr())
            i += 1
        elif arg == '!':
            # Negate next expr
            subexpr, skip = parse_expr(args[i+1:])
            expr = And(expr, Not(subexpr))
            i += skip + 1
        elif arg == '-not':
            subexpr, skip = parse_expr(args[i+1:])
            expr = And(expr, Not(subexpr))
            i += skip + 1
        elif arg == '-and' or arg == '-a':
            i += 1
        elif arg == '-or' or arg == '-o':
            subexpr, skip = parse_expr(args[i+1:])
            expr = Or(expr, subexpr)
            i += skip + 1
        elif arg == '(':  # Not implemented: grouping
            i += 1
        elif arg == ')':
            i += 1
        elif arg == '--help':
            print_help()
            sys.exit(0)
        elif arg == '--version':
            print(VERSION)
            sys.exit(0)
        else:
            # Unknown arg, skip
            i += 1
    return expr, i

def print_help():
    print(f"""Usage: pyfind [path...] [expression]\n\nA minimal Python implementation of the Unix find tool.\n\nSupported tests: -name, -iname, -type, -user, -group, -size, -mtime, -atime, -ctime, -true, -false\nSupported actions: -print, -print0, -delete\nSupported operators: !, -not, -and, -a, -or, -o\nOther: --help, --version\n\nDefault path is the current directory; default action is -print.\n""")

# --- Main walk logic ---
def walk(paths, expr, actions, mindepth=0, maxdepth=None):
    for top in paths:
        for root, dirs, files in os.walk(top, topdown=True, followlinks=False):
            rel_depth = root[len(top):].count(os.sep)
            if mindepth and rel_depth < mindepth:
                continue
            if maxdepth is not None and rel_depth > maxdepth:
                del dirs[:]
                continue
            for name in files + dirs:
                path = os.path.join(root, name)
                try:
                    st = os.lstat(path)
                except Exception:
                    continue
                if expr(path, st):
                    for action in actions:
                        action(path, st)

# --- CLI entry ---
def main():
    argv = sys.argv[1:]
    # Parse paths
    paths = []
    i = 0
    while i < len(argv):
        if argv[i].startswith('-'):
            break
        paths.append(argv[i])
        i += 1
    if not paths:
        paths = ['.']
    expr_args = argv[i:]
    expr, _ = parse_expr(expr_args)
    # Actions are set by parse_expr, but only last one is used
    actions = [action_print]
    for j, arg in enumerate(expr_args):
        if arg == '-print':
            actions = [action_print]
        elif arg == '-print0':
            actions = [action_print0]
        elif arg == '-delete':
            actions = [action_delete]
    # Depth options (not full find semantics)
    mindepth = 0
    maxdepth = None
    if '-mindepth' in expr_args:
        idx = expr_args.index('-mindepth')
        mindepth = int(expr_args[idx+1])
    if '-maxdepth' in expr_args:
        idx = expr_args.index('-maxdepth')
        maxdepth = int(expr_args[idx+1])
    walk(paths, expr, actions, mindepth, maxdepth)

if __name__ == '__main__':
    main()
