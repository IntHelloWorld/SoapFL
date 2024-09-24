from collections import defaultdict

res_file = "../EvaluationResult/DebugResult_d4j140_GPT35_human.csv"
res = defaultdict(dict)
top_n = {}

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tm, he, mr, rr, fp= line.strip().split(",")
        res[proj][bug_id] = {"tm": tm, "mr": mr, "rr": rr, "fp": fp, "he": he}

for proj in res:
    if proj not in top_n:
        top_n[proj] = {"t1": 0, "t3": 0, "t5": 0, "human": 0}
    for bug_id in res[proj]:
        if int(res[proj][bug_id]["tm"]) == 1:
            top_n[proj]["t1"] += 1
        if int(res[proj][bug_id]["he"]) == 1:
            top_n[proj]["human"] += 1
        if res[proj][bug_id]["mr"] == "N/A":
            continue
        if int(res[proj][bug_id]["mr"]) <= 3:
            top_n[proj]["t3"] += 1
        if int(res[proj][bug_id]["mr"]) <= 5:
            top_n[proj]["t5"] += 1

print(top_n)

top1_total = 0
top3_total = 0
top5_total = 0
human_total = 0
for proj in top_n:
    top1_total += top_n[proj]["t1"]
    top3_total += top_n[proj]["t3"]
    top5_total += top_n[proj]["t5"]
    human_total += top_n[proj]["human"]
print(f"Total top1:{top1_total}, top3:{top3_total}, top5:{top5_total}, human:{human_total}")