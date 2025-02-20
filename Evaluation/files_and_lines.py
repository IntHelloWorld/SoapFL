import os


def count_java_files_and_max_lines(directory):
    java_files_count = 0
    max_lines = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.java'):
                java_files_count += 1
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    max_lines = max(max_lines, len(lines))

    return java_files_count, max_lines

if __name__ == "__main__":
    # project_path = input("请输入Java项目路径: ")
    java_files_count, max_lines = count_java_files_and_max_lines("/home/qyh/projects/LLM-Location/AgentFL/Closure-21/src")
    print(f"Java文件总数: {java_files_count}")
    print(f"单个文件的最大行数: {max_lines}")