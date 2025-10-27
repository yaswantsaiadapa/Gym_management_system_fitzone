import sys, importlib, pathlib
print("cwd:", pathlib.Path.cwd())
print("sys.path[0]:", sys.path[0])
try:
    m = importlib.import_module("app")
    print("import app OK, attrs:", [a for a in dir(m) if a.startswith("create") or a=="__file__"])
    m2 = importlib.import_module("app.app")
    print("import app.app OK, create_app:", hasattr(m2, "create_app"))
except Exception as e:
    print("IMPORT ERROR:", type(e).__name__, e)
