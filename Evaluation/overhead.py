from collections import defaultdict

res_file = "../EvaluationResult/DebugResult_d4j140_GPT35.csv"
res = defaultdict(dict)
top_n = {}

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, _, _, _, _, cost, tokens, time= line.strip().split(",")
        res[proj][bug_id] = {"cost": float(cost), "tokens": int(tokens), "time": float(time)}

for proj in res:
    if proj not in top_n:
        top_n[proj] = {"cost": 0, "tokens": 0, "time": 0}
    for bug_id in res[proj]:
        top_n[proj]["cost"] += res[proj][bug_id]["cost"]
        top_n[proj]["tokens"] += res[proj][bug_id]["tokens"]
        top_n[proj]["time"] += res[proj][bug_id]["time"]
    
    top_n[proj]["cost"] = top_n[proj]["cost"] / len(res[proj])
    top_n[proj]["tokens"] = top_n[proj]["tokens"] / len(res[proj])
    top_n[proj]["time"] = top_n[proj]["time"] / len(res[proj])

print(top_n)