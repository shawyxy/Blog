#!/bin/bash

# 定义源目录和目标目录
src_directory="content/Blogs"
dest_directory="static"

# 找到所有以'.'开头的文件夹，然后移动它们到static目录
find "$src_directory" -type d -name ".*" -print0 | while IFS= read -r -d $'\0' folder; do
    # 构造新的目标路径
    new_path="$dest_directory/${folder#$src_directory/}"

    # 创建目标路径的父目录
    mkdir -p "$(dirname "$new_path")"

    # 移动文件夹到新位置
    mv "$folder" "$new_path"
    echo "Moved $folder to $new_path"
done

echo "All hidden folders have been moved to $dest_directory."
