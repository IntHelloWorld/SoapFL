import os
import subprocess

from joblib import Parallel, delayed

D4J_LLMAO = {
    "1.4.0": {
        # "Chart": {
        #     "begin": 1,
        #     "end": 26,
        #     "deprecate": [23]
        # },
        # "Closure": {
        #     "begin": 1,
        #     "end": 133,
        #     "deprecate": [63, 93]
        # },
        # "Lang": {
        #     "begin": 1,
        #     "end": 65,
        #     "deprecate": [2]
        # },
        # "Math": {
        #     "begin": 1,
        #     "end": 106,
        #     "deprecate": []
        # },
        # "Time": {
        #     "begin": 1,
        #     "end": 27,
        #     "deprecate": [21]
        # },
        "Mockito": {
            "begin": 1,
            "end": 38,
            "deprecate": []
        },
    },
}

D4J = {
    "1.4.0": {
        "Time": {
            "begin": 1,
            "end": 27,
            "deprecate": [21]
        },
        "Chart": {
            "begin":1,
            "end": 26,
            "deprecate": []
        },
        "Lang": {
            "begin": 1,
            "end": 65,
            "deprecate": [2, 18, 25, 48]
        },
        "Mockito": {
            "begin": 1,
            "end": 38,
            "deprecate": []
        },
        "Math": {
            "begin": 1,
            "end": 106,
            "deprecate": []
        },
        "Closure": {
            "begin": 1,
            "end": 133,
            "deprecate": [63, 93]
        }
    },
    # "2.0.0": {
    #     "Cli": {
    #         "begin": 1,
    #         "end": 40,
    #         "deprecate": [6]
    #     },
    #     "Closure": {
    #         "begin": 134,
    #         "end": 176,
    #         "deprecate": []
    #     },
    #     "Codec": {
    #         "begin": 1,
    #         "end": 18,
    #         "deprecate": []
    #     },
    #     "Collections": {
    #         "begin": 25,
    #         "end": 28,
    #         "deprecate": []
    #     },
    #     "Compress": {
    #         "begin": 1,
    #         "end": 47,
    #         "deprecate": []
    #     },
    #     "Csv": {
    #         "begin": 1,
    #         "end": 16,
    #         "deprecate": []
    #     },
    #     # "Gson": {
    #     #     "begin": 1,
    #     #     "end": 18,
    #     #     "deprecate": []
    #     # },
    #     # "JacksonCore": {
    #     #     "begin": 1,
    #     #     "end": 26,
    #     #     "deprecate": []
    #     # },
    #     "JacksonDatabind": {
    #         "begin": 1,
    #         "end": 112,
    #         "deprecate": []
    #     },
    #     "JacksonXml": {
    #         "begin": 1,
    #         "end": 6,
    #         "deprecate": []
    #     },
    #     "Jsoup": {
    #         "begin": 46,
    #         "end": 93,
    #         "deprecate": []
    #     },
    #     "JxPath": {
    #         "begin": 1,
    #         "end": 22,
    #         "deprecate": []
    #     },
    # }
}

# D4J = {
#     "1.4.0": {
#         "Time": {
#             "begin": 22,
#             "end": 22,
#             "deprecate": [21]
#         }
#     }
# }
# D4J = {
#     "1.4.0": {
#         "Chart": {
#             "begin":1,
#             "end": 26,
#             "deprecate": []
#         }
#     }
# }
# D4J = {
#     "1.4.0": {
#         "Lang": {
#             "begin": 1,
#             "end": 65,
#             "deprecate": [2, 18, 25, 48]
#         }
#     }
# }
# D4J = {
#     "1.4.0": {
#         "Mockito": {
#             "begin": 1,
#             "end": 38,
#             "deprecate": []
#         }
#     }
# }
# D4J = {
#     "1.4.0": {
#         "Math": {
#             "begin": 1,
#             "end": 106,
#             "deprecate": []
#         }
#     }
# }
# D4J = {
#     "1.4.0": {
#         "Closure": {
#             "begin": 45,
#             "end": 45,
#             "deprecate": [63, 93]
#         }
#     }
# }

def run_single_project(version, proj, bug_id, config, model, output_dir):
    cmd = f"python3 run.py --config {config} --version {version} --project {proj} --bugID {bug_id} --model {model} --output {output_dir}"
    result = subprocess.run(cmd.split(" "))
    return result.returncode

def run_project(config, model, output_dir, num_jobs=None):
    jobs = []
    for version in D4J:
        for proj in D4J[version]:
            for bug_id in range(D4J[version][proj]["begin"], D4J[version][proj]["end"] + 1):
                if bug_id in D4J[version][proj]["deprecate"]:
                    continue
                res_file = f"{output_dir}/d4j{version}-{proj}-{bug_id}/result.json"
                if os.path.exists(res_file):
                    print(f"d4j{version}-{proj}-{bug_id} already finished, skip!")
                    continue
                jobs.append((version, proj, bug_id, config, model, output_dir))
                
    results = Parallel(n_jobs=num_jobs)(
        delayed(run_single_project)(version, proj, bug_id, config, model, output_dir) 
        for version, proj, bug_id, config, model, output_dir in jobs
    )
    
    if any(rc != 0 for rc in results if rc is not None):
        print("Some tasks failed!")
        return False
    return True

def run_single():
    cmd = f"python run.py --config Default --version 1.4.0 --project Closure --bugID 26 --model GPT_3_5_TURBO --output Default_d4j140_GPT35_TURBO"
    result = subprocess.run(cmd.split(" "))
    if result.returncode != 0:
        return

if __name__ == "__main__":
    
    # config = "BaseOnGrace"
    # model = "GPT_3_5_TURBO"
    # output_dir = "BaseOnGrace_d4j140_GPT35_TURBO"
    
    config = "Default"
    model = "GPT_3_5_TURBO"
    output_dir = "Default_d4j140_GPT35_TURBO"
    
    # config = "NoMultipleMethodReview"
    # model = "GPT_3_5_TURBO"
    # output_dir = "results/NoMultipleMethodReview_d4j140_GPT35_TURBO"
    
    # config = "NoMethodDoc"
    # model = "GPT_3_5_TURBO"
    # output_dir = "results/NoMethodDoc_d4j140_GPT35_TURBO"
    
    # config = "NoMethodDocEnhancement"
    # model = "GPT_3_5_TURBO"
    # output_dir = "results/NoMethodDocEnhancement_d4j140_GPT35_TURBO"
    
    # config = "NoTestBehaviorAnalysis"
    # model = "GPT_3_5_TURBO"
    # output_dir = "results/NoTestBehaviorAnalysis_d4j140_GPT35_TURBO"
    
    # config = "NoTestFailureAnalysis"
    # model = "GPT_3_5_TURBO"
    # output_dir = "results/NoTestFailureAnalysis_d4j140_GPT35_TURBO"
    
    num_jobs = 8
    success = run_project(config, model, output_dir, num_jobs)
    if not success:
        print("Project execution failed")
    # run_single()