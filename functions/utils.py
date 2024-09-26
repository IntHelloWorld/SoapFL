import os
import re
import subprocess as sp


def run_cmd(cmd: str):
    print("-" * 50)
    print(f"run command: {cmd}")
    p = sp.Popen(cmd.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    output, err = p.communicate()
    out = output.decode("utf-8")
    err = err.decode("utf-8")
    print(err)
    print(out)
    print("-" * 50)
    return out, err

def git_clean(git_dir):
    cwd = os.getcwd()
    os.chdir(git_dir)
    run_cmd("git checkout . && git clean -xdf")
    os.chdir(cwd)

def clean_doc(doc: str) -> str:
    """
    Turn multi-line doc into one line.
    """
    new_doc_lines = []
    doc_lines = doc.split("\n")
    for doc_line in doc_lines:
        doc_str =  re.match(r"^([/\s\*]*)(.*)", doc_line)
        if doc_str is not None:
            line = doc_str.group(2)
            if not line.startswith("@author"):
                new_doc_lines.append(line)
    return " ".join(new_doc_lines)
