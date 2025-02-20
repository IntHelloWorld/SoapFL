from collections import defaultdict

# res_file = "../EvaluationResult/DebugResult_d4j140_GPT35.csv"
res_file = "EvaluationResult/Default_d4j140_GPT4o.csv"
output_file = "EvaluationResult/Top1_Default.csv"

top_1 = []

with open(res_file, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tm, mr, rr, fp, _, _, _= line.strip().split(",")
        if int(tm) == 1:
            top_1.append(f"{proj}-{bug_id}")

with open(output_file, "w") as f:
    f.write("\n".join(top_1))