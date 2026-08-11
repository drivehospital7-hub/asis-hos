"""Quick script to check for print() in auditoria service files."""
import os
import sys

ok = True
base = os.path.join(os.path.dirname(__file__), "..", "..", "app", "services", "auditoria")
for dirpath, _dirnames, files in os.walk(base):
    for fn in files:
        if not fn.endswith(".py"):
            continue
        path = os.path.join(dirpath, fn)
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue
                if "print(" in stripped:
                    rel = os.path.relpath(path, os.path.join(base, "..", ".."))
                    print(f"print() found in {rel}:{i}: {stripped}")
                    ok = False

if ok:
    print("NO print() FOUND IN ANY SERVICE FILE")
    sys.exit(0)
else:
    sys.exit(1)
