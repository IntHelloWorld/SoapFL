from typing import List


class JavaMethod():
    def __init__(self, class_name, method_name):
        self.class_name = class_name
        self.method_name = method_name
        self._covered = False
        self._run_times = 0
    
    def add_run_time(self):
        self._run_times += 1
    
    def set_covered(self):
        self._covered = True

class JavaClass():
    def __init__(self, class_name):
        self.class_name = class_name
        self.methods = {}
    
    def add_methods(self, method: JavaMethod):
        self.methods[method.method_name] = method
    
    def statistic(self):
        n_covered_methods = 0
        _all_run_times = 0
        for method in self.methods.values():
            if method._covered:
                n_covered_methods += 1
                _all_run_times += method._run_times
        self.n_covered_methods = n_covered_methods
        self.n_all_methods = len(self.methods)
        self.porpotion = self.n_covered_methods / self.n_all_methods * 100
        self._all_run_times = _all_run_times

def analyse_coverage(inst_file, run_file) -> List[JavaClass]:
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
            java_method.add_run_time()
            if java_method._covered is False:
                java_method.set_covered()
    
    # statistics
    for class_name in classes_dict:
        classes_dict[class_name].statistic()
    class_list = [c for c in classes_dict.values()]
    class_list.sort(key=lambda x: x.porpotion, reverse=True)
    return class_list

def test():
    inst_file = "/home/qyh/projects/LLM-Location/Functions/tmp_Closure_4_com.google.javascript.jscomp.TypeCheckTest::testConversionFromInterfaceToRecursiveConstructor/inst.log"
    run_file = "/home/qyh/projects/LLM-Location/Functions/tmp_Closure_4_com.google.javascript.jscomp.TypeCheckTest::testConversionFromInterfaceToRecursiveConstructor/run.log"
    analyse_coverage(inst_file, run_file)

if __name__ == "__main__":
    test()