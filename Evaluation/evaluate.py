import json
import os
import pickle
import sys
from collections import defaultdict

from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from run_all import D4J_ALL

N_PHASES = {"Default": 6,
            "BaseOnGrace": 2,
            "Baseline": 1,
            "NoTestBehaviorAnalysis": 5,
            "NoTestFailureAnalysis": 4,
            "NoMethodDocEnhancement": 5}

def get_metrics(project, bug_id, result_dict, res_file, test_failure_file):
    true_method = 0
    method_rank = "N/A"
    recall = 0
    fp = 0
    num_buggy = None
    
    res = json.load(open(res_file, "r"))
    if len(res["buggy_methods"]) == 0:
        top1_method = None
    elif res["top1_method"] == {}:
        top1_method = res["buggy_methods"][0]["method_name"]
    else:
        top1_method = res["top1_method"]["method_name"]

    test_failure = pickle.load(open(test_failure_file, "rb"))
    buggy_methods = test_failure.buggy_methods

    # get num_buggy and true_method
    num_buggy = len(buggy_methods)
    for buggy_method in buggy_methods:
        if buggy_method == top1_method:
            true_method = 1
            method_rank = 1
            break
    
    # get method rank
    if method_rank == "N/A":
        rank = 0
        for m in res["buggy_methods"]:
            rank += 1
            if m["method_name"] in buggy_methods:
                break
        else:
            rank = 0
        if rank > 0:
            if res["buggy_methods"][0]["method_name"] in buggy_methods:
                rank += 1
            method_rank = rank

    # get recall and fp
    for n in res["buggy_codes"]:
        if n not in buggy_methods:
            fp += 1
        else:
            recall += 1
    recall_ratio = f"{recall}|{num_buggy}"
    
    result_dict[project][bug_id] = {"true_method": true_method,
                                    "method_rank": method_rank,
                                    "recall_ratio": recall_ratio,
                                    "false_positive": fp}
    
    return result_dict

def get_post_info(project, bug_id, result_dict, info_files):
    cost = 0
    total_tokens = 0
    time = 0
    
    for info_file in info_files:
        with open(info_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("**cost**"):
                    cost += float(line.split("$")[1].rstrip())
                elif line.startswith("**num_total_tokens**"):
                    total_tokens += int(line.split("=")[1].rstrip())
                elif line.startswith("**duration**"):
                    time += float(line.split("=")[1].rstrip("s\n"))
    
    result_dict[project][bug_id].update({"cost": cost,
                                         "total_tokens": total_tokens,
                                         "time": time})
    return result_dict

def save_to_csv(result_dict, d4j_version):
    eval_dir = "EvaluationResult"
    if not os.path.exists(eval_dir):
        os.mkdir(eval_dir)
    csv_file = os.path.join(eval_dir, f"{res_dir}.csv")
    f = open(csv_file, "w")
    items = ["project", "bug_id", "true_method", "method_rank", "recall_ratio", "false_positive", "cost", "total_tokens", "time"]
    f.write(",".join(items) + "\n")
    for project in D4J_ALL[d4j_version]:
        for bug_id in tqdm(range(D4J_ALL[d4j_version][project]["begin"],
                                 D4J_ALL[d4j_version][project]["end"] + 1),
                           desc=f"Saving {project}"):
            if bug_id in D4J_ALL[d4j_version][project]["deprecate"]:
                continue
            if str(bug_id) not in result_dict[project]:
                print(f"Warning: Result of {project}-{bug_id} not exists!")
                continue
            string = project + "," + str(bug_id) + ","
            for item in items[2:]:
                string += str(result_dict[project][str(bug_id)][item]) + ","
            else:
                string = string.rstrip(",")
            f.write(string + "\n")
    f.close()

def main(res_dir, config):
    result_dict = defaultdict(dict)
    for bug_res in tqdm(os.listdir(res_dir), desc=f"Evaluating {res_dir}"):
        bug_res_dir = os.path.join(res_dir, bug_res)
        ckpt_dir = os.path.join(bug_res_dir, "checkpoint")
        d4j_version, project, bug_id = bug_res.split("-")
        d4j_version = d4j_version.replace("d4j", "")
        res_file = os.path.join(bug_res_dir, "result.json")

        # make sure that the chain is finished
        if not os.path.exists(ckpt_dir):
            print(f"Warning: {ckpt_dir} not exists!")
        else:
            for test_suite in os.listdir(ckpt_dir):
                test_suite_dir = os.path.join(ckpt_dir, test_suite)
                if len(os.listdir(test_suite_dir)) < N_PHASES[config]:
                    print(f"Warning: {test_suite_dir} not finished!")
        if not os.path.exists(res_file):
            print(f"Warning: {res_file} not exists, skip!")
            continue
        
        test_failure_file = os.path.join(bug_res_dir, "test_failure.pkl")
        info_files = []
        for file in os.listdir(bug_res_dir):
            if file.startswith("post_info") and os.path.isfile(os.path.join(bug_res_dir, file)):
                info_files.append(os.path.join(bug_res_dir, file))
        
        # Get metrics
        result_dict = get_metrics(project, bug_id, result_dict, res_file, test_failure_file)
        
        # Get post info
        result_dict = get_post_info(project, bug_id, result_dict, info_files)
    
    # Save to csv
    save_to_csv(result_dict, d4j_version)

if __name__ == "__main__":
    res_dir = "DebugResult_APRContest"
    config = "Default"
    main(res_dir, config)