import copy
import json
import os
import re
import sys
from functools import reduce
from typing import Dict, List, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatdev.test_suite import (
    TestCase,
    TestFailure,
    TestMethod,
    TestSuite,
    TestUtilityMethod,
)
from functions.line_parser import (
    JavaClass,
    JavaMethod,
    parse_coverage,
    parse_stack_trace,
    parse_test_report,
    parse_test_run_log,
)
from functions.methodExtractor import (
    FunctionsExtractor,
    get_all_methods,
    get_buggy_methods,
    get_class_doc,
)
from functions.utils import clean_doc, git_clean, run_cmd

filepath = os.path.dirname(__file__)
TREE_SITTER_LIB_PATH = os.path.join(
    filepath, "methodExtractor/myparser/my-languages.so")
root = os.path.dirname(filepath)
directory = os.path.join(root, "DebugResult")
agent_jar = os.path.join(root, "functions/classtracer/target/classtracer-1.0.jar")

D4J_EXEC = {
    "d4j1.4.0": "/home/qyh/DATASET/defects4j-2.0.1/framework/bin/defects4j",
    "d4j2.0.1": "/home/qyh/DATASET/defects4j-2.0.1/framework/bin/defects4j",
    "GrowingBugs": "/root/APR/GrowingBugRepository-6.1/framework/bin/defects4j"
}



def check_out(version, project, bugID, subproj, project_path=None):
    cwd = os.getcwd()
    if project_path is None:
        project_path = os.path.join(directory, f"d4j{version}-{project}-{bugID}")
    os.makedirs(project_path, exist_ok=True)
    os.chdir(project_path)
    if not os.path.exists("buggy"):
        if subproj:
            run_cmd(f"{D4J_EXEC[version]} checkout -p {project} -v {bugID}b -w buggy -s {subproj}")
        else:
            run_cmd(f"{D4J_EXEC[version]} checkout -p {project} -v {bugID}b -w buggy")
    if not os.path.exists("fixed"):
        if subproj:
            run_cmd(f"{D4J_EXEC[version]} checkout -p {project} -v {bugID}f -w fixed -s {subproj}")
        else:
            run_cmd(f"{D4J_EXEC[version]} checkout -p {project} -v {bugID}f -w fixed")
    os.chdir(cwd)


# def run_single_test(test_name, buggy_path, test_tmp_dir):
#     test_output_file = os.path.join(test_tmp_dir, "test_output.txt")
#     stack_trace_file = os.path.join(test_tmp_dir, "stack_trace.txt")
#     if os.path.exists(test_output_file) and os.path.exists(stack_trace_file):
#         print("test already run")
#         with open(test_output_file, "r") as f:
#             test_output = f.readlines()
#         with open(stack_trace_file, "r") as f:
#             stack_trace = f.readlines()
#         return test_output, stack_trace
#     run_cmd(f"{D4J_EXEC} compile -w {buggy_path}")
#     cmd = f"timeout 90 {D4J_EXEC} test -n -t {test_name} -w {buggy_path}"
#     run_cmd(cmd)
#     with open(f"{buggy_path}/failing_tests", "r") as f:
#         test_res = f.readlines()
#     test_output, stack_trace = parse_test_report(test_res)
#     with open(test_output_file, "w") as f:
#         f.writelines(test_output)
#     with open(stack_trace_file, "w") as f:
#         f.writelines(stack_trace)
#     git_clean(buggy_path)
#     return test_output, stack_trace


