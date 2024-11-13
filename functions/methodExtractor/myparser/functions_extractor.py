import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import tree_sitter
from tree_sitter import Language, Parser

from .language_processors import JavascriptProcessor, PhpProcessor, PythonProcessor

sys.path.append(os.getcwd())


@dataclass
class Method():
    name: str
    args: str
    comment: str
    code: str
    ast: tree_sitter.Node
    loc: Tuple[Tuple[int, int], Tuple[int, int]]
    class_name: Optional[str] = None


class FunctionsExtractor:
    def __init__(self, lib_path: str, languages: List[str]) -> None:
        self.lib_path = lib_path
        self.languages = languages
        self.language_parsers = {}
        self.language_tokenizers = {}
        tokens_processor_map = {
            "java": self.get_tokens_with_node_type,
            "c": self.get_tokens_with_node_type,
            "cpp": self.get_tokens_with_node_type,
            "c_sharp": self.get_tokens_with_node_type,
            "javascript": JavascriptProcessor.get_tokens,
            "python": PythonProcessor.get_tokens,
            "php": PhpProcessor.get_tokens,
            "ruby": self.get_tokens_with_node_type,
            "go": self.get_tokens_with_node_type,
        }
        for lang in languages:
            tmp_parser = Parser()
            try:
                tmp_parser.set_language(Language(lib_path, lang))
                self.language_parsers[lang] = tmp_parser
                self.language_tokenizers[lang] = tokens_processor_map[lang]
            except Exception as e:
                print(e)
                continue
    
    def extract_method_info(self, code):
        def traverse_node(node):
            if node.type == 'method_declaration':
                method_comment = ""
                method_code = None
                method_name = None
                if "comment" in node.prev_sibling.type:
                    method_comment = bytes.decode(node.prev_sibling.text)
                method_code = node.text.decode("utf-8")

                for child in node.children:
                    if child.type == 'identifier':
                        method_name = bytes.decode(child.text)
                
                if method_name is None:
                    raise ValueError("No method name found in the code")

                return {
                    "method_name": method_name,
                    "method_code": method_code,
                    "method_comment": method_comment
                }

            for child in node.children:
                result = traverse_node(child)
                if result:
                    return result

            return None

        parser = self.language_parsers["java"]
        tree = parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        method_info = traverse_node(root_node)
        if not method_info:
            raise ValueError("No method found in the code")
        return method_info
    
    def get_functions(
        self, language: str, code: str
    ) -> List[Method]:
        if language not in self.language_parsers:
            raise Exception("language not supported")
        parser = self.language_parsers[language]
        functions_producer = eval("self.get_" + language + "_functions")
        return functions_producer(code, parser)

    def get_class_doc(
        self, language: str, code: str, class_name: str
    ) -> str:
        if language not in self.language_parsers:
            raise Exception("language not supported")
        parser = self.language_parsers[language]
        functions_producer = eval("self.get_" + language + "_class_doc")
        return functions_producer(code, parser, class_name)

    def get_tokens_with_node_type_from_str(
        self, language: str, code: str, remove_comment=True
    ) -> Tuple[List[str], List[List[str]]]:
        """
        This function extracts the tokens and types of the tokens from string.
        It returns a list of string as tokens, and a list of list of string as types.
        For every token, it extracts the sequence of ast node type starting from the token all the way to the root(similar to AST path).
        :param language: the language of input code
        :param code: the byte string corresponding to the code.
        :return:
            List[str]: The list of tokens.
            List[List[str]]: The AST node types corresponding to every token.
        """

        if language not in self.language_parsers:
            return [], []
        if not isinstance(code, bytes):
            code = bytes(code, "utf8")
        tree = self.language_parsers[language].parse(code)
        root_node = tree.root_node
        return self.get_tokens_with_node_type(code, root_node, remove_comment)

    def get_tokens_with_node_type(
        self, code: bytes, root: tree_sitter.Node, remove_comment=True
    ) -> Tuple[List[str], List[List[str]]]:
        """
        This function extracts the tokens and types of the tokens.
        It returns a list of string as tokens, and a list of list of string as types.
        For every token, it extracts the sequence of ast node type starting from the token all the way to the root.
        :param code: the byte string corresponding to the code.
        :param root: the root node of the parsed tree
        :return:
            List[str]: The list of tokens.
            List[List[str]]: The AST node types corresponding to every token.
        """
        if not isinstance(code, bytes):
            code = bytes(code, "utf8")
        tokens, types = [], []
        if root.type == "comment" and remove_comment:
            return tokens, types
        elif root.type == "comment" and not remove_comment:
            return [code[root.start_byte: root.end_byte].decode()], types
        if "string" in str(root.type):
            return [code[root.start_byte: root.end_byte].decode()], [["string"]]
        if len(root.children) == 0:
            tokens.append(code[root.start_byte: root.end_byte].decode())
            types.append(get_ancestor_type_chains(root))
        else:
            for child in root.children:
                _tokens, _types = self.get_tokens_with_node_type(
                    code, child, remove_comment)
                tokens += _tokens
                types += _types
        return tokens, types

    @staticmethod
    def get_c_functions(code, parser):
        def dfs(node, method_list):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                if child.type == "function_definition" or child.type == "method_declaration":
                    method_list.append(child)

        tree = parser.parse(bytes(code, "utf8"))
        method_nodes = []
        dfs(tree.root_node, method_nodes)

        code_list = code.split("\n")
        methods_list = []
        method_locations = []
        for n in method_nodes:
            method = "\n".join(code_list[n.start_point[0]: n.end_point[0] + 1])
            methods_list.append(method)
            method_locations.append((n.start_point, n.end_point))
        return methods_list, method_nodes, method_locations


    @staticmethod
    def get_java_class_doc(code, parser, target_class_name):
        def dfs(node):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                if child.type == "class_declaration":
                    class_name = get_class_name(child)
                    if class_name == target_class_name:
                        nonlocal class_doc
                        class_doc = get_doc(child)
                else:
                    dfs(child)
        
        def get_doc(node):
            if "comment" in node.prev_sibling.type:
                return bytes.decode(node.prev_sibling.text)
            else:
                return ""
        
        def get_class_name(node):
            for child in node.children:
                if child.type == "identifier":
                    return bytes.decode(child.text)

        tree = parser.parse(bytes(code, "utf8"))
        class_doc = ""
        dfs(tree.root_node)
        return class_doc
    

    @staticmethod
    def get_java_functions(code, parser):
        """
        find all method declarations, including methods in inner classes.
        
        ignore the nested relationship between methods, which means when there are 
        inner-methods (such as methods of anonymous class or else) in a outer-method, 
        only keep the outer-method.
        """

        def get_args_type(method_declaration):
            type_list = []
            c = method_declaration.child_by_field_name("parameters").named_children
            for param in c:
                if param.type == "spread_parameter":  # solve spread parameter, e.g., "final String[]..." -> "String[][]"
                    for child in param.children:
                        if child.type != "modifiers":
                            arg = bytes.decode(child.text) + "[]"
                            type_list.append(arg)
                            break
                else:
                    type_identifier = param.child_by_field_name("type")
                    if type_identifier.type == "scoped_type_identifier":  # e.g., "Node.Type" -> "Type"
                        arg = bytes.decode(type_identifier.named_children[-1].text)
                    else:
                        arg = bytes.decode(type_identifier.text)
                    
                    # solve array parameter, e.g., "String" -> "String[]"
                    dimension = param.child_by_field_name("dimensions")
                    if dimension is not None:
                        arg += "[]"

                    # remove type parameters. e.g., "List<String>" -> "List"
                    if "<" in arg:
                        arg = arg.split("<")[0]
                    type_list.append(arg)
            return "(" + ",".join(type_list) + ")"

        def get_method_name(method_declaration):
            for child in method_declaration.children:
                if child.type == "identifier":
                    return bytes.decode(child.text)

        def get_class_name(node):
            classes = []
            while True:
                if node is None:
                    break
                if node.type in ["class_declaration", "interface_declaration", "enum_declaration"]:
                    for child in node.children:
                        if child.type == "identifier":
                            classes.insert(0, bytes.decode(child.text))
                node = node.parent
            if len(classes) == 0:
                return None
            else:
                return "$".join(classes)

        def get_method_object(node: tree_sitter.Node) -> Method:
            method_code = "\n".join(
                code_list[node.start_point[0]: node.end_point[0] + 1])
            method_name = get_method_name(node)
            method_class = get_class_name(node)
            method_arg = get_args_type(node)
            method_location = (node.start_point, node.end_point)
            if "comment" in node.prev_sibling.type:
                method_comment = bytes.decode(node.prev_sibling.text)
            else:
                method_comment = ""
            method = Method(method_name, method_arg, method_comment, method_code,
                            node, method_location, method_class)
            return method

        def dfs(node):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                if child.type in ["method_declaration", "constructor_declaration"]:
                    methods.append(get_method_object(child))
                else:
                    dfs(child)

        tree = parser.parse(bytes(code, "utf8"))
        methods = []
        code_list = code.split("\n")
        dfs(tree.root_node)
        return methods

    @staticmethod
    def get_python_functions(code, parser):
        def dfs(node, method_list):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                if child.type == "class_definition":
                    dfs(child, method_list)
                elif child.type == "block":
                    method_nodes = child.children
                    for grandson in method_nodes:
                        if grandson.type == "function_definition":
                            method_list.append(grandson)
                    return
                elif child.type == "function_definition":
                    method_list.append(child)
                    dfs(child, method_list)  # for the nested functions

        tree = parser.parse(bytes(code, "utf8"))
        method_nodes = []
        dfs(tree.root_node, method_nodes)

        code_list = code.split("\n")
        methods_list = []
        method_locations = []
        for n in method_nodes:
            method = "\n".join(code_list[n.start_point[0]: n.end_point[0] + 1])
            methods_list.append(method)
            method_locations.append((n.start_point, n.end_point))
        return methods_list, method_nodes, method_locations

    @staticmethod
    def get_go_functions(code, parser):
        def dfs(node, method_list):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                # DEBUG
                # print(child.type)
                #
                if child.type == "function_declaration" or child.type == "method_declaration":
                    method_list.append(child)

        tree = parser.parse(bytes(code, "utf8"))
        method_nodes = []
        dfs(tree.root_node, method_nodes)
        code_list = code.split("\n")
        methods_list = []
        method_locations = []
        for n in method_nodes:
            method = "\n".join(code_list[n.start_point[0]: n.end_point[0] + 1])
            methods_list.append(method)
            method_locations.append((n.start_point, n.end_point))
        return methods_list, method_nodes, method_locations

    @staticmethod
    def get_php_functions(code, parser):
        def dfs(node, method_list):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                # DEBUG
                # print(child.type)
                #
                if child.type == "class_declaration":
                    dfs(child, method_list)
                elif child.type == "declaration_list":
                    method_nodes = child.children
                    for grandson in method_nodes:
                        if grandson.type == "method_declaration":
                            method_list.append(grandson)
                    return
                elif child.type == "compound_statement":
                    method_nodes = child.children
                    for grandson in method_nodes:
                        if grandson.type == "function_definition":
                            method_list.append(grandson)
                    return
                elif child.type == "function_definition":
                    method_list.append(child)
                    dfs(child, method_list)  # for the nested functions

        tree = parser.parse(bytes(code, "utf8"))
        method_nodes = []
        dfs(tree.root_node, method_nodes)

        code_list = code.split("\n")
        methods_list = []
        method_locations = []
        for n in method_nodes:
            method = "\n".join(code_list[n.start_point[0]: n.end_point[0] + 1])
            methods_list.append(method)
            method_locations.append((n.start_point, n.end_point))
        return methods_list, method_nodes, method_locations

    @staticmethod
    def get_ruby_functions(code, parser):
        def dfs(node, method_list):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                # DEBUG
                # print(child.type)
                #
                if child.type == "class":
                    dfs(child, method_list)
                elif child.type == "method":
                    method_list.append(child)
                    dfs(child, method_list)  # for the nested functions

        tree = parser.parse(bytes(code, "utf8"))
        method_nodes = []
        dfs(tree.root_node, method_nodes)

        code_list = code.split("\n")
        methods_list = []
        method_locations = []
        for n in method_nodes:
            method = "\n".join(code_list[n.start_point[0]: n.end_point[0] + 1])
            methods_list.append(method)
            method_locations.append((n.start_point, n.end_point))
        return methods_list, method_nodes, method_locations

    @staticmethod
    def get_javascript_functions(code, parser):
        def dfs(node, method_list):
            node_childs = node.children
            if node_childs == []:
                return
            for child in node_childs:
                if child.type == "class_declaration":
                    dfs(child, method_list)
                elif child.type == "class_body":
                    method_nodes = child.children
                    for grandson in method_nodes:
                        if grandson.type == "method_definition":
                            method_list.append(grandson)
                    return
                elif child.type == "statement_block":
                    method_nodes = child.children
                    for grandson in method_nodes:
                        if grandson.type == "function_declaration":
                            method_list.append(grandson)
                    return
                elif child.type == "function_declaration":
                    method_list.append(child)
                    dfs(child, method_list)  # for the nested functions

        tree = parser.parse(bytes(code, "utf8"))
        method_nodes = []
        dfs(tree.root_node, method_nodes)

        code_list = code.split("\n")
        methods_list = []
        method_locations = []
        for n in method_nodes:
            method = "\n".join(code_list[n.start_point[0]: n.end_point[0] + 1])
            methods_list.append(method)
            method_locations.append((n.start_point, n.end_point))
        return methods_list, method_nodes, method_locations


