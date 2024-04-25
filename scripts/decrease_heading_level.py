import os
import re

def decrease_heading_level(directory):
    # 正则表达式用于匹配 Markdown 标题
    heading_pattern = re.compile(r'^(#+)', re.MULTILINE)

    # 遍历指定目录及其子目录下的所有文件
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()

                # 替换所有标题，增加一个 #
                updated_content = heading_pattern.sub(lambda m: '#' + m.group(1), content)

                # 将更新后的内容写回文件
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(updated_content)

# 示例使用路径，请替换为你的实际路径
directory_path = '/Users/man9o/'
decrease_heading_level(directory_path)
