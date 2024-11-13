import argparse
import os
import shutil
import subprocess
import sys

from functions.generate_dataset import sample_fix_dataset
from projects import projectDict

ALL_BUGS = projectDict

root = os.path.dirname(__file__)
sys.path.append(root)

def run_all_bugs(config_name: str):
    version = "GrowingBugs"
    for proj in ALL_BUGS:
        bugIDs = ALL_BUGS[proj][0]
        deprecatedIDs = ALL_BUGS[proj][1]
        subproj = ALL_BUGS[proj][2]
        if subproj == "None":
            subproj = ""
        for bug_id in bugIDs:
            res_path = os.path.join(root, f"DebugResult/d4j{version}-{proj}-{bug_id}")
            res_file = os.path.join(res_path, "result.json")
            if bug_id in deprecatedIDs:
                continue
            # if os.path.exists(res_file):
            #     print(f"{version}-{proj}-{bug_id} already finished, skip!")
            #     continue
            
            ret_code = run_one_bug(config_name, version, proj, bug_id, subproj)
            # if ret_code != 0:
            #     shutil.rmtree(res_path, ignore_errors=True)
            #     raise Exception(f"Error in running {version}-{proj}-{bug_id}!")
    
    sample_fix_dataset(ALL_BUGS, 5)

def run_one_bug(config_name, version, proj, bug_id, subproj):
    cmd = f"python run.py --config {config_name} --version {version} --project {proj} --bugID {bug_id} --subproj {subproj} --model DeepSeek"
    result = subprocess.run(cmd.split(" "))
    return result.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='argparse')
    parser.add_argument('-k', type=int, default=1)
    args = parser.parse_args()
    config_name = "Default"
    run_all_bugs(config_name)