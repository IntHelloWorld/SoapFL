import pickle
from collections import defaultdict

res_dir = "../DebugResult_BaseOnOchiai"
res_file = "../EvaluationResult/DebugResult_BaseOnOchiai.csv"
ochiai_dir = "../functions/OchiaiResult"
res = defaultdict(dict)
top_n = {}

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tm, mr, rr, fp, _, _, _= line.strip().split(",")
        res[proj][bug_id] = {"tm": tm, "mr": mr, "rr": rr, "fp": fp}

def get_ochiai_rank(ochiai_file, test_failure_file):
    res = []
    with open(ochiai_file, "r") as f:
        line = f.readline()
        line = f.readline()
        while line:
            name, _ = line.split(";")
            name = name.split(":")[0]
            if res == []:
                res.append(name)
            else:
                if name != res[-1]:
                    res.append(name)
            if len(res) == 10:
                break
            line = f.readline()
    
    test_failure = pickle.load(open(test_failure_file, "rb"))

for proj in res:
    if proj not in top_n:
        top_n[proj] = {"t1": 0, "t3": 0, "t5": 0}
    for bug_id in res[proj]:
        if res[proj][bug_id]["mr"] == "N/A" and res[proj][bug_id]["fp"] == 0:
            rank = get_ochiai_rank(f"{ochiai_dir}/{proj}/{bug_id}/ochiai.ranking.csv",
                                   f"{res_dir}/d4j1.4.0-{proj}-{bug_id}/test_failure.pkl")
            if rank == 1:
                top_n[proj]["t1"] += 1
            elif rank <= 3:
                top_n[proj]["t3"] += 1
            elif rank <= 5:
                top_n[proj]["t5"] += 1
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