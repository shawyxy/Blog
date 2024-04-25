# 为了生成HTML可以引用图片,将图片文件夹开头的`.`去掉

import os
import re

def rename_and_update_references(root_dir):
    # 递归处理文件和文件夹
    for root, dirs, files in os.walk(root_dir):
        # 修改文件夹名
        for folder in dirs:
            if folder.startswith('.'):  # 检查是否以点开始
                new_folder = os.path.join(root, folder[1:])  # 删除前面的点
                os.rename(os.path.join(root, folder), new_folder)
        
        # 修改Markdown文件中的图片引用
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 删除路径中不正确的点
                updated_content = re.sub(r'\]\(\./\.(.*?)\.IMG/', r'](\1.IMG/', content)
                updated_content = re.sub(r'<img src="\./\.(.*?)\.IMG/', r'<img src="\1.IMG/', updated_content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

# 调用函数并传入根目录路径
root_directory = '/Users/man9o/Desktop/Blog/content/Blogs/os/Reactor 模式/'
rename_and_update_references(root_directory)
