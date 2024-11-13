import json
import os
import re
import shutil
import sys
import test
from pathlib import Path

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root)

from functions.d4j import check_out
from functions.line_parser import parse_test_report
from functions.methodExtractor.myparser.functions_extractor import FunctionsExtractor
from functions.utils import run_cmd

filepath = os.path.dirname(__file__)
TREE_SITTER_LIB_PATH = os.path.join(
    filepath, "methodExtractor/myparser/my-languages.so")


def make_fix_dataset(chat_chain, test_failure_obj):
    # move the top1 method to the first
    res_dict = chat_chain.chat_env.res_dict
    top1_method_name = res_dict["top1_method"]["method_name"]
    top1_method = list(filter(lambda x: x["method_name"] == top1_method_name, res_dict["buggy_methods"]))[0]
    res_dict["buggy_methods"].remove(top1_method)
    res_dict["buggy_methods"].insert(0, top1_method)
    
    # extract trigger tests
    trigger_tests = {}
    test_log_dir = Path(chat_chain.directory) / "tmp"
    for test_suite in test_failure_obj.test_suites:
        for test_case in test_suite.test_cases:
            stack_trace_file = test_log_dir / test_suite.name / test_case.name / "stack_trace.txt"
            test_path = test_case.test_method.class_name.replace(".", "/") + ".java"
            with open(stack_trace_file, "r") as f:
                stack_trace = f.read()
            clean_lines = stack_trace.split("\n")[:2]
            test_info = {
                "path": test_path,
                "function_name": test_case.test_method.name,
                "src": test_case.test_method.code,
                "error_msg": stack_trace,
                "clean_error_msg": "\n".join(clean_lines),
            }
            trigger_tests[test_case.name] = test_info
    if len(trigger_tests) == 0:
        raise ValueError("No trigger test found")
    
    buggy_path = Path(chat_chain.directory) / "buggy"
    cmd = f"defects4j export -p dir.src.classes -w {buggy_path}"
    src_path, err = run_cmd(cmd)

    java_method_extractor = FunctionsExtractor(TREE_SITTER_LIB_PATH, ["java"])
    suspicious_methods = []
    for method in res_dict["buggy_methods"]:
        class_name = method["class_name"]
        if "$" in class_name:
            class_name = class_name.split("$")[0]
        loc = os.path.join(src_path, class_name.replace(".", "/") + ".java")
        suspicious_method = {
            "buggy": method["method_code"].replace("```java\n", "").replace("```", ""),
            "fix": "",
            "start": method["method_loc"][0][0],
            "end": method["method_loc"][1][0],
            "loc": loc,
            "method_signature": {'method_name': method["method_name"].split("::")[1].split("(")[0]},
            "trigger_test": trigger_tests,
            "buggy_code_comment": method["method_doc"],
        }
        suspicious_methods.append(suspicious_method)

    dataset_for_fix_file = Path(chat_chain.directory) / "dataset_for_fix.json"
    with open(dataset_for_fix_file, "w") as f:
        json.dump(suspicious_methods, f, indent=2)


def sample_fix_dataset(all_bugs, top_k):
    res_path = os.path.join(root, "DebugResult")
    dataset_path = os.path.join(res_path, "fix_dataset")
    if not os.path.exists(dataset_path):
        os.makedirs(dataset_path, exist_ok=True)
    
    version = "GrowingBugs"
    for i in range(1, top_k+1):
        dataset = {}
        for proj in all_bugs:
            bugIDs = all_bugs[proj][0]
            deprecatedIDs = all_bugs[proj][1]
            subproj = all_bugs[proj][2]
            if subproj == "None":
                subproj = ""
            for bug_id in bugIDs:
                if bug_id in deprecatedIDs:
                    continue

                bug_name = f"{proj}-{bug_id}"
                fl_res_dir = os.path.join(res_path, f"d4j{version}-{proj}-{bug_id}")
                dataset_file = os.path.join(fl_res_dir, "dataset_for_fix.json")
                with open(dataset_file, "r") as f:
                    dataset_for_fix = json.load(f)
                if i <= len(dataset_for_fix):
                    dataset[bug_name] = dataset_for_fix[i-1]

        with open(os.path.join(dataset_path, f"dataset_rank_{i}.json"), "w") as f:
            json.dump(dataset, f, indent=2)