def get_modified_methods(buggy_path, src_path, modified_classes):
    buggy_method_names = []
    function_extractor = FunctionsExtractor(TREE_SITTER_LIB_PATH, ["java"])
    for class_name in modified_classes:
        buggy_file = os.path.join(
            buggy_path,
            src_path,
            class_name.replace(".", "/") + ".java",
        )

        fixed_file = os.path.join(
            buggy_path.replace("buggy", "fixed"),
            src_path,
            class_name.replace(".", "/") + ".java",
        )
        if not (os.path.exists(fixed_file) and os.path.exists(buggy_file)):
            print(f"Warning: {fixed_file} or {buggy_file} not exists.")
            continue
        
        pkgname = ".".join(class_name.split(".")[:-1])
        try:
            buggy_code = open(buggy_file, "r").readlines()
        except UnicodeDecodeError:
            print(f"Warning: UnicodeDecodeError for {buggy_file}.")
            buggy_code = open(buggy_file, "r", errors="ignore").readlines()
        try:
            fixed_code = open(fixed_file, "r").readlines()
        except UnicodeDecodeError:
            print(f"Warning: UnicodeDecodeError for {fixed_file}.")
            fixed_code = open(fixed_file, "r", errors="ignore").readlines()
        buggy_methods = get_buggy_methods(function_extractor, buggy_code, fixed_code, "java")
        for buggy_method in buggy_methods:
            full_name = pkgname + "." + buggy_method.class_name + "::" + buggy_method.name + buggy_method.args
            buggy_method_names.append(full_name)
    return buggy_method_names

def get_modified_methods_with_labels(buggy_path, src_path, modified_classes):
    buggy_method_names = []
    function_extractor = FunctionsExtractor(TREE_SITTER_LIB_PATH, ["java"])
    for class_name in modified_classes:
        buggy_file = os.path.join(
            buggy_path,
            src_path,
            class_name.replace(".", "/") + ".java",
        )

        fixed_file = os.path.join(
            buggy_path.replace("buggy", "fixed"),
            src_path,
            class_name.replace(".", "/") + ".java",
        )
        if not (os.path.exists(fixed_file) and os.path.exists(buggy_file)):
            print(f"Warning: {fixed_file} or {buggy_file} not exists.")
            continue
        
        pkgname = ".".join(class_name.split(".")[:-1])
        try:
            buggy_code = open(buggy_file, "r").readlines()
        except UnicodeDecodeError:
            print(f"Warning: UnicodeDecodeError for {buggy_file}.")
            buggy_code = open(buggy_file, "r", errors="ignore").readlines()
        try:
            fixed_code = open(fixed_file, "r").readlines()
        except UnicodeDecodeError:
            print(f"Warning: UnicodeDecodeError for {fixed_file}.")
            fixed_code = open(fixed_file, "r", errors="ignore").readlines()
        buggy_methods = get_buggy_methods(function_extractor, buggy_code, fixed_code, "java")
    return buggy_methods

def get_test_code(buggy_path, src_path, runed_methods, stack_trace):
    # parse runed_methods to find the test methods need to be extracted
    run_log_methods = parse_test_run_log(runed_methods)

    # parse stack_trace to find test suite need to be extracted
    test_method_name, test_suites, file_path, location = parse_stack_trace(stack_trace)

    # find test method and test utility methods
    test_utility_methods = []
    for clazz in test_suites:
        clazz_name = clazz.split(".")[-1]

        # get test file path
        outer_clazz = clazz.split("$")[0] if "$" in clazz else clazz  # consider inner class
        test_file = os.path.join(buggy_path, src_path, outer_clazz.replace(".", "/") + ".java")
        if not os.path.exists(test_file):
            continue

        # extract methods
        try:
            code = open(test_file, "r").readlines()
        except UnicodeDecodeError as e:
            print(f"Warning: UnicodeDecodeError for {test_file}.")
            code = open(test_file, "r", errors="ignore").readlines()
        function_extractor = FunctionsExtractor(TREE_SITTER_LIB_PATH, ["java"])
        methods = get_all_methods(function_extractor, code, "java")
        for method in methods:
            signature = method.name + method.args
            if method.name == test_method_name and clazz_name == method.class_name:  # test method
                method_code = method.code
                if location != -1:
                    code_line = code[location-1].strip("\n")
                    method_code = method_code.replace(
                        code_line, code_line + " // error occurred here")
                test_method = TestMethod(
                    method.name, clazz, signature, method_code, method.comment)
            else:  # test utility method
                if clazz in run_log_methods:
                    if signature in run_log_methods[clazz]:
                        test_utility_method = TestUtilityMethod(method.name,
                                                                clazz,
                                                                signature,
                                                                method.code,
                                                                method.comment)
                        test_utility_methods.append(test_utility_method)

    return test_method, test_utility_methods


