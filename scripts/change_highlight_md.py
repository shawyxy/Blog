import os
import re

def replace_highlight_syntax(directory):
    # 正则表达式匹配 ==文本内容==
    pattern = re.compile(r'(?<!`)==([^=]+)==(?!`)')

    # 遍历指定目录及其子目录
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()

                # 处理文件内容，跳过代码块
                processed_content = []
                skip = False  # 用于跟踪是否在代码块中
                for line in content.split('\n'):
                    if line.strip().startswith('```'):  # 切换跳过状态
                        skip = not skip
                    if not skip and not line.strip().startswith('!['):  # 忽略图片标记
                        line = pattern.sub(r'<mark>\1</mark>', line)
                    processed_content.append(line)

                # 将处理后的内容写回文件
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write('\n'.join(processed_content))

# 使用示例
directory_path = '/Users/man9o/'
replace_highlight_syntax(directory_path)