def get_ancestor_type_chains(node: tree_sitter.Node) -> List[str]:
    types = [str(node.type)]
    while node.parent is not None:
        node = node.parent
        types.append(str(node.type))
    return types


if __name__ == "__main__":
    # LIB_PATH = 'parser/my-languages.so'

    # TODO: remove comments in code
    LIB_PATH = "parser/languages_0.19.1.so"
    supproted_languages = ["java", "python", "go", "php", "ruby", "javascript"]

    extractor = FunctionsExtractor(LIB_PATH, supproted_languages)
    java_code = open("DataProcessing/code_cases/java_code.java", "r").read()
    python_code = open("DataProcessing/code_cases/python_code.py", "r").read()
    go_code = open("DataProcessing/code_cases/go_code.go", "r").read()
    php_code = open("DataProcessing/code_cases/php_code.php", "r").read()
    ruby_code = open("DataProcessing/code_cases/ruby_code.rb", "r").read()
    js_code = open("DataProcessing/code_cases/js_code.js", "r").read()
    m, n, l = extractor.get_functions("java", java_code)
    res = extractor.get_tokens_with_node_type_from_str("java", java_code)
    res = extractor.get_tokens_with_node_type(java_code, n[0])
    # m, n, l = extractor.get_functions('python', python_code)
    # m, n, l = extractor.get_functions('go', go_code)
    # m, n, l = extractor.get_functions('php', php_code)
    # m, n, l = extractor.get_functions('ruby', ruby_code)
    # m, n, l = extractor.get_functions('javascript', js_code)

    print("一共有{}个函数".format(len(m)))
    print(m)
    print("对应的节点信息为：")
    print("\n".join([str(x) for x in n]))
