from collections import defaultdict

res_file = "../EvaluationResult/DebugResult_d4j140_GPT35.csv"
res = defaultdict(dict)
false_positive = {}

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, _, mr, _, fp, _, _, _= line.strip().split(",")
        if mr == "N/A":
            res[proj][bug_id] = int(fp)

for proj in res:
    if proj not in false_positive:
        false_positive[proj] = 0
    for bug_id in res[proj]:
        false_positive[proj] += res[proj][bug_id]
    false_positive[proj] = false_positive[proj] / len(res[proj])

print(false_positive)