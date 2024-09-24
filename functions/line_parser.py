import os
import re
from typing import List, Optional


class JavaMethod:
    def __init__(self, class_name: str, inst_sig: str, inner: bool):
        self.class_name = class_name
        self.inst_sig = inst_sig
        self.inst_id = class_name + "::" + inst_sig
        self._inner = inner  # if the method is in an inner class
        self._covered = False
        
        self.src_sig = None
        self.src_id = None
        self.doc = ""
        self.enhanced_doc = ""
        self.code = None

    def set_covered(self):
        self._covered = True
    
    def __hash__(self) -> int:
        return hash(self.inst_id)

    def __eq__(self, other: object) -> bool:
        return self.inst_id == other.inst_id


class JavaClass:
    """
    Only for outer class, for inner class, we save its methods as the JavaMethod which name in
    format InnerClass1$InnerClass2.method_sig
    """

    def __init__(self, class_name):
        self.class_name = class_name
        self.methods = {}  # first extracted from instrument file, then enriched by source code
        self.doc = ""

    def add_methods(self, method: JavaMethod):
        self.methods[method.class_name + "::" + method.inst_sig] = method

    def statistic(self):
        n_covered_methods = 0
        for method in self.methods.values():
            if method._covered:
                n_covered_methods += 1
        self.n_covered_methods = n_covered_methods
        self.n_all_methods = len(self.methods)
        self.porpotion = self.n_covered_methods / self.n_all_methods * 100

    def __hash__(self) -> int:
        return hash(self.class_name)

    def __eq__(self, other: object) -> bool:
        return self.class_name == other.class_name


def parse_test_report(lines):
    """Seperate the raw test information into output and report."""
    output = []
    report = []
    test_method = lines[0].strip("\n").split("::")[1]
    flag = False  # for skipping the unrelated trace
    last_line = ""  # for skipping the infinite loop
    for i, line in enumerate(lines):
        if i < 2:
            report.append(line)
        elif line == last_line:
            continue
        elif line.startswith("\tat"):
            if not flag:
                report.append(line)
            if test_method in line:
                flag = True
        else:
            output.append(line)
        last_line = line
    return output, report


def parse_stack_trace(lines):
    """parse the bug error stack trace, find all test suites, e.g.:

    --- com.google.javascript.jscomp.TypeCheckTest::testBadInterfaceExtendsNonExistentInterfaces
    java.lang.NullPointerException
        at com.google.javascript.jscomp.TypeCheck.checkInterfaceConflictProperties(TypeCheck.java:1574)
        at com.google.javascript.jscomp.TypeCheck.visitFunction(TypeCheck.java:1664)
        at com.google.javascript.jscomp.TypeCheck.visit(TypeCheck.java:778)
        at com.google.javascript.jscomp.NodeTraversal.traverseBranch(NodeTraversal.java:505)
        at com.google.javascript.jscomp.NodeTraversal.traverseBranch(NodeTraversal.java:498)
        at com.google.javascript.jscomp.NodeTraversal.traverseWithScope(NodeTraversal.java:343)
        at com.google.javascript.jscomp.TypeCheck.check(TypeCheck.java:404)
        at com.google.javascript.jscomp.TypeCheck.process(TypeCheck.java:375)
        at com.google.javascript.jscomp.TypeCheck.processForTesting(TypeCheck.java:393)
        at com.google.javascript.jscomp.TypeCheckTest.testTypes(TypeCheckTest.java:11530)
        at com.google.javascript.jscomp.TypeCheckTest.testBadInterfaceExtendsNonExistentInterfaces(TypeCheckTest.java:3780)
    """
    test_suites = []
    test_method_name = ""
    location = -1
    file_path = ""
    for line in lines:
        if line.startswith("---"):
            _, clazz, test_method_name = re.split(r' |::', line.strip("\n"))
            test_suites.append(clazz)
        elif line.startswith("\tat"):
            method_full_name = re.search(r'at (.*)\(', line).group(1)
            method_name = method_full_name.split(".")[-1]
            clazz = ".".join(method_full_name.split(".")[:-1])
            if method_name == test_method_name:
                location = int(re.search(r':(\d+)', line).group(1))
                file_path = clazz.replace(".", "/") + ".java"
            if "Test" in clazz:
                if clazz not in test_suites:
                    test_suites.append(clazz)
    return test_method_name, test_suites, file_path, location


