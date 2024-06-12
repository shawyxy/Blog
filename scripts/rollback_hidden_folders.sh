#!/bin/bash

# 定义源目录和目标根目录
src_dir="/Users/man9o/Desktop/Blog/content/Blogs/Blogs"
dest_dir="/Users/man9o/Desktop/Blog/content/Blogs"

# 遍历源目录中的所有目录
find "$src_dir" -type d | while read src_subdir; do
  # 忽略源根目录本身
  if [[ "$src_subdir" == "$src_dir" ]]; then
    continue
  fi

  # 生成目标子目录路径
  dest_subdir="${src_subdir/$src_dir/$dest_dir}"

  # 查找并移动每个.IMG文件到目标目录
  find "$src_subdir" -maxdepth 1 -name "*.IMG" -exec mv {} "$dest_subdir" \;

  # 打印已移动的文件
  echo "Moved .IMG files from $src_subdir to $dest_subdir"
done

echo "All .IMG files have been moved."
