import os
import shutil
import subprocess
import sys

from projects import SBF

ALL_BUGS = SBF

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
            res_path = f"DebugResult/{config_name}/{version}/{proj}/{proj}-{bug_id}"
            res_path = os.path.join(root, res_path)
            if bug_id in deprecatedIDs:
                continue
            if os.path.exists(res_path):
                print(f"{version}-{proj}-{bug_id} already finished, skip!")
                continue
            
            ret_code = run_one_bug(config_name, version, proj, bug_id, subproj)
            if ret_code != 0:
                shutil.rmtree(res_path, ignore_errors=True)
                raise Exception(f"Error in running {version}-{proj}-{bug_id}!")

def run_one_bug(config_name, version, proj, bug_id, subproj):
    cmd = f"python run.py --config {config_name} --version {version} --project {proj} --bugID {bug_id} --subproj {subproj} --model DeepSeek"
    result = subprocess.run(cmd.split(" "))
    return result.returncode

if __name__ == "__main__":
    config_name = "Default"
    run_all_bugs(config_name)