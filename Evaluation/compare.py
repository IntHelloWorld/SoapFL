f1 = "/home/qyh/projects/LLM-Location/AgentFL/EvaluationResult/DebugResult_d4j140_GPT35.csv"
f2 = "/home/qyh/projects/LLM-Location/AgentFL/EvaluationResult/results_analysis_3_5_turbo_human.csv"
res1 = {}
with open(f1, "r") as f:
    for line in f.readlines()[1:]:
        proj, bug_id, tm, mr, rr, fp, _, _, _ = line.strip().split(",")
        res1[f"{proj}-{bug_id}"] = {"tm": tm, "mr": mr, "rr": rr, "fp": fp}

res2 = {}
with open(f2, "r") as f2:
    for line in f2.readlines()[1:]:
        proj, bug_id, tm, mr, rr, fp = line.strip().split(",")
        res2[f"{proj}-{bug_id}"] = {"tm": tm, "mr": mr, "rr": rr, "fp": fp}

for k in res1:
    assert k in res2
    if res1[k] != res2[k]:
        print(k, res1[k], res2[k])