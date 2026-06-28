import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

project_root = Path(__file__).parent.parent
os.chdir(project_root)

def run():
    print("📊 Starting dashboard...")
    sys.argv = ["streamlit", "run", "dashboard/app.py"]
    from streamlit.web import cli as stcli
    stcli.main()

if __name__ == "__main__":
    run()