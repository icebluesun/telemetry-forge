import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

print(f"Current directory: {os.getcwd()}")

project_root = Path(__file__).parent.parent

def run():
    print("Running dbt transformations...")
    
    dbt_path = project_root / "dbt"
    os.chdir(dbt_path)
    
    # Run dbt with full refresh
    result = subprocess.run(
        ["uv", "run", "dbt", "run", "--profiles-dir", ".", "--full-refresh"],
        cwd=dbt_path,
        capture_output=False
    )
                  
    if result.returncode != 0:
        print("dbt run failed")
        return False
    
    print("dbt run successful")
    
    # Run dbt tests
    print("Running dbt tests...")
    result = subprocess.run(
        ["uv", "run", "dbt", "test", "--profiles-dir", "."],
        capture_output=False
    )
    
    if result.returncode != 0:
        print("dbt tests had errors (continuing anyway)")
    else:
        print("dbt tests passed")
    
    # Generate dbt docs
    print("Generating dbt docs...")
    subprocess.run(
        ["uv", "run", "dbt", "docs", "generate", "--profiles-dir", "."],
        capture_output=False
    )
    
    os.chdir(project_root)
    print("dbt complete!")
    return True

if __name__ == "__main__":
    run()