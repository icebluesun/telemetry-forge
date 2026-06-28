from dotenv import load_dotenv
load_dotenv()
import subprocess
import os
os.chdir("dbt")
subprocess.run(["dbt", "run", "--profiles-dir", "."])