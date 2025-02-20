import json
import os
import re
import shutil
import signal
import subprocess
import time
from typing import Dict, Tuple

import openai
import requests

from chatdev.codes import Codes
from chatdev.documents import Documents
from chatdev.roster import Roster
from chatdev.utils import log_online


class ChatEnvConfig:
    def __init__(self,
                 config_name,
                 clear_structure,
                 brainstorming,
                 gui_design,
                 git_management,
                 num_test_cases,
                 num_test_suites,
                 num_classes,
                 test_output_tokens,
                 class_doc_tokens,
                 method_doc_tokens,
                 num_selected_classes,
                 basement):
        self.config_name = config_name
        self.clear_structure = clear_structure
        self.brainstorming = brainstorming
        self.gui_design = gui_design
        self.git_management = git_management
        self.num_test_cases = num_test_cases
        self.num_test_suites = num_test_suites
        self.num_classes = num_classes
        self.test_output_tokens = test_output_tokens
        self.class_doc_tokens = class_doc_tokens
        self.method_doc_tokens = method_doc_tokens
        self.num_selected_classes = num_selected_classes
        self.basement = basement

    def __str__(self):
        string = ""
        string += "ChatEnvConfig.clear_structure: {}\n".format(self.clear_structure)
        string += "ChatEnvConfig.brainstorming: {}\n".format(self.brainstorming)
        string += "ChatEnvConfig.num_test_cases: {}\n".format(self.num_test_cases)
        string += "ChatEnvConfig.num_test_suites: {}\n".format(self.num_test_suites)
        string += "ChatEnvConfig.num_classes: {}\n".format(self.num_classes)
        string += "ChatEnvConfig.test_output_tokens: {}\n".format(self.test_output_tokens)
        string += "ChatEnvConfig.class_doc_tokens: {}\n".format(self.class_doc_tokens)
        string += "ChatEnvConfig.method_doc_tokens: {}\n".format(self.method_doc_tokens)
        string += "ChatEnvConfig.num_selected_classes: {}\n".format(self.num_selected_classes)
        string += "ChatEnvConfig.basement: {}\n".format(self.basement)
        return string


