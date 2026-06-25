import os
import sys
import re
import ctypes
from pathlib import Path

ROOT = Path('.').resolve()
SRC_CPP = ROOT / "src" / "cpp"
INC_NAME = "params_fields.inc"
INC_PATH = SRC_CPP / INC_NAME
PARAMS_H = SRC_CPP / "params.hpp"
CMAKE = ROOT / "CMakeLists.txt"
BUILD = ROOT / "build"

def print_header(title):
    print("\n" + "="*8 + " " + title + " " + "="*8)

def exists_and_readable(p: Path):
    ok = p.exists()
    readable = False
    size = None
    try:
        if ok:
            size = p.stat().st_size
            with p.open("rb") as f:
                f.read(1)
            readable = True
    except Exception as e:
        print(f"  [err] cannot open {p}: {e}")
    return ok, readable, size

def list_dir(p: Path):
    try:
        for e in sorted(p.iterdir()):
            print(f"  {e.name}  (size={e.stat().st_size})")
    except Exception as e:
        print(f"  [err] listing {p}: {e}")

def find_similar_names(dirname: Path, needle: str):
    hits = []
    if not dirname.exists(): return hits
    for e in dirname.iterdir():
        if needle.lower() in e.name.lower() or e.name.lower().startswith(needle.split('_')[0]):
            hits.append(e.name)
    return hits

def read_top(path: Path, n=40):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return ''.join([next(f) for _ in range(n)])
    except StopIteration:
        return ''
    except Exception as e:
        return f"<error reading: {e}>"

def check_windows_offline(p: Path):
    # FILE_ATTRIBUTE_OFFLINE = 0x1000, FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
        if attrs == -1:
            return None
        flags = []
        if attrs & 0x1000: flags.append("OFFLINE")
        if attrs & 0x400000: flags.append("RECALL_ON_DATA_ACCESS")
        if attrs & 0x1: flags.append("READONLY")
        return flags
    except Exception:
        return None

def scan_cmakelists(path: Path):
    if not path.exists(): return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    found = {
        "target_include_directories": re.findall(r"target_include_directories\s*\(\s*([^\s\)]+)[\s\S]*?\)", text, flags=re.IGNORECASE),
        "target_sources": re.findall(r"target_sources\s*\([^\)]*?\)", text, flags=re.IGNORECASE),
        "params_refs": re.findall(r"params_fields\.inc|params_field\.inc", text, flags=re.IGNORECASE),
        "typos": re.findall(r"params_field\.inc", text, flags=re.IGNORECASE),
    }
    return found

def main():
    print_header("Project root")
    print(f"  {ROOT}")

    print_header("src/cpp listing")
    list_dir(SRC_CPP)

    print_header(f"Check {INC_PATH}")
    ok, readable, size = exists_and_readable(INC_PATH)
    print(f"  exists: {ok}, readable: {readable}, size: {size}")

    if not ok:
        print("  -> params_fields.inc not found where expected.")
        similar = find_similar_names(SRC_CPP, "params_fields")
        if similar:
            print("  -> similar filenames in src/cpp:")
            for s in similar: print(f"     {s}")
    else:
        print("  -> first lines of the .inc:")
        print(read_top(INC_PATH, 10))

    print_header(f"Check params.hpp ({PARAMS_H.name})")
    if PARAMS_H.exists():
        top = read_top(PARAMS_H, 60)
        print(top)
        m = re.search(r'#\s*include\s*["<]([^">]+params_fields[^">]*)[">]', top)
        if m:
            print(f"  include line references: {m.group(1)}")
        else:
            print("  -> no include for params_fields.inc found in params.hpp (or different syntax).")
    else:
        print(f"  params.hpp missing at {PARAMS_H}")

    print_header("Scan CMakeLists.txt")
    if CMAKE.exists():
        print(f"  {CMAKE}")
        cm = scan_cmakelists(CMAKE)
        print("  params_fields references found in CMakeLists:")
        for k,v in cm.items():
            print(f"    {k}: {len(v)} hits")
        if cm.get("typos"):
            print("  -> possible typo found: 'params_field.inc' referenced in CMakeLists")
        txt = CMAKE.read_text(encoding="utf-8", errors="replace")
        if "target_include_directories" in txt.lower():
            print("  -> target_include_directories appears in CMakeLists (verify the path includes src/cpp).")
    else:
        print("  CMakeLists.txt not found")

    print_header("Build dir / CMake cache")
    if BUILD.exists():
        print(f"  build dir exists: {BUILD}")
        cmk = BUILD / "CMakeCache.txt"
        if cmk.exists():
            print("  CMakeCache.txt exists: scanning for include dirs and python")
            txt = cmk.read_text(encoding="utf-8", errors="replace")
            if "INCLUDE_DIRECTORIES" in txt.upper() or "CMAKE_INCLUDE" in txt.upper():
                print("   (CMakeCache contains include-related entries; inspect manually)")
            # quick search for src/cpp path
            if str(SRC_CPP) in txt:
                print("   build cache references src/cpp")
        else:
            print("  No CMakeCache.txt found (first configure maybe failed).")
    else:
        print("  build dir does not exist (or was removed).")

    if os.name == 'nt' and INC_PATH.exists():
        print_header("Windows file attributes")
        flags = check_windows_offline(INC_PATH)
        print(f"  attributes flags: {flags}")

    print_header("Summary / Suggestions")
    if not INC_PATH.exists():
        print("  - Ensure params_fields.inc is at src/cpp/params_fields.inc (or update include path).")
        print("  - Check for typos: 'params_field.inc' vs 'params_fields.inc' in CMakeLists and source.")
    else:
        if not readable:
            print("  - File exists but cannot be read. Check permissions or OneDrive placeholder state.")
        else:
            print("  - File present and readable. Likely cause: compiler include paths missing.")
            print("    * Make sure CMake target_include_directories(...) includes src/cpp.")
            print("    * Or change params.hpp include to the relative path used by the compiler.")
            print("    * Optionally remove/guard target_sources(... params_fields.inc) in CMake if file optional.")
    print("\nDone.")

if __name__ == "__main__":
    main()