import json
import os
import pickle
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from run_all import D4J

AutoFL_top5_file = "/home/qyh/projects/LLM-Location/AgentFL/EvaluationResult/AutoFL_top_5.txt"
SoapFL_top5_file = "/home/qyh/projects/LLM-Location/AgentFL/EvaluationResult/Top5Bugs.txt"

success_AutoFL = []
with open(AutoFL_top5_file, "r") as f:
    for line in f.readlines():
        bug = line.strip()
        if bug != "":
            success_AutoFL.append(bug)

success_SoapFL = []
with open(SoapFL_top5_file, "r") as f:
    for line in f.readlines():
        bug = line.strip()
        if bug != "":
            success_SoapFL.append(bug)


human_AutoFL = {}
human_SoapFL = {}

new_success_AutoFL = []
new_success_SoapFL = []


def check_AutoFL(proj, bug_id, buggy_methods):
    res_file = f"/home/qyh/projects/autofl/results/d4j_autofl_1/gpt-3.5-turbo-1106/XFL-{proj}_{bug_id}.json"
    if not os.path.exists(res_file):
        return False
    raw_res = json.load(open(res_file, "r"))
    raw_response = raw_res["messages"][-1]["content"]
    predict_sigs = [s for s in raw_response.split("\n") if s != "" and s != "```"]
    predict_names = [s.split("(")[0].split(".")[-1] + "(" for s in predict_sigs]
    for method in buggy_methods:
        for name in predict_names:
            if name in method["snippet"]:
                return True
    return False


def check_SoapFL(proj, bug_id, buggy_methods):
    res_file = f"/home/qyh/projects/LLM-Location/AgentFL/results/Default_d4j140_GPT4o/d4j1.4.0-{proj}-{bug_id}/result.json"
    if not os.path.exists(res_file):
        return False
    raw_res = json.load(open(res_file, "r"))
    predict_methods = raw_res["buggy_methods"]
    predict_sigs = [s["method_name"] for s in predict_methods]
    predict_names = [s.split("::")[1].split("(")[0] + "(" for s in predict_sigs]
    for method in buggy_methods:
        for name in predict_names:
            if name in method["snippet"]:
                return True
    return False

for version in D4J:
    for proj in D4J[version]:
        for bug_id in range(D4J[version][proj]["begin"], D4J[version][proj]["end"] + 1):
            if bug_id in D4J[version][proj]["deprecate"]:
                continue
            
            snippets_file = f"/home/qyh/projects/autofl/data/defects4j/{proj}_{bug_id}/snippet.json"
            buggy_methods = []
            if os.path.exists(snippets_file):
                with open(snippets_file, "r") as f:
                    snippets = json.load(f)
                    for snippet in snippets:
                        if snippet["is_bug"]:
                            buggy_methods.append(snippet)
            
            bug_name = f"{proj}-{bug_id}"
            autofl_flag = False
            if bug_name in success_AutoFL:
                autofl_flag = True
            else:
                autofl_flag = check_AutoFL(proj, bug_id, buggy_methods)
            if autofl_flag:
                try:
                    human_AutoFL[proj] += 1
                except:
                    human_AutoFL[proj] = 1
            
            soapfl_flag = False
            if bug_name in success_SoapFL:
                soapfl_flag = True
            else:
                soapfl_flag = check_SoapFL(proj, bug_id, buggy_methods)
                if soapfl_flag:
                    new_success_SoapFL.append(bug_name)
            if soapfl_flag:
                try:
                    human_SoapFL[proj] += 1
                except:
                    human_SoapFL[proj] = 1

print(human_AutoFL)
print(human_SoapFL)
with open("EvaluationResult/new_success_SoapFL.txt", "w") as f:
    for bug in new_success_SoapFL:
        f.write(f"{bug}\n")