def run_instrument(version, test_name, buggy_dir, tmp_dir, agent_jar, mode="src"):
    
    log = ""
    
    if mode == "src":
        property = "dir.bin.classes"
    elif mode == "test":
        property = "dir.bin.tests"
    else:
        raise RuntimeError(
            f"Unknown mode: {mode}, should be one of ['src', 'test']")
    
    inst_log = os.path.join(tmp_dir, f"inst_{mode}.log")
    run_log = os.path.join(tmp_dir, f"run_{mode}.log")
    if os.path.exists(inst_log) and os.path.exists(run_log):
        print("instrumentation already done")
        return log

    os.makedirs(tmp_dir, exist_ok=True)

    try:
        cmd1 = f"{D4J_EXEC[version]} export -p {property} -w {buggy_dir}"
        out, err = run_cmd(cmd1)
        log = log + out + err
        classes_dir = os.path.join(buggy_dir, out)
    except Exception as e:
        raise RuntimeError(f"Failed to export \"{property}\" for {buggy_dir}, {e}")

    run_cmd(f"{D4J_EXEC[version]} compile -w {buggy_dir}")
    cmd2 = f"{D4J_EXEC[version]} test -n -w {buggy_dir} -t {test_name} -a -Djvmargs=-javaagent:{agent_jar}=outputDir={tmp_dir},classesPath={classes_dir}"
    out, err = run_cmd(cmd2)
    log = log + out + err
    
    if os.path.exists(os.path.join(tmp_dir, "run.log")):
        os.rename(os.path.join(tmp_dir, "run.log"), run_log)
    if os.path.exists(os.path.join(tmp_dir, "inst.log")):
        os.rename(os.path.join(tmp_dir, "inst.log"), inst_log)
    
    return log


# def refine_failed_tests(version, project, bugID):
#     import pickle
#     project_path = os.path.join("/home/qyh/projects/LLM-Location/AgentFL/DebugResult_d4j140_GPT35", f"d4j{version}-{project}-{bugID}")
#     pickle_file = os.path.join(project_path, "test_failure.pkl")
#     with open(pickle_file, "rb") as f:
#         test_failure = pickle.load(f)
    
#     check_out_path = os.path.join(project_path, "refine_check_out")
#     check_out(version, project, bugID, check_out_path)
#     buggy_path = os.path.join(check_out_path, "buggy")
    
#     cmd = f"{D4J_EXEC} export -p dir.src.classes -w {buggy_path}"
#     src_path, err = run_cmd(cmd)
    
#     cmd = f"{D4J_EXEC} export -p classes.modified -w {buggy_path}"
#     out, err = run_cmd(cmd)
#     modified_classes = out.split("\n")
    
#     buggy_methods = get_modified_methods(buggy_path, src_path, modified_classes)  # for evaluation
#     test_failure.buggy_methods = buggy_methods
    
#     with open(pickle_file, "wb") as f:
#         pickle.dump(test_failure, f)
    
#     run_cmd(f"rm -rf {check_out_path}")