class ChatEnv:
    def __init__(self, chat_env_config: ChatEnvConfig):
        self.config = chat_env_config
        self.roster: Roster = Roster()
        self.codes: Codes = Codes()
        self.proposed_images: Dict[str, str] = {}
        self.incorporated_images: Dict[str, str] = {}
        self.requirements: Documents = Documents()
        self.manuals: Documents = Documents()
        self.if_run_search = True
        self.res_dict = {
            "buggy_classes": [],
            "buggy_methods": [],  # buggy methods for all test suites
            "buggy_codes":{}  # buggy codes for all test suites, remove duplicates
        }
        self.reset_dict()
    
    def reset_dict(self):
        self.env_dict = {
            "d4j_version": "",
            "project_name": "",
            "bug_ID": "",
            "test_infos": "",
            "failed_tests": "",
            "test_codes": "",
            "test_behavior": "",
            "test_failure_causes": "",
            "classes_dict": {},
            "suspicious_classes": [],
            "suspicious_methods": {},
            "directory": ""
        }

    @staticmethod
    def fix_module_not_found_error(test_reports):
        if "ModuleNotFoundError" in test_reports:
            for match in re.finditer(r"No module named '(\S+)'", test_reports, re.DOTALL):
                module = match.group(1)
                subprocess.Popen("pip install {}".format(module), shell=True).wait()
                log_online("**[CMD Execute]**\n\n[CMD] pip install {}".format(module))

    def set_directory(self, directory):
        self.env_dict['directory'] = directory
        self.codes.directory = directory
        self.requirements.directory = directory
        self.manuals.directory = directory

    def exist_bugs(self) -> Tuple[bool, str]:
        directory = self.env_dict['directory']

        success_info = "The software run successfully without errors."
        try:

            # check if we are on windows or linux
            if os.name == 'nt':
                command = "cd {} && dir && python main.py".format(directory)
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                command = "cd {}; ls -l; python3 main.py;".format(directory)
                process = subprocess.Popen(command,
                                           shell=True,
                                           preexec_fn=os.setsid,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE
                                           )
            time.sleep(3)
            return_code = process.returncode
            # Check if the software is still running
            if process.poll() is None:
                if "killpg" in dir(os):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    os.kill(process.pid, signal.SIGTERM)
                    if process.poll() is None:
                        os.kill(process.pid,signal.CTRL_BREAK_EVENT)

            if return_code == 0:
                return False, success_info
            else:
                error_output = process.stderr.read().decode('utf-8')
                if error_output:
                    if "Traceback".lower() in error_output.lower():
                        errs = error_output.replace(directory + "/", "")
                        return True, errs
                else:
                    return False, success_info
        except subprocess.CalledProcessError as e:
            return True, f"Error: {e}"
        except Exception as ex:
            return True, f"An error occurred: {ex}"

        return False, success_info

    def recruit(self, agent_name: str):
        self.roster._recruit(agent_name)

    def exist_employee(self, agent_name: str) -> bool:
        return self.roster._exist_employee(agent_name)

    def print_employees(self):
        self.roster._print_employees()

    def update_codes(self, generated_content):
        self.codes._update_codes(generated_content)

    def rewrite_codes(self) -> None:
        self.codes._rewrite_codes(self.config.git_management)

    def get_codes(self) -> str:
        return self.codes._get_codes()

    def _load_from_hardware(self, directory) -> None:
        self.codes._load_from_hardware(directory)

    def _update_requirements(self, generated_content):
        self.requirements._update_docs(generated_content)

    def rewrite_requirements(self):
        self.requirements._rewrite_docs()

    def get_requirements(self) -> str:
        return self.requirements._get_docs()

    def _update_manuals(self, generated_content):
        self.manuals._update_docs(generated_content, parse=False, predifined_filename="manual.md")

    def rewrite_manuals(self):
        self.manuals._rewrite_docs()

    def write_result(self) -> None:
        directory = self.env_dict['directory']

        if not os.path.exists(directory):
            os.mkdir(directory)
            print("{} Created.".format(directory))

        result_filename = "result.json"
        if len(self.res_dict['buggy_methods']) > 0:
            with open(os.path.join(directory, result_filename), "w", encoding="utf-8") as writer:
                json.dump(self.res_dict, writer, indent=4)
        print(os.path.join(directory, result_filename), "Wrote")

    def generate_images_from_codes(self):
        def download(img_url, file_name):
            r = requests.get(img_url)
            filepath = os.path.join(self.env_dict['directory'], file_name)
            if os.path.exists(filepath):
                os.remove(filepath)
            with open(filepath, "wb") as f:
                f.write(r.content)
                print("{} Downloaded".format(filepath))

        regex = r"(\w+.png)"
        joined_codes = self.get_codes()
        matches = re.finditer(regex, joined_codes, re.DOTALL)
        # matched_images = {}
        for match in matches:
            filename = match.group(1).strip()
            if filename in self.proposed_images.keys():
                self.incorporated_images[filename] = self.proposed_images[filename]
            else:
                self.incorporated_images[filename] = filename.replace("_", " ")

        for filename in self.incorporated_images.keys():
            if not os.path.exists(os.path.join(self.env_dict['directory'], filename)):
                desc = self.incorporated_images[filename]
                if desc.endswith(".png"):
                    desc = desc.replace(".png", "")
                print("{}: {}".format(filename, desc))
                response = openai.Image.create(
                    prompt=desc,
                    n=1,
                    size="256x256"
                )
                image_url = response['data'][0]['url']
                download(image_url, filename)

    def get_proposed_images_from_message(self, messages):
        def download(img_url, file_name):
            r = requests.get(img_url)
            filepath = os.path.join(self.env_dict['directory'], file_name)
            if os.path.exists(filepath):
                os.remove(filepath)
            with open(filepath, "wb") as f:
                f.write(r.content)
                print("{} Downloaded".format(filepath))

        regex = r"(\w+.png):(.*?)\n"
        matches = re.finditer(regex, messages, re.DOTALL)
        images = {}
        for match in matches:
            filename = match.group(1).strip()
            desc = match.group(2).strip()
            images[filename] = desc

        if len(images.keys()) == 0:
            regex = r"(\w+.png)"
            matches = re.finditer(regex, messages, re.DOTALL)
            images = {}
            for match in matches:
                filename = match.group(1).strip()
                desc = " ".join(filename.replace(".png", "").split("_"))
                images[filename] = desc
                print("{}: {}".format(filename, images[filename]))

        for filename in images.keys():
            if not os.path.exists(os.path.join(self.env_dict['directory'], filename)):
                desc = images[filename]
                if desc.endswith(".png"):
                    desc = desc.replace(".png", "")
                print("{}: {}".format(filename, desc))
                response = openai.Image.create(
                    prompt=desc,
                    n=1,
                    size="256x256"
                )
                image_url = response['data'][0]['url']
                download(image_url, filename)

        return images
