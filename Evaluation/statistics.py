import os
import shutil
import subprocess as sp
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from functions.d4j import check_out
from functions.extract_classes import extract_classes_statistic
from functions.utils import run_cmd
from run_all import D4J_ALL

OTHER_BUGS = {
    "6.1": {
        "Zip4j": {
            "begin": 1,
            "end": 52,
            "deprecate": []
        },
        "Dagger_core": {
            "subproject": "core",
            "begin": 1,
            "end": 20,
            "deprecate": []
        },
        "Wicket_core": {
            "subproject": "wicket-core",
            "begin": 1,
            "end": 18,
            "deprecate": []
        },
    }
}

def class_extraction_statistics_others(version):
    """Statistic the coverage rank of modified class in all covered classes
    """
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.join(cur_dir, "tmp_repo")
    res_file = os.path.join(cur_dir, "classes_statistics.csv")

    # state recovery
    already = defaultdict(dict)
    if os.path.exists(res_file):
        with open(res_file, 'r') as f:
            for line in f:
                if line == "":
                    continue
                proj, bug_id, n_loaded, rank = line.strip().split(",")
                if rank != "NOT_COVERED":
                    rank = int(rank)
                already[proj][int(bug_id)] = {"n_loaded": int(n_loaded), "rank": rank}
    
    for proj in OTHER_BUGS[version]:
        for bug_id in range(OTHER_BUGS[version][proj]["begin"], OTHER_BUGS[version][proj]["end"] + 1):
            if bug_id in OTHER_BUGS[version][proj]["deprecate"]:
                continue
            if proj in already and bug_id in already[proj]:
                continue
            buggy_dir = os.path.join(repo_dir, proj, str(bug_id), "buggy")
            if "subproject" in OTHER_BUGS[version][proj]:
                sub_proj = OTHER_BUGS[version][proj]["subproject"]
            else:
                sub_proj = None
            if not os.path.exists(buggy_dir):
                os.makedirs(buggy_dir)
                if sub_proj:
                    os.system(f"defects4j checkout -p {proj} -v {bug_id}b -w {buggy_dir} -s {sub_proj}")
                    buggy_dir = os.path.join(buggy_dir, sub_proj)
                else:
                    os.system(f"defects4j checkout -p {proj} -v {bug_id}b -w {buggy_dir}")

            print(buggy_dir)
            # get modified class
            cmd1 = f"defects4j export -p classes.modified -w {buggy_dir}"
            p = sp.Popen(cmd1.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            output, err = p.communicate()
            out = output.decode("utf-8")
            err = err.decode("utf-8")
            modified_classes = out.split("\n")

            # get failed test suite
            cmd2 = f"defects4j export -p tests.trigger -w {buggy_dir}"
            p = sp.Popen(cmd2.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            output, err = p.communicate()
            out = output.decode("utf-8")
            err = err.decode("utf-8")
            failed_tests = out.split("\n")
            print(err)
            test_suite = {}
            for test in failed_tests:
                test_suite_name = test.split("::")[0]
                if test_suite_name in test_suite:
                    test_suite[test_suite_name].append(test)
                else:
                    test_suite[test_suite_name] = [test]

            # get extracted classes
            index_list = []
            n_loaded_list = []
            for test_suite_name in test_suite:
                loaded_classes, covered_classes, extracted_classes = extract_classes_statistic(
                    proj,
                    bug_id,
                    test_suite[test_suite_name],
                    repo_dir,
                    "/home/qyh/projects/LLM-Location/preprocess/classtracer/target/classtracer-1.0.jar",
                    30,
                    sub_proj=sub_proj
                )
                for java_classes in loaded_classes:
                    n_loaded_list.append(len(java_classes))
                
                for java_classes in covered_classes:
                    classes_names = [c.class_name for c in java_classes]
                    for modified_class in modified_classes:
                        try:
                            index = classes_names.index(modified_class) + 1
                            index_list.append(index)
                        except Exception:
                            print(f"{modified_class} not in covered classes")
                            pass
            try:
                rank = int(sum(index_list) / len(index_list))
            except Exception:
                # don't find modified class
                rank = "NOT_COVERED"
            n_loaded = int(sum(n_loaded_list) / len(n_loaded_list))
            already[proj][bug_id] = {"n_loaded": n_loaded, "rank": rank}
            with open(res_file, 'a') as f:
                f.write(f"{proj},{bug_id},{n_loaded},{rank}\n")
    
    # print statistics result
    for proj in already:
        n_bug = 0
        all_loaded = 0
        all_rank = 0
        for bug_id in already[proj]:
            if already[proj][bug_id]["rank"] != "NOT_COVERED":
                n_bug += 1
                all_loaded += already[proj][bug_id]["n_loaded"]
                all_rank += already[proj][bug_id]["rank"]
        print(f"project:{proj} bugs:{n_bug} n_avg_loaded_classes:{(all_loaded / n_bug):.2f} avg_modified_class_rank:{(all_rank / n_bug):.2f}")
    
    shutil.rmtree(repo_dir)


def class_extraction_statistics(version, repo_dir):
    """Statistic the coverage rank of modified class in all covered classes
    """
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    res_file = os.path.join(cur_dir, "classes_statistics.csv")
    
    # state recovery
    already = defaultdict(dict)
    if os.path.exists(res_file):
        with open(res_file, 'r') as f:
            for line in f:
                if line == "":
                    continue
                proj, bug_id, n_loaded, rank = line.strip().split(",")
                if rank != "NOT_COVERED":
                    rank = int(rank)
                already[proj][int(bug_id)] = {"n_loaded": int(n_loaded), "rank": rank}
    
    for proj in D4J_ALL[version]:
        for bug_id in range(D4J_ALL[version][proj]["begin"], D4J_ALL[version][proj]["end"] + 1):
            if bug_id in D4J_ALL[version][proj]["deprecate"]:
                continue
            if proj in already and bug_id in already[proj]:
                continue
            buggy_dir = os.path.join(repo_dir, proj, str(bug_id), "buggy")
            os.chdir(buggy_dir)

            # get modified class
            cmd1 = f"defects4j export -p classes.modified"
            p = sp.Popen(cmd1.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            output, err = p.communicate()
            out = output.decode("utf-8")
            err = err.decode("utf-8")
            modified_classes = out.split("\n")

            # get failed test suite
            cmd2 = f"defects4j export -p tests.trigger"
            p = sp.Popen(cmd2.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            output, err = p.communicate()
            out = output.decode("utf-8")
            err = err.decode("utf-8")
            failed_tests = out.split("\n")
            test_suite = {}
            for test in failed_tests:
                test_suite_name = test.split("::")[0]
                if test_suite_name in test_suite:
                    test_suite[test_suite_name].append(test)
                else:
                    test_suite[test_suite_name] = [test]

            # get extracted classes
            index_list = []
            n_loaded_list = []
            for test_suite_name in test_suite:
                loaded_classes, covered_classes, extracted_classes = extract_classes_statistic(
                    proj,
                    bug_id,
                    test_suite[test_suite_name],
                    repo_dir,
                    "/home/qyh/projects/LLM-Location/preprocess/classtracer/target/classtracer-1.0.jar",
                    30,
                )
                for java_classes in loaded_classes:
                    n_loaded_list.append(len(java_classes))
                
                for java_classes in covered_classes:
                    classes_names = [c.class_name for c in java_classes]
                    for modified_class in modified_classes:
                        try:
                            index = classes_names.index(modified_class) + 1
                            index_list.append(index)
                        except Exception:
                            print(f"{modified_class} not in covered classes")
                            pass
            try:
                rank = int(sum(index_list) / len(index_list))
            except Exception:
                # don't find modified class
                rank = "NOT_COVERED"
            n_loaded = int(sum(n_loaded_list) / len(n_loaded_list))
            already[proj][bug_id] = {"n_loaded": n_loaded, "rank": rank}
            with open(res_file, 'a') as f:
                f.write(f"{proj},{bug_id},{n_loaded},{rank}\n")
    
    # print statistics result
    for proj in already:
        n_bug = 0
        all_loaded = 0
        all_rank = 0
        for bug_id in already[proj]:
            if already[proj][bug_id]["rank"] != "NOT_COVERED":
                n_bug += 1
                all_loaded += already[proj][bug_id]["n_loaded"]
                all_rank += already[proj][bug_id]["rank"]
        print(f"project:{proj} bugs:{n_bug} n_avg_loaded_classes:{(all_loaded / n_bug):.2f} avg_modified_class_rank:{(all_rank / n_bug):.2f}")


def bug_info_statistics(version):
    """Statistic the coverage rank of modified class in all covered classes
    """
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    res_file = os.path.join(cur_dir, f"bug_info_statistics_d4j{version}.csv")
    
    # state recovery
    already = defaultdict(dict)
    if os.path.exists(res_file):
        with open(res_file, 'r') as f:
            for line in f:
                if line == "":
                    continue
                proj, bug_id, n_test_suites, max_test_cases, n_modified_classes = line.strip().split(",")
                already[proj][int(bug_id)] = {
                    "n_test_suites": n_test_suites,
                    "max_test_cases": max_test_cases,
                    "n_modified_classes": n_modified_classes,
                }
    
    f = open(res_file, "a")
    f.write("project,bug_id,n_test_suites,max_test_cases,n_modified_classes\n")
    
    for proj in D4J_ALL[version]:
        for bug_id in range(D4J_ALL[version][proj]["begin"], D4J_ALL[version][proj]["end"] + 1):
            if bug_id in D4J_ALL[version][proj]["deprecate"]:
                continue
            if proj in already and bug_id in already[proj]:
                continue

            # get info
            cmd = f"defects4j info -p {proj} -b {bug_id}"
            p = sp.Popen(cmd.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            output, err = p.communicate()
            out = output.decode("utf-8")
            err = err.decode("utf-8")
            info = out.split("\n")
            
            # parse info
            failed_tests = defaultdict(list)
            modified_classes = []
            i = 0
            while(i < len(info)):
                if info[i].startswith("Root cause in triggering tests:"):
                    while(not info[i].startswith("----")):
                        if info[i].startswith(" - "):
                            test_suite = info[i].split("::")[0][3:]
                            failed_tests[test_suite].append(info[i][3:])
                        i += 1
                elif info[i].startswith("List of modified sources:"):
                    while(not info[i].startswith("----")):
                        if info[i].startswith(" - "):
                            modified_classes.append(info[i][3:])
                        i += 1
                else:
                    i += 1
            
            n_test_suites = len(failed_tests)
            max_test_cases = max([len(failed_tests[test_suite]) for test_suite in failed_tests])
            n_modified_classes = len(modified_classes)
            f.write(f"{proj},{bug_id},{n_test_suites},{max_test_cases},{n_modified_classes}\n")
            print(f"{proj}-{bug_id} n_test_suites:{n_test_suites} max_test_cases:{max_test_cases} n_modified_classes:{n_modified_classes}")


def cal_n_predictions(res_dir):
    import json
    output = {"=0":0, "<3":0, "<5":0}
    res_dir = "../DebugResult_d4j140_GPT35"
    for sample in os.listdir(res_dir):
        with open(os.path.join(res_dir, sample, "result.json"), "r") as f:
            data = json.load(f)
            if len(data["buggy_methods"]) < 3:
                output["<3"] += 1
            if len(data["buggy_methods"]) < 5:
                output["<5"] += 1
            if len(data["buggy_methods"]) == 0:
                output["=0"] += 1
    print(output)


def cal_incorrect_predictions(res_file):
    import pandas as pd
    df = pd.read_csv(res_file)
    df = df[['project', 'false_positive', 'recall_ratio', 'true_method']]
    df = df[(df["true_method"] == 0) & (df["recall_ratio"].str[0] != "0") & (df["false_positive"] > 0)]
    print(df.head())
    df.to_csv("/home/qyh/projects/LLM-Location/AgentFL/EvaluationResult/incorrect_predictions.csv", index=False)

if __name__ == "__main__":
    # class_extraction_statistics("1.4.0", "/home/qyh/projects/LLM-Location/preprocess/Defects4J-1.4.0")
    class_extraction_statistics_others("6.1")
    # bug_info_statistics("2.0.0")
    # cal_n_predictions("/home/qyh/projects/LLM-Location/AgentFL/DebugResult_d4j140_GPT35")
    # cal_incorrect_predictions("/home/qyh/projects/LLM-Location/AgentFL/EvaluationResult/DebugResult_d4j140_GPT35.csv")