def get_failed_tests(version, project, bugID, subproj) -> TestFailure:
    """Get the TestFailure object for a defect4j bug.
    """

    project_path = os.path.join(directory, f"d4j{version}-{project}-{bugID}")
    if subproj:
        buggy_path = os.path.join(project_path, "buggy", subproj)
    else:
        buggy_path = os.path.join(project_path, "buggy")
    tmp_path = os.path.join(project_path, "tmp")

    # get properties
    cmd = f"{D4J_EXEC[version]} export -p tests.trigger -w {buggy_path}"
    out, err = run_cmd(cmd)
    test_names = out.split("\n")

    cmd = f"{D4J_EXEC[version]} export -p dir.src.classes -w {buggy_path}"
    src_path, err = run_cmd(cmd)

    cmd = f"{D4J_EXEC[version]} export -p dir.src.tests -w {buggy_path}"
    test_path, err = run_cmd(cmd)

    cmd = f"{D4J_EXEC[version]} export -p classes.modified -w {buggy_path}"
    out, err = run_cmd(cmd)
    modified_classes = out.split("\n")

    # initialize test failure
    test_suites = {}
    for test_name in test_names:
        suite_name = test_name.split("::")[0]
        if suite_name not in test_suites:
            test_suites[suite_name] = TestSuite(
                suite_name, [TestCase(test_name)])
        else:
            test_suites[suite_name].test_cases.append(TestCase(test_name))

    buggy_methods = get_modified_methods(buggy_path, src_path, modified_classes)  # for evaluation
    test_failure = TestFailure(project, bugID, list(test_suites.values()), buggy_methods)

    # gather information for each single test case
    for test_suite in test_failure.test_suites:
        for test_case in test_suite.test_cases:
            test_name = test_case.name
            print(f"<run instrumentation for {project}-{bugID}-{test_name}>")
            test_tmp_dir = os.path.join(tmp_path, test_suite.name, test_name)
            os.makedirs(test_tmp_dir, exist_ok=True)

            # run test with instrumentation
            run_instrument(version, test_name, buggy_path, test_tmp_dir, agent_jar, mode="test")

            test_output_file = os.path.join(test_tmp_dir, "test_output.txt")
            stack_trace_file = os.path.join(test_tmp_dir, "stack_trace.txt")
            if os.path.exists(test_output_file) and os.path.exists(stack_trace_file):
                print("test already run")
                with open(test_output_file, "r") as f:
                    test_output = f.readlines()
                with open(stack_trace_file, "r") as f:
                    stack_trace = f.readlines()
            else:
                with open(f"{buggy_path}/failing_tests", "r") as f:
                    test_res = f.readlines()
                test_output, stack_trace = parse_test_report(test_res)
                with open(test_output_file, "w") as f:
                    f.writelines(test_output)
                with open(stack_trace_file, "w") as f:
                    f.writelines(stack_trace)
            git_clean(buggy_path)
            
            # find all related test code
            run_log_file = os.path.join(test_tmp_dir, "run_test.log")
            with open(run_log_file, "r") as f:
                runed_methods = f.readlines()
            test_method, test_utility_methods = get_test_code(buggy_path, test_path, runed_methods, stack_trace)
            test_case.test_method = test_method
            test_case.test_utility_methods = test_utility_methods

    return test_failure


