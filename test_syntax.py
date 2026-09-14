import ast
import sys

def check_syntax(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        ast.parse(content)
        print(f"✓ {file_path} - Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path} - Syntax Error: {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path} - Error: {e}")
        return False

files_to_check = [
    "backend/api/auth.py",
    "backend/api/utils/utils.py",
    "backend/api/constituency.py",
    "backend/api/governors.py",
    "backend/app.py",
    "extract_and_seed.py",
    "governor_seed.py"
]

all_good = True
for file_path in files_to_check:
    if not check_syntax(file_path):
        all_good = False

if all_good:
    print("\nAll files have valid syntax!")
else:
    print("\nSome files have syntax errors!")
    sys.exit(1)