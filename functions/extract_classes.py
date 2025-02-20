import os
import subprocess as sp
from functools import reduce
from typing import List


def extract_classes(proj_name, bug_id, test_suite, repo_dir, agent_jar):
    """Extract classes for a test suite (witch may contains multiple test methods)"""

    cwd = os.path.dirname(os.path.abspath(__file__))
    buggy_dir = os.path.join(repo_dir, proj_name, str(bug_id), "buggy")
    tmp_dir = os.path.join(cwd, "tmp")
    os.chdir(buggy_dir)

    loaded_classes = []
    covered_classes = []
    test_suite_name = test_suite[0].split("::")[0]
    print(f"[solving {proj_name}-{bug_id}-{test_suite_name}]")
    for test_name in test_suite:
        print(f"    <extracting classes for {proj_name}-{bug_id}-{test_name}>")
        test_tmp_dir = os.path.join(cwd, tmp_dir, f"tmp_{proj_name}_{bug_id}_{test_name}")
        inst_log = os.path.join(test_tmp_dir, "inst.log")
        run_log = os.path.join(test_tmp_dir, "run.log")
        # print(test_tmp_dir)
        run_instrument(proj_name, bug_id, test_name, buggy_dir, test_tmp_dir, agent_jar)
        class_list, covered_class_list = analyse_coverage(inst_log, run_log)
        loaded_classes.append(class_list)
        if len(covered_class_list) > 0:
            covered_classes.append(covered_class_list)

    # classes intersection
    if len(covered_classes) > 0:
        if len(test_suite) > 1:
            print(f"    <classes intersection for test suite {proj_name}-{bug_id}-{test_suite_name}>")
            extracted_classes = covered_classes
            extracted_classes = [[c.class_name for c in x] for x in extracted_classes]
            extracted_classes = reduce(lambda x, y: set(x).intersection(set(y)), extracted_classes)
            extracted_classes = list(extracted_classes)
        else: 
            print(f"    <test suite with single failed test {proj_name}-{bug_id}-{test_suite_name}>")
            extracted_classes = covered_classes[0]
            extracted_classes = [c.class_name for c in extracted_classes]
    else:
        extracted_classes = []
    
    p = os.popen("git checkout . && git clean -xdf").read()
    os.chdir(cwd)
    cmd = "rm -rf tmp"
    os.system(cmd)
    return loaded_classes, covered_classes, extracted_classes

def extract_classes_statistic(proj_name, bug_id, test_suite, repo_dir, agent_jar, max_num=30, sub_proj=None):
    """Extract classes for a test suite (witch may contains multiple test methods)"""

    cwd = os.path.dirname(os.path.abspath(__file__))
    buggy_dir = os.path.join(repo_dir, proj_name, str(bug_id), "buggy")
    if sub_proj:
        buggy_dir = os.path.join(buggy_dir, sub_proj)
    tmp_dir = os.path.join(cwd, "tmp")
    os.chdir(buggy_dir)

    loaded_classes = []
    covered_classes = []
    test_suite_name = test_suite[0].split("::")[0]
    print(f"[solving {proj_name}-{bug_id}-{test_suite_name}]")
    for test_name in test_suite:
        print(f"    <extracting classes for {proj_name}-{bug_id}-{test_name}>")
        test_tmp_dir = os.path.join(cwd, tmp_dir, f"tmp_{proj_name}_{bug_id}_{test_name}")
        inst_log = os.path.join(test_tmp_dir, "inst.log")
        run_log = os.path.join(test_tmp_dir, "run.log")
        # print(test_tmp_dir)
        run_instrument(proj_name, bug_id, test_name, buggy_dir, test_tmp_dir, agent_jar)
        class_list, covered_class_list = analyse_coverage(inst_log, run_log)
        loaded_classes.append(class_list)
        if len(covered_class_list) > 0:
            covered_classes.append(covered_class_list)

    # classes intersection
    if len(covered_classes) > 0:
        if len(test_suite) > 1:
            print(f"    <classes intersection for test suite {proj_name}-{bug_id}-{test_suite_name}>")
            extracted_classes = [x[:max_num] for x in covered_classes]
            extracted_classes = [[c.class_name for c in x] for x in extracted_classes]
            extracted_classes = reduce(lambda x, y: set(x).intersection(set(y)), extracted_classes)
            extracted_classes = list(extracted_classes)
        else: 
            print(f"    <test suite with single failed test {proj_name}-{bug_id}-{test_suite_name}>")
            extracted_classes = covered_classes[0][:max_num]
            extracted_classes = [c.class_name for c in extracted_classes]
    else:
        extracted_classes = []
    
    p = os.popen("git checkout . && git clean -xdf").read()
    os.chdir(cwd)
    # cmd = "rm -rf tmp"
    # os.system(cmd)
    return loaded_classes, covered_classes, extracted_classes