def get_classes_code(classes: List[JavaClass], src_path, buggy_path) -> List[JavaClass]:
    need_delete = []
    for clazz in classes:
        outer_class_name = clazz.class_name.split(".")[-1]
        prefix = clazz.class_name.replace(outer_class_name, "")
        java_file = os.path.join(buggy_path, src_path, clazz.class_name.replace(".", "/") + ".java")
        if not os.path.exists(java_file):
            need_delete.append(clazz)
            continue

        try:
            code = open(java_file, "r").readlines()
        except UnicodeDecodeError:
            print(f"Warning: UnicodeDecodeError for {java_file}.")
            code = open(java_file, "r", errors="ignore").readlines()

        function_extractor = FunctionsExtractor(TREE_SITTER_LIB_PATH, ["java"])
        
        # get class documetation
        origin_doc = get_class_doc(function_extractor, code, "java", outer_class_name)
        cleaned_doc = clean_doc(origin_doc)
        clazz.doc = cleaned_doc
        
        # get source methods documentation and code
        src_methods = get_all_methods(function_extractor, code, "java")
        src_methods = {prefix + m.class_name + "::" + m.name + m.args : m for m in src_methods}
        should_delete_ids = []
        for inst_id in clazz.methods:
            if inst_id in src_methods:
                # in this situation the method id is the same both in instrument result and source code
                # e.g., inst_sig: com.google.javascript.jscomp.PeepholeOptimizationsPass::visit(Node) 
                #        src_sig: com.google.javascript.jscomp.PeepholeOptimizationsPass::visit(Node)
                clazz.methods[inst_id].src_sig = clazz.methods[inst_id].inst_sig
                clazz.methods[inst_id].src_id = inst_id
                clazz.methods[inst_id].code = src_methods[inst_id].code
                clazz.methods[inst_id].doc = clean_doc(src_methods[inst_id].comment)
            else:
                # - case 1: this method not exists in source code, no "Object" in inst_id, e.g.,
                #           com.google.javascript.jscomp.parsing.Config$LanguageMode::values()
                #           com.google.javascript.jscomp.parsing.Config$LanguageMode::valueOf(String)
                #           com.google.javascript.rhino.jstype.JSTypeRegistry$1::getConstructor()
                # - case 2: this method exists in source code but the id is different, there is "Object" in inst_id, e.g.,
                #           inst_id: (1) com.google.javascript.jscomp.graph.FixedPointGraphTraversal::computeFixedPoint(DiGraph,Object) // here
                #                    (2) com.google.javascript.jscomp.graph.FixedPointGraphTraversal::computeFixedPoint(DiGraph,Set)
                #            src_id: (1) com.google.javascript.jscomp.graph.FixedPointGraphTraversal::computeFixedPoint(DiGraph,N) // here
                #                    (2) com.google.javascript.jscomp.graph.FixedPointGraphTraversal::computeFixedPoint(DiGraph,Set)
                # - case 3: this method not exists in source code but there is "Object" in inst_id, e.g.,
                #           com.google.javascript.jscomp.ComposeWarningsGuard$GuardComparator::compare(Object,Object)
                #           com.google.javascript.jscomp.DiagnosticType::compareTo(Object)
                #           com.google.javascript.rhino.jstype.PropertyMap$1::apply(Object)
                
                # solve case 2
                if "Object" in inst_id:
                    pattern = r"{}".format(inst_id.replace("$", "\$")
                                                  .replace(".", "\.")
                                                  .replace("(", "\(")
                                                  .replace("[", "\[")
                                                  .replace("]", "\]")
                                                  .replace(")", "\)")
                                                  .replace("Object", ".+"))
                    for src_id in src_methods:
                        if re.match(pattern, src_id) and src_id not in clazz.methods:
                            clazz.methods[inst_id].src_sig = src_id.split("::")[-1]
                            clazz.methods[inst_id].src_id = src_id
                            clazz.methods[inst_id].code = src_methods[src_id].code
                            clazz.methods[inst_id].doc = clean_doc(src_methods[src_id].comment)
                            break
                    # solve case 3
                    else:
                        should_delete_ids.append(inst_id)
                # solve case 1
                else:
                    should_delete_ids.append(inst_id)
        
        # delete methods not exists in source code
        for inst_id in should_delete_ids:
            del clazz.methods[inst_id]
        
        # check all source code have been found
        for inst_id in clazz.methods:
            assert clazz.methods[inst_id].code is not None, f"Error: No source code found for method {inst_id}"

    for clazz in need_delete:
        classes.remove(clazz)
    return classes


def merge_classes(class_name: str, covered_classes: List[Dict[str, JavaClass]]) -> JavaClass:
    merged_class = JavaClass(class_name)
    all_covered_methods = [[m for m in c[class_name].methods.values() if m._covered] for c in covered_classes]
    spc_methods = {}
    for covered_methods in all_covered_methods:
        for method in covered_methods:
            if method.inst_id not in spc_methods:
                spc_methods[method.inst_id] = method
    if len(spc_methods) == 0:  # no suspicious methods, which means nether of the methods in the class can be buggy
        return None
    merged_class.methods = spc_methods
    return merged_class


