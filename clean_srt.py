import os
import sys


def clean_srt_files(root_path="."):
    to_replace_1 = '\u200b'
    to_replace_2 = '\u200c'
    total_replacements = 0

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if filename.endswith("_原文.srt"):
                file_path = os.path.join(dirpath, filename)
                print(f"处理文件: {file_path}")

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                count_1 = content.count(to_replace_1)
                count_2 = content.count(to_replace_2)
                count = count_1 + count_2
                if count > 0:
                    new_content = content.replace(to_replace_1, "")
                    new_content = new_content.replace(to_replace_2, "")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    total_replacements += count
                    print(f"已替换 {count} 个目标字符。")
                else:
                    print("未发现目标字符，无需替换。")

    print(f"\n总共替换了 {total_replacements} 个目标字符。")


# 示例调用
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用当前目录")
        clean_srt_files()
    else:
        clean_srt_files(sys.argv[1])