def parse_inst_method_sig(inst_method):
    """
    To match the code, parse the method signature in instrument file to expected format, e.g.:
    testTypes(java.lang.String,java.lang.String[]) -> testTypes(String,String[])
    
    We only focus on the coverage of source code methods, so if the method not exists in source code, return None, e.g.:
    access$100(com.google.javascript.rhino.Node) -> None
    """
    if re.match(r'access\$.*', inst_method):
        return None
    
    match = re.search(r'(.*)\((.*)\)', inst_method)
    method_name = match.group(1)
    params = match.group(2).split(",")

    new_params = []
    for param in params:
        new_param = param.replace("$", ".")  # ignore the inner class name
        new_param = new_param.split(".")[-1]  # ignore the package name
        if new_param == "LatticeElement":
            new_param = "L"
        new_params.append(new_param)
    simple_params = ",".join(new_params)
    method_sig = f"{method_name}({simple_params})"
    return method_sig


def parse_test_run_log(lines):
    """parse the method run log of test, find all runed methods, e.g.:

    com.google.javascript.jscomp.TypeCheckTest testBadInterfaceExtendsNonExistentInterfaces() void
    com.google.javascript.jscomp.TypeCheckTest testTypes(java.lang.String,java.lang.String[]) void
    com.google.javascript.jscomp.TypeCheckTest makeTypeCheck() com.google.javascript.jscomp.TypeCheck
    """
    methods = {}
    for line in lines:
        if line == "\n":
            continue
        clazz, method, _ = line.split(" ")
        method = parse_inst_method_sig(method)
        try:
            methods[clazz].append(method)
        except KeyError:
            methods[clazz] = [method]
    return methods


def parse_coverage(inst_file, run_file):
    assert os.path.exists(inst_file), "Error: No instrument file:\n"
    classes_dict = {}

    # parse instrumentation file
    with open(inst_file, "r") as f:
        for line in f:
            if line is None:
                continue
            line = line.strip()
            class_name, method, _ = line.split(" ")
            inner = True if "$" in class_name else False
            # add outer class
            outer_class_name = class_name.split("$")[0] if inner else class_name
            if outer_class_name not in classes_dict:
                classes_dict[outer_class_name] = JavaClass(outer_class_name)
            # add methods
            method_sig = parse_inst_method_sig(method)
            if method_sig:
                java_method = JavaMethod(class_name, method_sig, inner)
                classes_dict[outer_class_name].add_methods(java_method)

    if os.path.exists(run_file):
        # parse method run file
        with open(run_file, "r") as f:
            for line in f:
                if line is None:
                    continue
                line = line.strip()
                class_name, method, _ = line.split(" ")
                inner = True if "$" in class_name else False
                outer_class_name = class_name.split("$")[0] if inner else class_name
                method_sig = parse_inst_method_sig(method)
                if method_sig is None:
                    continue
                key = class_name + "::" + method_sig

                if outer_class_name not in classes_dict:
                    raise Exception(f"{outer_class_name} not in inst file")
                if key not in classes_dict[outer_class_name].methods:
                    raise Exception(
                        f"{key} not in inst file")
                java_method = classes_dict[outer_class_name].methods[key]
                if java_method._covered is False:
                    java_method.set_covered()
    else:
        print("Warning: No run log file!")

    # statistics
    for class_name in classes_dict:
        classes_dict[class_name].statistic()
    class_list = [c for c in classes_dict.values()]
    class_list.sort(key=lambda x: x.porpotion, reverse=True)
    covered_classes = [c for c in class_list if c.n_covered_methods > 0]
    return class_list, covered_classes