def filter_classes_Ochiai(project, bugID, extracted_classes: List[JavaClass]) -> List[JavaClass]:
    """
    Filter the classes according to the top 20 result of Ochiai (https://github.com/Instein98/D4jOchiai).
    """
    def parse_ochiai(path):
        """
        Parse the Ochiai result from line level to method level.
        """
        res = []
        with open(path, "r") as f:
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
                if len(res) == 20:
                    break
                line = f.readline()
        return res
    
    ochiai_res_path = os.path.join("functions/OchiaiResult", project, str(bugID), "ochiai.ranking.csv")
    if not os.path.exists(ochiai_res_path):
        print(f"Warning: No Ochiai result for {project}-{bugID}")
        return []
    ochiai_res = parse_ochiai(ochiai_res_path)
    filtered_classes = []
    bug_result_dict = {}
    for m in ochiai_res:
        class_name = m.split("#")[0].replace("$", ".")
        method_name = m.split("#")[1].split("(")[0]
        if class_name not in bug_result_dict:
            bug_result_dict[class_name] = [method_name]
        else:
            if method_name not in bug_result_dict[class_name]:
                bug_result_dict[class_name].append(method_name)
    
    # filter out useless classes and methods
    for javaclass in extracted_classes:
        if javaclass.class_name in bug_result_dict:
            new_javaclass = copy.deepcopy(javaclass)
            for inst_id in javaclass.methods:
                inst_method_name = inst_id.split("::")[1].split("(")[0]
                if inst_method_name not in bug_result_dict[javaclass.class_name]:
                    new_javaclass.methods.pop(inst_id)
            filtered_classes.append(new_javaclass)
    return filtered_classes


def filter_classes_Grace(project, bugID, extracted_classes: List[JavaClass]) -> List[JavaClass]:
    """
    Filter the classes according to the top 10 result of Grace (https://github.com/yilinglou/Grace/tree/master).
    """
    filtered_classes = []
    with open("functions/grace_result_dict.json", "r") as f:
        grace_result = json.load(f)
    if str(bugID) not in grace_result[project]:
        print(f"Warning: No Grace result for {project}-{bugID}")
        return filtered_classes
    bug_result = grace_result[project][str(bugID)]["top10_result"]
    bug_result_dict = {}
    for m in bug_result:
        class_name = m.split(":")[0].split("$")[0]
        method_name = m.split(":")[1].split("(")[0]
        if class_name not in bug_result_dict:
            bug_result_dict[class_name] = [method_name]
        else:
            if method_name not in bug_result_dict[class_name]:
                bug_result_dict[class_name].append(method_name)
    
    # filter out useless classes and methods
    for javaclass in extracted_classes:
        if javaclass.class_name in bug_result_dict:
            new_javaclass = copy.deepcopy(javaclass)
            for inst_id in javaclass.methods:
                inst_method_name = inst_id.split("::")[1].split("(")[0]
                if inst_method_name not in bug_result_dict[javaclass.class_name]:
                    new_javaclass.methods.pop(inst_id)
            filtered_classes.append(new_javaclass)
    return filtered_classes


