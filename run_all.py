import os
import shutil
import subprocess
import sys

from projects import ALL_BUGS

root = os.path.dirname(__file__)
sys.path.append(root)

def run_all_bugs(config_name: str):
    for version in ALL_BUGS:
        for proj in ALL_BUGS[version]:
            bugIDs = ALL_BUGS[version][proj][0]
            deprecatedIDs = ALL_BUGS[version][proj][1]
            subproj = ALL_BUGS[version][proj][2] if version == "GrowingBugs" else ""
            for bug_id in bugIDs:
                res_path = os.path.join(root, f"DebugResult/d4j{version}-{proj}-{bug_id}")
                res_file = os.path.join(res_path, "result.json")
                if bug_id in deprecatedIDs:
                    continue
                if os.path.exists(res_file):
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