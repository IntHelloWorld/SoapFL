import os
import pickle
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

res_dir = "DebugResult_d4j140_GPT35"
res = defaultdict(dict)
n_utility_methods = {}

for bug_dir in os.listdir(res_dir):
    bug_res_dir = os.path.join(res_dir, bug_dir)
    proj = bug_dir.split("-")[1]
    if proj not in n_utility_methods:
        n_utility_methods[proj] = {"n_test_cases":0, "n_utility_methods":0, "avg":0}
    pkl_file = os.path.join(bug_res_dir, "test_failure.pkl")
    with open(pkl_file, "rb") as f:
        test_failure = pickle.load(f)
    for test_suite in test_failure.test_suites:
        for test_case in test_suite.test_cases:
            n_utility_methods[proj]["n_test_cases"] += 1
            n_utility_methods[proj]["n_utility_methods"] += len(test_case.test_utility_methods)

all_test_cases = 0
all_utility_methods = 0
for proj in n_utility_methods:
    all_test_cases += n_utility_methods[proj]["n_test_cases"]
    all_utility_methods += n_utility_methods[proj]["n_utility_methods"]
    n_utility_methods[proj]["avg"] = n_utility_methods[proj]["n_utility_methods"] / n_utility_methods[proj]["n_test_cases"]

print(n_utility_methods)
print("all_test_cases:", all_test_cases, "all_utility_methods:", all_utility_methods, "avg:", all_utility_methods / all_test_cases)