def extract_classes(
    version, project, bugID, subproj, test_suite: TestSuite, max_num=50
) -> Tuple[List[List[JavaClass]], List[List[JavaClass]], List[JavaClass]]:
    """
    Extract loaded java classes for a test suite (witch may contains multiple test methods)
    according to the method coverage information.
    """

    project_path = os.path.join(directory, f"d4j{version}-{project}-{bugID}")
    if subproj:
        buggy_path = os.path.join(project_path, "buggy", subproj)
    else:
        buggy_path = os.path.join(project_path, "buggy")
    tmp_path = os.path.join(project_path, "tmp")

    cmd = f"{D4J_EXEC[version]} export -p dir.src.classes -w {buggy_path}"
    src_path, err = run_cmd(cmd)

    loaded_classes = []
    covered_classes = []
    test_suite_name = test_suite.name
    print(f"[extracting classes for test suite {project}-{bugID}-{test_suite_name}...]")
    for test_case in test_suite.test_cases:
        test_name = test_case.name
        print(f"  <{project}-{bugID}-{test_name}>")
        test_tmp_dir = os.path.join(tmp_path, test_suite.name, test_name)
        os.makedirs(test_tmp_dir, exist_ok=True)
        inst_log = os.path.join(test_tmp_dir, "inst_src.log")
        run_log = os.path.join(test_tmp_dir, "run_src.log")
        
        run_instrument(test_name, buggy_path, test_tmp_dir, agent_jar, mode="src")
        class_list, covered_class_list = parse_coverage(inst_log, run_log)
        loaded_classes.append(class_list)
        if len(covered_class_list) == 0:
            print(f"Warning: No covered classes found for test {test_name}")
        covered_classes.append({c.class_name : c for c in covered_class_list})

    # classes selection
    extracted_classes = []
    if len(test_suite.test_cases) > 1:
        print(f"<classes intersection for multiple failed test cases...>")
        try:
            common_class_names = reduce(lambda x, y: set(x).intersection(set(y)),
                                        [list(c.keys()) for c in covered_classes if len(c) > 0])
            common_class_names = list(common_class_names)
        except TypeError:
            common_class_names = []
            print(f"Warning: skip classes intersection")

        extracted_class_names = set(common_class_names[:max_num])
        extra_class_names = get_class_name_from_msg(tmp_path, test_suite)
        for i in extra_class_names:
            for j in common_class_names:
                if (i in j) and (j not in extracted_class_names):
                    extracted_class_names.add(j)
        extracted_class_names = list(extracted_class_names)
        for class_name in extracted_class_names:
            merged_class = merge_classes(class_name, covered_classes)
            if merged_class is not None:
                extracted_classes.append(merged_class)
    else:
        print(f"<classes selection for single failed test...>")
        class_names = list(covered_classes[0].keys())
        extracted_class_names = set(class_names[:max_num])
        extra_class_names = get_class_name_from_msg(tmp_path, test_suite)
        for i in extra_class_names:
            for j in class_names:
                if (i in j.split(".")[-1]) and (j not in extracted_class_names):
                    extracted_class_names.add(j)
        extracted_class_names = list(extracted_class_names)
        for class_name in extracted_class_names:
            merged_class = merge_classes(class_name, covered_classes)
            if merged_class is not None:
                extracted_classes.append(merged_class)

    # get doc for extracted classes and code + doc for methods
    extracted_classes = get_classes_code(extracted_classes, src_path, buggy_path)

    return loaded_classes, covered_classes, extracted_classes


def get_class_name_from_msg(tmp_path, test_suite):
    """
    Some buggy classes may have low method level coverage proportion rank because of the crash, 
    so we add these classes according to the error messages.
    """
    
    def get_target_classes(match):
        target_classes = []
        class_name = match.split(".")[-1]
        class_names = re.findall(r"[A-Z][a-zA-Z0-9]*", class_name)
        for class_name in class_names:
            if "Tests" in class_name:
                target_classes.append(class_name.replace("Tests", ""))
            elif "Test" in class_name:
                target_classes.append(class_name.replace("Test", ""))
            else:
                target_classes.append(class_name)
        return target_classes
    
    extra_class_names = set()
    for test_case in test_suite.test_cases:
        test_name = test_case.name
        test_tmp_dir = os.path.join(tmp_path, test_suite.name, test_name)
        stack_trace_file = os.path.join(test_tmp_dir, "stack_trace.txt")
        with open(stack_trace_file, "r") as f:
            stack_trace = f.read()
        matches = re.findall(r'\b(?:\w*\.)+[A-Z]\w*', stack_trace)
        matches = list(set(matches))
        candidates = []
        for match in matches:
            candidates.extend(get_target_classes(match))
        for candidate in candidates:
            extra_class_names.add(candidate)
    return list(extra_class_names)


def test():
    check_out("2.0.0", "Closure", "2")
    test_failure = get_failed_tests("2.0.0", "Closure", "2")
    loaded_classes, covered_classes, extracted_classes = extract_classes(
        "2.0.0", "Closure", "2", test_failure.test_suites[0])
    print("over")


if __name__ == "__main__":
    test()
    # refine_failed_tests("1.4.0", "Mockito", "30")
