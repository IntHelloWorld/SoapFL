from collections import defaultdict

# res_file = "EvaluationResult/DebugResult_d4j140_GPT35.csv"
# res_file = "EvaluationResult/DebugResult_d4j200_GPT35.csv"
# res_file = "EvaluationResult/DebugResult_NoTestBehaviorAnalysis.csv"
# res_file = "EvaluationResult/DebugResult_NoMethodDocEnhancement.csv"
# res_file = "EvaluationResult/DebugResult_NoTestFailureAnalysis.csv"
# res_file = "EvaluationResult/DebugResult_Baseline.csv"
# res_file = "EvaluationResult/DebugResult_BaseOnGrace.csv"
res_file = "EvaluationResult/Default_d4j140_GPT4o.csv"
# res_file = "EvaluationResult/Default_d4j140_GPT35_TURBO.csv"
# res_file = "EvaluationResult/BaseOnGrace_d4j140_GPT4o.csv"
# res_file = "EvaluationResult/Default_d4j200_GPT4o.csv"


# res_file = "EvaluationResult/NoMultipleMethodReview_d4j140_GPT4o.csv"
# res_file = "EvaluationResult/NoMethodDocEnhancement_d4j140_GPT4o.csv"
# res_file = "EvaluationResult/NoMethodDoc_d4j140_GPT4o.csv"
# res_file = "EvaluationResult/NoTestBehaviorAnalysis_d4j140_GPT4o.csv"
# res_file = "EvaluationResult/NoTestFailureAnalysis_d4j140_GPT4o.csv"

res = defaultdict(dict)
top_n = {}
top_5_bugs = []

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tc, tm, mr, rr, fp, _, _, _= line.strip().split(",")
        res[proj][bug_id] = {"tc": tc, "tm": tm, "mr": mr, "rr": rr, "fp": fp}

for proj in res:
    if proj not in top_n:
        top_n[proj] = {"t1": 0, "t3": 0, "t5": 0, "class_level": 0}
    for bug_id in res[proj]:
        # if int(res[proj][bug_id]["tm"]) == 1:
        #     top_n[proj]["t1"] += 1
        
        if int(res[proj][bug_id]["tc"]) == 1:
            top_n[proj]["class_level"] += 1
        
        if res[proj][bug_id]["mr"] == "N/A":
            continue
        
        if int(res[proj][bug_id]["mr"]) == 1:
            top_n[proj]["t1"] += 1
        if int(res[proj][bug_id]["mr"]) <= 3:
            top_n[proj]["t3"] += 1
        if int(res[proj][bug_id]["mr"]) <= 5:
            top_n[proj]["t5"] += 1
            top_5_bugs.append(f"{proj}-{bug_id}")

print(top_n)

top1_total = 0
top3_total = 0
top5_total = 0
for proj in top_n:
    top1_total += top_n[proj]["t1"]
    top3_total += top_n[proj]["t3"]
    top5_total += top_n[proj]["t5"]
print(f"Total top1:{top1_total}, top3:{top3_total}, top5:{top5_total}")

with open("EvaluationResult/Top5Bugs.txt", "w") as f:
    for bug in top_5_bugs:
        f.write(f"{bug}\n")