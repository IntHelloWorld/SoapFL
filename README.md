# Summary

This is the online repository for the TSE article "SoapFL: A Standard Operating Procedure for LLM-based Method-Level Fault Localization".

---

# Environment
- Defects4J-V1.4.0 (Note that the buggy items in V1.4.0 is identical with V1.2.0, we use V1.4.0 to avoid some problems in V1.2.0)
- Defects4J-V2.0.0
- Python version >= 3.8.5
- Defects4J Mod

Before running SoapFL, please apply the files under the `Defects4J_mod` directory to modify your Defects4J V1.4.0/V2.0.0.

---

# Run SoapFL

Set your own OpenAI API key in `camel/model_backend.py`

It's easy to run SoapFL for localizing a bug with the following command:

```shell
python3 run.py --config <CONFIG_DIR> --version <D4J_VERSION> --project <PROJECT> --bugID <BUG_ID> --model <GPT_MODEL_NAME>
```

For example:

```shell
python3 run.py --config Default --version 1.4.0 --project Closure --bugID 26 --model GPT_3_5_TURBO
```

More configs can be seen under the directory `Config`

# Results

We release all of the results of SoapFL in the [online repository](https://zenodo.org/records/10853388), including the evaluation results on Defects4J V1.4.0/V2.0.0 and the ablation study result.

In the result of each bug, we record all of the prompts, responses, and intermediate outputs.

The human evaluation results can be found in the file `EvaluationResult/DebugResult_d4j140_GPT35_human.xlsx`

# System Messages for Agents
- Test Code Reviewer:

> You are a Test Code Reviewer. We share a common interest in collaborating to successfully locate the buggy code that cause the test suite to fail. You can examine the test code and the initialized classes to analyze the similar behavior of the failed tests within the test suite. To locate the bug, you must write a response that appropriately solves the requested instruction based on your expertise.

- Source Code Reviewer

> You are a Source Code Reviewer. we are both working at DebugDev. We share a common interest in collaborating to successfully locate the buggy code that cause the test suite to fail. Your main responsibilities is to generate a comment for each covered method base on the method call relationship. To locate the bug, you must write a response that appropriately solves the requested instruction based on your expertise.

- Software Test Engineer

> You are a Software Test Engineer. We share a common interest in collaborating to successfully locate the buggy code that cause the test suite to fail. You main responsibilities include examining the information of the failed tests to analyze the possible causes of the test failures, and determining the method that need to be fixed. To locate the bug, you must write a response that appropriately solves the requested instruction based on your expertise.

- Software Architect

> You are a Software Architect. We share a common interest in collaborating to successfully locate the buggy code that cause the test suite to fail. You are very familiar with the architecture of the software, the functions of each class and method in the software. You main responsibilities include examining the given information to locate the possible buggy classes and buggy methods. To locate the bug, you must write a response that appropriately solves the requested instruction based on your expertise.
