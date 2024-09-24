import json
from collections import defaultdict

# res_file = "EvaluationResult/DebugResult_d4j200_GPT35.csv"
# res_file = "EvaluationResult/DebugResult_NoTestBehaviorAnalysis.csv"
# res_file = "EvaluationResult/DebugResult_NoMethodDocEnhancement.csv"
res_file = "EvaluationResult/DebugResult.csv"
grace_result = "functions/grace_result_dict.json"
res = defaultdict(dict)
top_n = {}

with open(grace_result, "r") as f:
    grace_res = json.load(f)

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tm, mr, rr, fp, _, _, _= line.strip().split(",")
        res[proj][bug_id] = {"tm": tm, "mr": mr, "rr": rr, "fp": fp}

for proj in res:
    if proj not in top_n:
        top_n[proj] = {"t1": 0, "t3": 0, "t5": 0}
    for bug_id in res[proj]:
        if res[proj][bug_id]["mr"] == "N/A" and res[proj][bug_id]["fp"] == '0':
            if bug_id in grace_res[proj]:
                rank = grace_res[proj][bug_id]["rank"]
                if rank == 1:
                    top_n[proj]["t1"] += 1
                    print(proj, bug_id)
                elif rank <= 3:
                    top_n[proj]["t3"] += 1
                elif rank <= 5:
                    top_n[proj]["t5"] += 1
            continue
        if res[proj][bug_id]["mr"] == "N/A":
            continue
        if int(res[proj][bug_id]["tm"]) == 1:
            top_n[proj]["t1"] += 1
        if int(res[proj][bug_id]["mr"]) <= 3:
            top_n[proj]["t3"] += 1
        if int(res[proj][bug_id]["mr"]) <= 5:
            top_n[proj]["t5"] += 1

print(top_n)

top1_total = 0
top3_total = 0
top5_total = 0
for proj in top_n:
    top1_total += top_n[proj]["t1"]
    top3_total += top_n[proj]["t3"]
    top5_total += top_n[proj]["t5"]
print(f"Total top1:{top1_total}, top3:{top3_total}, top5:{top5_total}")