import tiktoken

from functions.d4j import extract_classes, filter_classes_Grace, filter_classes_Ochiai


def failed_tests_prompt(test_cases):
    prompt = ""
    for i, test_case in enumerate(test_cases):
        prompt += f"{i+1}) {test_case.name}\n"
    return prompt


def test_code_prompt(test_cases, comment=True):
    prompt = "```java\n"

    # make prompt for test methods
    for test_case in test_cases:
        if comment:
            prompt += test_case.test_method.comment
            prompt += "\n"
        prompt += test_case.test_method.code
        prompt += "\n\n"

    prompt += "```"
    return prompt


def method_code_prompt(java_class, method_src_id):
    flag = True
    doc = ""
    prompt = "```java\n"
    for method in java_class.methods.values():
        if method.src_id == method_src_id:
            prompt += method.code
            prompt += "\n\n"
            doc = method.doc if method.doc != "" else method.enhanced_doc
            flag = False
            break
    prompt += "```"
    if flag:
        raise RuntimeError(f"method {method_src_id} not found")
    return prompt, doc


def test_utility_prompt(test_cases, model_type, comment=True):
    prompt = "```java\n"

    # make prompt for test utility methods
    already = set([])
    for test_case in test_cases:
        for test_utility_method in test_case.test_utility_methods:
            if test_utility_method.signature in already:
                continue
            if comment:
                prompt += test_utility_method.comment
                prompt += "\n"
            utility_code = check_tokens(model_type, test_utility_method.code, 500)
            prompt += utility_code
            prompt += "\n\n"
            already.add(test_utility_method.signature)

    prompt += "```"
    return prompt


def test_infos_prompt(test_cases, model_type, test_output_tokens=100, comment=True):
    """
    Return prompt includes information for each failed test, including test names, test codes, stack traces and test outputs.
    If comment is True, the comment of each test method will be included in the prompt.
    """
    prompt = ""
    for i, test_case in enumerate(test_cases):
        prompt += f"{i+1}) Failed Test: {test_case.name}\n\n"

        # Test Code
        prompt += 'Test Code: \n"```java\n'
        if comment:
            prompt += test_case.test_method.comment
            prompt += "\n"
        prompt += test_case.test_method.code
        prompt += '\n```"\n\n'

        # stack trace
        if test_case.stack_trace is not None:
            stack_trace = test_case.stack_trace
            if len(stack_trace) > 20:  # avoid extremly long stack trace
                stack_trace = stack_trace[:20]
            prompt += 'Stack Trace: \n"'
            prompt += "".join(stack_trace)
            prompt += '"\n\n'

        # test output
        if test_case.test_output is not None:
            if test_case.test_output != "":
                output_str = "".join(test_case.test_output)
                test_output = check_tokens(model_type, output_str, test_output_tokens)
                prompt += 'Test Output: \n"'
                prompt += test_output
                prompt += '"\n\n'

    return prompt


def covered_classes_prompt(version, project, bugID, test_suite, model_type, n_classes=50, class_doc_tokens=100, basement="None"):
    """
    Return prompt includes information of covered classes, including name and doc for each.
    The prompt is in shape of a MarkDown table.

    n_classes: in all of the covered classes, classes with Top n_classes highest
            method level coverage will be included in the prompt.
    class_doc_tokens: the maximum number of tokens for the class doc.
    """
    classes_dict = {}
    _, _, extracted_classes = extract_classes(version, project, bugID, test_suite, max_num=n_classes)
    if basement == "Grace":
        extracted_classes = filter_classes_Grace(project, bugID, extracted_classes)
    elif basement == "Ochiai":
        extracted_classes = filter_classes_Ochiai(project, bugID, extracted_classes)
    prompt = "| Index | Class Full Name | Class Documentation |\n"
    prompt += "| --- | --- | --- |\n"
    for i, java_class in enumerate(extracted_classes):
        class_name = java_class.class_name
        class_doc = check_tokens(model_type, java_class.doc, class_doc_tokens)
        classes_dict[class_name] = java_class
        prompt += f"| {i+1} | {class_name} | {class_doc} |\n"
    prompt += "\n\n\n"
    return prompt, classes_dict


def methods_prompt(java_class):
    prompt = "```java\n"
    for i, inst_id in enumerate(java_class.methods):
        method_name = java_class.methods[inst_id].src_id
        method_doc = java_class.methods[inst_id].doc
        method_code = java_class.methods[inst_id].code
        prompt += f'// {i+1}) Method Full Name: "{method_name}"\n'
        prompt += f'// Original Comment: "{method_doc}"\n'
        prompt += method_code
        prompt += "\n\n"
    prompt += "```\n\n\n"
    return prompt


def buggy_codes_prompt(buggy_codes):
    prompt = ""
    for i, key in enumerate(buggy_codes):
        prompt += f"{i+1}) Suspicious Method Full Name: {key}\n\n"
        prompt += f"Suspicious Method Comment: \"{buggy_codes[key]['method_doc']}\"\n\n"
        prompt += f"Suspicious Method Code:\n"
        prompt += f"\"\n{buggy_codes[key]['method_code']}\"\n\n\n"
    return prompt


def methods_prompt_new(java_class, methods):
    prompt = "```java\n"
    for inst_id in java_class.methods:
        method_name = java_class.methods[inst_id].src_id
        if method_name not in methods:
            continue
        method_doc = java_class.methods[inst_id].doc
        method_code = java_class.methods[inst_id].code
        prompt += f'// Method Full Name: "{method_name}"\n'
        prompt += f'// Original Comment: "{method_doc}"\n'
        prompt += method_code
        prompt += "\n\n"
    prompt += "```\n\n\n"
    return prompt


def methods_list_prompt(java_class, model_type, method_doc_tokens=100):
    prompt = "| Index | Method Full Name | Method Comment |\n"
    prompt += "| --- | --- | --- |\n"
    for i, inst_id in enumerate(java_class.methods):
        method_name = java_class.methods[inst_id].src_id
        enhanced_doc = java_class.methods[inst_id].enhanced_doc
        if enhanced_doc == "":
            enhanced_doc = java_class.methods[inst_id].doc
        method_doc = check_tokens(model_type, enhanced_doc, method_doc_tokens)
        prompt += f"| {i+1} | {method_name} | {method_doc} |\n"
    prompt += "\n\n\n"
    return prompt


def check_tokens(model_type, doc, max_tokens):
    encoding = tiktoken.encoding_for_model(model_type.value)
    original_tokens = encoding.encode(doc)
    num_doc_tokens = len(original_tokens)
    if num_doc_tokens <= max_tokens:
        return doc
    else:
        new_tokens = original_tokens[:max_tokens]
        new_doc = encoding.decode(new_tokens)
        return new_doc + " <truncated> ..."


def get_top1_prompt(test_suites, buggy_methods):
    test_suites_prompt = ""
    prompt = ""
    for i, test_suite in enumerate(test_suites):
        prompt += f"{i+1}) Failed Test Suite: \"{test_suite}\"\n"
        test_suites_prompt += f"{i+1}) {test_suite}\n"
        cause = ""
        methods = []
        for method in buggy_methods:
            if method["test_suite"] == test_suite:
                methods.append(method)
                if cause == "":
                    cause = method["test_failure_causes"].replace("\n", " ")
        prompt += f"Possible Causes of this Test Suite: \"{cause}\"\n"
        prompt += "Suspicious Methods of this Test Suite: \"\n"
        for method in methods:
            prompt += f"- {method['method_name']}\n"
        prompt += "\"\n\n"
    return test_suites_prompt, prompt
