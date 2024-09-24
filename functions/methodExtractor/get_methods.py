import os
import sys
from difflib import unified_diff
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from myparser import FunctionsExtractor, remove_comments_and_docstrings
from myparser.functions_extractor import Method
from unidiff import PatchSet


def get_modified_methods(extractor: FunctionsExtractor, buggy_file: List[str], fixed_file: List[str]):
    buggy_methods, _, buggy_locs = extractor.get_functions(
        CURRENT_LANG, "".join(buggy_file))
    fixed_methods, _, fixed_locs = extractor.get_functions(
        CURRENT_LANG, "".join(fixed_file))

    diff = list(unified_diff(buggy_file, fixed_file,
                fromfile='text1', tofile='text2', n=0))
    if len(diff) == 0:
        return [], [], [], []

    hunks = PatchSet("".join(diff))[0]
    changed_points_b = set()
    changed_points_f = set()
    for hunk in hunks:
        changed_points_b.add(hunk.source_start)
        changed_points_b.add(hunk.source_start + hunk.source_length - 1)
        changed_points_f.add(hunk.target_start)
        changed_points_f.add(hunk.target_start + hunk.target_length - 1)
    changed_buggy_methods = []
    changed_fixed_methods = []
    for method_idx, loc in enumerate(buggy_locs):
        start = loc[0][0] + 1
        end = loc[1][0] + 1
        for point in changed_points_b:
            if start <= point <= end:
                changed_buggy_methods.append(buggy_methods[method_idx])
                break
    for method_idx, loc in enumerate(fixed_locs):
        start = loc[0][0] + 1
        end = loc[1][0] + 1
        for point in changed_points_f:
            if start <= point <= end:
                changed_fixed_methods.append(fixed_methods[method_idx])
                break
    tokenized_buggy_methods = [
        extractor.get_tokens_with_node_type_from_str(
            CURRENT_LANG, x, remove_comment=False)[0]
        for x in changed_buggy_methods
    ]
    tokenized_fixed_methods = [
        extractor.get_tokens_with_node_type_from_str(
            CURRENT_LANG, x, remove_comment=False)[0]
        for x in changed_fixed_methods
    ]
    return changed_buggy_methods, tokenized_buggy_methods, changed_fixed_methods, tokenized_fixed_methods


def get_buggy_methods(extractor: FunctionsExtractor, buggy_file: List[str], fixed_file: List[str], lang: str):
    methods = extractor.get_functions(lang, "".join(buggy_file))
    diff = list(unified_diff(buggy_file, fixed_file,
                fromfile='text1', tofile='text2', n=0))
    assert len(diff) != 0, "buggy file and fixed file are the same"
    hunks = PatchSet("".join(diff))[0]
    changed_points_b = set()
    for hunk in hunks:
        changed_points_b.add(hunk.source_start)
        changed_points_b.add(hunk.source_start + hunk.source_length - 1)
    changed_buggy_methods = []
    ast_nodes = []
    for method in methods:
        loc = method.loc
        start = loc[0][0] + 1
        end = loc[1][0] + 1
        for point in changed_points_b:
            if start <= point <= end:
                changed_buggy_methods.append(method)
                break
    return changed_buggy_methods

def get_buggy_lines(buggy_file: List[str], fixed_file: List[str]):
    diff = list(unified_diff(buggy_file, fixed_file,
                fromfile='text1', tofile='text2', n=0))
    if len(diff) == 0:
        print("buggy file and fixed file are the same")
        return []
    diff = list(map(lambda x: x + "\n" if not x.endswith("\n") else x, diff))
    hunks = PatchSet("".join(diff))[0]
    changed_points = set()
    for hunk in hunks:
        if hunk.source_length == 0: # only add some lines, we label the wrapped lines as buggy
            changed_points.add(hunk.source_start)
            changed_points.add(hunk.source_start + 1)
        else:  # both have add and delete, we label all the deleted lines
            for i in range(hunk.source_start, hunk.source_start + hunk.source_length):
                changed_points.add(i)
    # sort the changed points
    buggy_lines = sorted(list(changed_points))
    return buggy_lines


def get_all_methods(extractor: FunctionsExtractor, file: List[str], lang: str) -> List[Method]:
    methods = extractor.get_functions(lang, "".join(file))
    return methods


def get_class_doc(extractor: FunctionsExtractor, file: List[str], lang: str, class_name: str) -> str:
    class_doc = extractor.get_class_doc(lang, "".join(file), class_name)
    return class_doc


if __name__ == '__main__':
    # extract buggy and patched file from secure them all
    code = """
    public class OuterClass {

    private String name;
    
    public OuterClass(String name) {
        this.name = name;
    }
    
    public void method() {
        System.out.println("This is outer class method");
    }
    
    class InnerClass {
        
        public void method() {
            System.out.println("This is inner class method");
        }
        
    }

}"""
    TREE_SITTER_LIB_PATH = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "myparser/my-languages.so")
    CURRENT_LANG = 'java'
    supproted_languages = ["java"]
    extractor = FunctionsExtractor(TREE_SITTER_LIB_PATH, supproted_languages)
    methods = get_all_methods(
        extractor, [line + "\n" for line in code.split("\n")], CURRENT_LANG)
    print("over")
