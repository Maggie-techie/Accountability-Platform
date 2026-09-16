import ast
import sys
import os

def check_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check Python files with ast
        if file_path.endswith('.py'):
            ast.parse(content)
            print(f"✓ {file_path} - Syntax OK")
            return True
        # For HTML, CSS, JS files, just check if they're readable and not empty
        elif file_path.endswith(('.html', '.css', '.js')):
            if len(content.strip()) > 0:
                print(f"✓ {file_path} - File readable and not empty")
                return True
            else:
                print(f"✗ {file_path} - File is empty")
                return False
        else:
            # For other file types, just check if readable
            print(f"✓ {file_path} - File readable")
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
    "backend/api/ai_engine.py",
    "backend/app.py",
    "extract_and_seed.py",
    "governor_seed.py",
    "warm_cache.py",
    # Frontend files
    "frontend/index.html",
    "frontend/mps.html",
    "frontend/constituency.html",
    "frontend/findings.html",
    "frontend/allocations.html",
    "frontend/governor.html",
    "frontend/governor-departments.html",
    "frontend/governor-findings.html",
    "frontend/compare.html",
    "frontend/css/style.css",
    "frontend/js/main.js"
]

all_good = True
for file_path in files_to_check:
    if not check_syntax(file_path):
        all_good = False

if all_good:
    print("\nAll files are OK!")
else:
    print("\nSome files have issues!")
    sys.exit(1)