# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import argparse
import logging
import os
import pickle
import random
import sys

from camel.typing import ModelType
from functions.d4j import check_out, get_failed_tests
from functions.generate_dataset import make_fix_dataset

root = os.path.dirname(__file__)
sys.path.append(root)

from chatdev.chat_chain import ChatChain


def get_config(company):
    """
    return configuration json files for ChatChain
    user can customize only parts of configuration json files, other files will be left for default
    Args:
        company: customized configuration name under Config/

    Returns:
        path to three configuration jsons: [config_path, config_phase_path, config_role_path]
    """
    config_dir = os.path.join(root, "Config", company)
    default_config_dir = os.path.join(root, "Config", "Default")

    config_files = [
        "ChatChainConfig.json",
        "PhaseConfig.json",
        "RoleConfig.json"
    ]

    config_paths = []

    for config_file in config_files:
        company_config_path = os.path.join(config_dir, config_file)
        default_config_path = os.path.join(default_config_dir, config_file)

        if os.path.exists(company_config_path):
            config_paths.append(company_config_path)
        else:
            config_paths.append(default_config_path)

    return tuple(config_paths)

def main():
    parser = argparse.ArgumentParser(description='argparse')
    parser.add_argument('--config', type=str, default="Default",
                        help="Name of config, which is used to load configuration under Config/")
    parser.add_argument('--version', type=str, default="1.4.0",
                        help="Version of defects4j")
    parser.add_argument('--project', type=str, default="Closure",
                        help="Name of project, your debug result will be generated in DebugResult/d4jversion_project_bugID")
    parser.add_argument('--bugID', type=int, default=1,
                        help="Prompt of software")
    parser.add_argument('--subproj', type=str, required=False, default="",
                        help="The subproject of the project")
    parser.add_argument('--model', type=str, default="DeepSeek",
                        help="GPT Model, choose from {'GPT_3_5_TURBO','GPT_4','GPT_4_32K', 'DeepSeek'}")
    args = parser.parse_args()

    # Start DebugDev
    print("*" * 100)
    print(f"Start DebugDev for d4j{args.version}-{args.project}-{args.bugID}")

    # ----------------------------------------
    #          Init Test Failure
    # ----------------------------------------
    
    project_path = os.path.join(root, "DebugResult", f"d4j{args.version}-{args.project}-{args.bugID}")
    res_file = os.path.join(project_path, "result.json")
    dataset_file = os.path.join(project_path, "dataset_for_fix.json")
    if os.path.exists(dataset_file):
        print(f"d4j{args.version}-{args.project}-{args.bugID} already finished, skip!")
        return
    
    check_out(args.version, args.project, args.bugID, args.subproj)
    print(f"Checkout successfully!")
    
    pkl_file = os.path.join(project_path, "test_failure.pkl")
    if os.path.exists(pkl_file):
        with open(pkl_file, "rb") as f:
            failed_tests = pickle.load(f)
            print(f"Load failed tests from {pkl_file}")
    else:
        failed_tests = get_failed_tests(args.version, args.project, args.bugID, args.subproj)
        with open(pkl_file, "wb") as f:
            pickle.dump(failed_tests, f)
        print(f"Save failed tests to {pkl_file}")
    
    # ----------------------------------------
    #          Init ChatChain
    # ----------------------------------------
    
    config_path, config_phase_path, config_role_path = get_config(args.config)
    args2type = {
        'GPT_3_5_TURBO': ModelType.GPT_3_5_TURBO,
        'GPT_4': ModelType.GPT_4,
        'GPT_4_32K': ModelType.GPT_4_32k,
        'DeepSeek': ModelType.DEEPSEEK
        }
    chat_chain = ChatChain(config_path=config_path,
                           config_phase_path=config_phase_path,
                           config_role_path=config_role_path,
                           d4j_version=args.version,
                           project_name=args.project,
                           bug_ID=args.bugID,
                           subproj=args.subproj,
                           model_type=args2type[args.model])
    
    # ----------------------------------------
    #          Init Log
    # ----------------------------------------
    logging.basicConfig(filename=chat_chain.log_filepath, level=logging.INFO,
                        format='[%(asctime)s %(levelname)s] %(message)s',
                        datefmt='%Y-%d-%m %H:%M:%S')

    # ----------------------------------------
    #          Run ChatChain for each test suite
    # ----------------------------------------

    for test_suite in failed_tests.test_suites:
        print("-" * 100)

        # ----------------------------------------
        #      Set Test Suite and Test Cases
        # ----------------------------------------
        
        chat_chain.test_suite = test_suite
        print(f"Start DebugDev for test suite {chat_chain.test_suite.name}...")
        
        num_test_cases = chat_chain.chat_env.config.num_test_cases
        if len(test_suite.test_cases) > num_test_cases:
            chat_chain.test_cases = random.sample(test_suite.test_cases, num_test_cases)
            print(f"Test cases {len(test_suite.test_cases)} => {num_test_cases}")
        else:
            chat_chain.test_cases = test_suite.test_cases
            print(f"Test cases {len(test_suite.test_cases)}")

        # ----------------------------------------
        #          Pre Processing
        # ----------------------------------------

        chat_chain.pre_processing()
        print(f"Pre processing finished!")

        # ----------------------------------------
        #          Personnel Recruitment
        # ----------------------------------------

        chat_chain.make_recruitment()
        print(f"Employees recruitment finished!")

        # ----------------------------------------
        #          Chat Chain
        # ----------------------------------------

        chat_chain.execute_chain()
        print("-" * 100)
    
    # ----------------------------------------
    #        Get Top1 Suspicious Method
    # ----------------------------------------

    chat_chain.execute_get_top1_phase()
    
    make_fix_dataset(chat_chain, failed_tests)
    
    # ----------------------------------------
    #          Post Processing
    # ----------------------------------------

    chat_chain.post_processing()
    print(f"Post processing finished!")
    print("*" * 100)

if __name__ == "__main__":
    main()