def run_instrument(proj_name, bug_id, test_name, buggy_dir, tmp_dir, agent_jar):
    os.makedirs(tmp_dir, exist_ok=True)
    log = ""

    os.chdir(buggy_dir)
    cmd1 = f"defects4j export -p dir.bin.classes"
    p = sp.Popen(cmd1.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    output, err = p.communicate()
    out = output.decode("utf-8")
    err = err.decode("utf-8")
    log = log + err + out + "\n"
    classes_dir = out
    assert classes_dir != "", f"[{proj_name}-{bug_id}-{test_name}] get classes dir error:\n" + log

    if not os.path.exists(os.path.join(buggy_dir, classes_dir)):
        cmd2 = f"defects4j compile"
        p = sp.Popen(cmd2.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
        output, err = p.communicate()
    
    cmd3 = f"defects4j test -n -t {test_name} -a -Djvmargs=-javaagent:{agent_jar}=outputDir={tmp_dir},classesPath={classes_dir}"
    print(cmd3)
    p = sp.Popen(cmd3.split(" "), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    output, err = p.communicate()
    out = output.decode("utf-8")
    err = err.decode("utf-8")
    log = log + err + out + "\n"
    return log


class JavaMethod:
    def __init__(self, class_name, method_name):
        self.class_name = class_name
        self.method_name = method_name
        self._covered = False

    def set_covered(self):
        self._covered = True


class JavaClass:
    def __init__(self, class_name):
        self.class_name = class_name
        self.methods = {}

    def add_methods(self, method: JavaMethod):
        self.methods[method.method_name] = method

    def statistic(self):
        n_covered_methods = 0
        for method in self.methods.values():
            if method._covered:
                n_covered_methods += 1
        self.n_covered_methods = n_covered_methods
        self.n_all_methods = len(self.methods)
        self.porpotion = self.n_covered_methods / self.n_all_methods * 100


def analyse_coverage(inst_file, run_file) -> List[JavaClass]:
    assert os.path.exists(inst_file), f"Error: No instrument file:\n"
    classes_dict = {}

    # parse instrumentation file
    with open(inst_file, "r") as f:
        for line in f:
            if line is None:
                continue
            line = line.strip()
            class_name, method, return_type = line.split(" ")
            if "$" in class_name:
                idx = class_name.index("$")
                inner_class_name = class_name[idx:]
                class_name = class_name.split("$")[0]
                method = inner_class_name + "." + method
            java_method = JavaMethod(class_name, method)
            if class_name not in classes_dict:
                classes_dict[class_name] = JavaClass(class_name)
            classes_dict[class_name].add_methods(java_method)

    if os.path.exists(run_file):
        # parse method run file
        with open(run_file, "r") as f:
            for line in f:
                if line is None:
                    continue
                line = line.strip()
                class_name, method, return_type = line.split(" ")
                if "$" in class_name:
                    idx = class_name.index("$")
                    inner_class_name = class_name[idx:]
                    class_name = class_name.split("$")[0]
                    method = inner_class_name + "." + method
                if class_name not in classes_dict:
                    raise Exception(f"{class_name} not in inst file")
                if method not in classes_dict[class_name].methods:
                    raise Exception(f"{class_name} {method} not in inst file")
                java_method = classes_dict[class_name].methods[method]
                if java_method._covered is False:
                    java_method.set_covered()

    # statistics
    for class_name in classes_dict:
        classes_dict[class_name].statistic()
    class_list = [c for c in classes_dict.values()]
    class_list.sort(key=lambda x: x.porpotion, reverse=True)
    covered_classes = [c for c in class_list if c.n_covered_methods > 0]
    return class_list, covered_classes


def test_inst():
    run_instrument(
        "Closure",
        4,
        "com.google.javascript.jscomp.TypeCheckTest::testConversionFromInterfaceToRecursiveConstructor",
        "/home/qyh/projects/LLM-Location/preprocess/Defects4J-1.2.0",
        "/home/qyh/projects/LLM-Location/preprocess/classtracer/target/classtracer-1.0.jar",
    )


def test_cvg():
    inst_file = "/home/qyh/projects/LLM-Location/Functions/tmp_Closure_4_com.google.javascript.jscomp.TypeCheckTest::testConversionFromInterfaceToRecursiveConstructor/inst.log"
    run_file = "/home/qyh/projects/LLM-Location/Functions/tmp_Closure_4_com.google.javascript.jscomp.TypeCheckTest::testConversionFromInterfaceToRecursiveConstructor/run.log"
    analyse_coverage(inst_file, run_file)


def test_extract():
    extract_classes(
        "Closure",
        2,
        [
            "com.google.javascript.jscomp.TypeCheckTest::testBadInterfaceExtendsNonExistentInterfaces",
        ],
        "/home/qyh/projects/LLM-Location/preprocess/Defects4J-1.2.0",
        "/home/qyh/projects/LLM-Location/preprocess/classtracer/target/classtracer-1.0.jar",
    )


if __name__ == "__main__":
    # test_inst()
    # test_cvg()
    test_extract()
