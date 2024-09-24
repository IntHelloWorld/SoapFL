from collections import defaultdict

# res_file = "../EvaluationResult/DebugResult_d4j140_GPT35.csv"
res_file = "EvaluationResult/DebugResult_BaseOnGrace.csv"

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tm, mr, rr, fp, _, _, _= line.strip().split(",")
        if int(tm) == 1:
            print(f"{proj}-{bug_id}")