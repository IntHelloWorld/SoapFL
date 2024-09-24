import os

from functions.utils import run_cmd


def run_instrument(test_name, buggy_dir, tmp_dir, agent_jar, mode="src"):
    
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
        cmd1 = f"defects4j export -p {property} -w {buggy_dir}"
        out, err = run_cmd(cmd1)
        log = log + out + err
        classes_dir = os.path.join(buggy_dir, out)
    except Exception as e:
        raise RuntimeError(f"Failed to export \"{property}\" for {buggy_dir}, {e}")

    cmd2 = f"defects4j test -n -w {buggy_dir} -t {test_name} -a -Djvmargs=-javaagent:{agent_jar}=outputDir={tmp_dir},classesPath={classes_dir}"
    out, err = run_cmd(cmd2)
    log = log + out + err
    
    if os.path.exists(os.path.join(tmp_dir, "run.log")):
        os.rename(os.path.join(tmp_dir, "run.log"), run_log)
    if os.path.exists(os.path.join(tmp_dir, "inst.log")):
        os.rename(os.path.join(tmp_dir, "inst.log"), inst_log)
    
    return log


def test():
    run_instrument(
        "com.google.javascript.jscomp.TypeCheckTest::testBadInterfaceExtendsNonExistentInterfaces",
        "/home/qyh/projects/LLM-Location/preprocess/Defects4J-1.2.0/Closure/2/buggy",
        "/home/qyh/projects/LLM-Location/AgentFL/DebugResult",
        "/home/qyh/projects/LLM-Location/preprocess/classtracer/target/classtracer-1.0.jar",
        "test"
    )


if __name__ == "__main__":
    test()
