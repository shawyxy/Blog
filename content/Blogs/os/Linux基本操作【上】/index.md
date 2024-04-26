---
title: Linux基本操作【上】
weight: 1
open: true
math: true
---

操作环境：CentOS 7.6

## 1. ls 指令
### 语法
ls [选项] [目录/文件]
### 功能
罗列出该目录下所有子目录或文件（不包括被隐藏的文件或目录）；罗列出文件名及各种信息
**非常常用的选项** [几分钟就用一次的那种]：

- -a 罗列出包括隐藏文件的所有文件或目录。（隐藏文件或目录通常以`.`开头）
- -l 罗列出每个文件的详细信息（不包括隐藏文件或目录）

### 选项
常用选项（**前两个经常用**）：

- -r 对目录反向排序；
- -t 以时间排序；
- -d 将目录象文件一样显示，而不是显示其下的文件。 如：ls –d 指定目录；
- -i 输出文件的 i 节点的索引信息。 如 ls –ai 指定文件；
- -k 以 k 字节的形式表示文件的大小。ls –alk 指定文件；
- -n 用数字的 UID，GID 代替名称。 （介绍 UID， GID）；
- -F 在每个文件名后附上一个字符以说明该文件的类型，“*”表示可执行的普通文件；“/”表示目录；“@”表示符号链接；“|”表示 FIFOs；“=”表示套接字（sockets）（目录类型识别）；
- -s 在 l 文件名后输出该文件的大小；（大小排序，如何找到目录下最大的文件）
- -R 列出所有子目录下的文件；（递归）
- -1 一行只输出一个文件。
### 示例
下面对前两个个选项做出演示：

1. 直接 ls 不加选项的效果：
```cpp
ls
clash  Code  Git  test 
```
第一行的 ls 是指令，第二行是该目录下所有的文件（不包括被隐藏的）。这些文件/目录都是我自己创建的。

2. ls -a
```cpp
ls -a
.   .bash_history  .cache  Code     .cquery  .LfCache  test  .VimForCpp  .vimrc
..  .bashrc        clash   .config  Git      .pki      .vim  .viminfo    .ycm_extra_conf.py

```
显示当前目录下所有的文件，包括被隐藏的。第一行和第二行开头的一个点和两个点分别代表当前目录和上一级目录（稍后会解释）

3. ls -l
```cpp
ls -l
total 16
drwxrwxr-x 2 xy xy 4096 Aug  9 15:09 clash
drwxrwxr-x 3 xy xy 4096 Jul 24 18:13 Code
drwxrwxr-x 3 xy xy 4096 Aug  9 00:50 Git
drwxrwxr-x 3 xy xy 4096 Aug  5 01:55 test
//权限 链接数 拥有者 所属群组  文档容量 [字节] 文档最后修改时间 文档名称
```
-l 选项显示当前目录下所有文件（不包括被隐藏的）的详细信息。关于这些信息，我们将在 [权限] 部分学习。

---

当然，选项是可以组合的。例如要显示当前目录下包括被隐藏的所有文件或子目录，可以用 ls -a -l
```cpp
ls -a -l
total 84
drwx------  11 xy   xy    4096 Aug  9 15:31 .
drwxr-xr-x.  4 root root  4096 Jul 12 10:45 ..
-rw-------   1 xy   xy   17102 Aug  9 16:12 .bash_history
-rw-rw-r--   1 root root   119 Aug  4 17:13 .bashrc
drwxrwxr-x   4 xy   xy    4096 Aug  9 02:22 .cache
drwxrwxr-x   2 xy   xy    4096 Aug  9 15:09 clash
drwxrwxr-x   3 xy   xy    4096 Jul 24 18:13 Code
drwxrwxr-x   4 xy   xy    4096 Aug  9 14:38 .config
lrwxrwxrwx   1 xy   xy      47 Aug  4 17:13 .cquery -> /home/xy/.VimForCpp/cquery/config/cquery.config
drwxrwxr-x   3 xy   xy    4096 Aug  9 00:50 Git
drwxrwxr-x   3 xy   xy    4096 Aug  4 20:26 .LfCache
drwxrw----   3 xy   xy    4096 Aug  4 16:58 .pki
drwxrwxr-x   3 xy   xy    4096 Aug  5 01:55 test
lrwxrwxrwx   1 xy   xy      23 Aug  4 17:13 .vim -> /home/xy/.VimForCpp/vim
drwxrwxr-x   8 xy   xy    4096 Aug  4 17:12 .VimForCpp
-rw-------   1 xy   xy    9346 Aug  9 12:45 .viminfo
lrwxrwxrwx   1 xy   xy      32 Aug  4 17:13 .vimrc -> /home/xy/.VimForCpp/vim/init.vim
lrwxrwxrwx   1 xy   xy      37 Aug  4 17:13 .ycm_extra_conf.py -> /home/xy/.VimForCpp/ycm_extra_conf.py
```
当然，选项之间是平等的，所以把-a 和-l 选项调换顺序也没关系。
不过为了方便，人们将诸如以上指令简化为：ls -al 或 ls -la。
**ls -l 通常简写为 ll。所以 ls -a -l 通常简写为 ll -s**。         注意 ls -a 没有简写哦。不过 Linux 允许用户自定义指令，不过目前我们暂时不需要。
选项之间的组合非常灵活，不过只需要掌握常用的指令组合即可应付大部分场景需求，下面的指令也是一样的。
## 2. pwd 指令
### 功能
显示当前路径
### 示例
```cpp
pwd
/home/xy
```
pwd 指令非常简单，非常实用。因为在命令行中很容易忘记当前处于哪个目录下，简单的 pwd 指令能快速帮助我们定位。
## 3. cd（change directory）指令
### 语法
cd [目录名]
### 功能
将工作目录切换切换到指定目录下

- `~`表示 home 目录。（相当于 windos 下的"我的电脑"目录）
- `.`表示当前所在目录
- `..`表示当前所在目录的上一级目录

在演示之前，我们需要了解相对路径和绝对路径之间的区别：

- 绝对路径：从**根目录**开始的路径
- 相对路径：从**当前目录**开始的路径
> 假设 1->2->3->4 是从根目录开始的路径
> 绝对路径：
> 1. 1
> 1. 1->2
> 1. 1->2->3
> 1. 1->2->3->4
>
> 相对路径：
> 1. 2->3
> 1. 2->3->4
> 1. 3->4
> 1. 4
>
> 总而言之，绝对路径一定是从根目录开始的路径，而相对路径是绝对路径里的一段，这样做是为了减轻切换工作目录的负担。假如当前目录离根目录非常远，而用户只想回到上一级，难道要重新打一段上面的一长串路径吗？
> ps：虽然通过方向上下键可以找到最近 cd 进去的路径，但是这样也是稍微麻烦的，相对路径能让切换工作目录方便些。

### 示例

1. cd [dir]
```cpp
ls
clash  Code  Git  test # 查看当前目录下的文件/目录

cd test     # 不加斜杠进入 test 目录
ls		   # 查看该目录的文件/目录
a.out  d1  test.cpp

cd ..	   # 退回上一级目录
ls		   
clash  Code  Git  test # 发现和上面的是一样的

cd test/    # 加斜杠进入 test 目录
ls
a.out  d1  test.cpp	   # 发现和上面的是一样的
```
进入当前目录下的子目录，加不加斜杠都可以，一般不加。
> windows 下是斜杠--'/'
> Linux/macOS 下是反斜杠--'\'

上面都是以相对路径切换工作目录的，下面以绝对路径示例：
```cpp
cd ..
pwd		   # 查看当前路径
/home/xy
cd /home/xy/test # 绝对路径
ls
a.out  d1  test.cpp
```
显然，绝对路径有时候不是那么高效。
`cd ..`表示回到上一级目录
## 4. touch 指令
### 语法
touch [选项] [文件/目录]
### 功能
Linux touch 命令用于修改文件或者目录的时间属性，包括存取时间和更改时间，若文件不存在，系统会建立一个新的文件。
### 选项

- a 改变档案的读取时间记录；
- m 改变档案的修改时间记录；
- c 假如目的档案不存在，不会建立新的档案。与 --no-create 的效果一样；
- f 不使用，是为了与其他 unix 系统的相容性而保留；
- r 使用参考档的时间记录，与 --file 的效果一样；
- d 设定时间与日期，可以使用各种不同的格式；
- t 设定档案的时间记录，格式与 date 指令相同；
- --no-create 不会建立新档案；
- --help 列出指令格式；
- --version 列出版本讯息。

一般情况下，touch 都是作为新建文件使用的。
### 示例：
```cpp
pwd
/home/xy/test
ls
d1
touch test.txt
ls
d1  test.txt
```
在 test 目录下新建一个 test。txt 文件。
## 5 . mkdir（make directory）指令
### 语法
mkdir [选项] [目录名]
### 功能
在该目录下创建子目录
### 选项：

- -p 确保目录名称存在，不存在的就建一个。
### 示例：
```cpp
ls
d1  test.txt
mkdir d2
ls
d1  d2  test.txt
```
如果目录不存在，也不加选项-p：
```cpp
ls
d1  d2  test.txt
mkdir d3/d4
mkdir: cannot create directory ‘d3/d4’: No such file or directory
```
加上选项-p 能用一个路径创建不止一个子目录，节省时间。
## *6.rmdir 指令和 rm 指令
### 6.1 rmdir（remove directory）
#### 语法
rmdir [选项] [目录名]
#### 功能
删除空目录
#### 选项

- -p 是当子目录被删除后使它也成为空目录的话，则顺便一并删除。

示例：
```cpp
ls
d1  d2  test.txt

rmdir d2
ls

d1  test.txt
```
首先查看当前目录的文件/目录，删除 d2 子目录，再查看会发现 d2 确实被删除了。
如果在路径 d1/d2 中，当前位置在 d1 目录下，执行有-p 的 rmdir 指令，d1 也会被一并删除。
```cpp
ls
d1  test.txt
rmdir -p d1/d2
ls
test.txt 
```
请注意，如果在被删除的目录下执行该指令，是无效的：
```cpp
ls
d2
rmdir -p d1/d2
rmdir: failed to remove ‘d1/d2’: No such file or directory
```
### 6.2 rm（remove）
#### 语法
rm [选项] 文件名
#### 功能
删除文件或者目录
#### 选项

- -d：直接把欲删除的目录的硬连接数据删除成 0，删除该目录；
- -f：强制删除文件或目录；
- -i：删除已有文件或目录之前先询问用户；
- -r 或-R：递归处理，将指定目录下的所有文件与子目录一并处理；
- --preserve-root：不对根目录进行递归操作。
- -v：显示指令的详细执行过程。

注意：使用 rm 命令要格外小心。因为一旦删除了一个文件，就无法再恢复它。所以，在删除文件之前，最好再看一下文件的内容，确定是否真要删除。rm 命令可以用-i 选项，这个选项在使用文件扩展名字符删除多个文件时特别有用。使用这个选项，系统会要求你逐一确定是否要删除。这时，必须输入 y 并按 Enter 键，才能删除文件。如果仅按 Enter 键或其他字符，文件不会被删除。
#### 示例
有一个目录 d1，它的子目录路径是：d1/d2/d3. 一个文件 text.txt.
> 可以使用 tree 命令，以树状图列出目录的内容。
> 使用命令

```cpp
sudo yum -y install tree
```
> 安装。
> 语法：tree 目录名

首先用 tree 查看 d1 目录的结构
```cpp
ls
d1  test.txt
tree d1
d1
`-- d2
    `-- d3
 

2 directories, 0 files
```
d1 的结构是：d1/d2/d3
删除 text.txt
```cpp
rm test.txt
ls
d1
```
成功删除 text.txt
删除文件夹（路径）d1
```cpp
rm d1 
rm: cannot remove ‘d1’: Is a directory
```
直接删除目录是无效的。需要搭配选项。
```cpp
rm -r d1
ls
//（无文件）
```
> 也可以写成：rm -rf d1

增加-r 选项，表示递归地删除目录下的所有文件和目录。 -f 表示强制删除（force）
## *7. man 指令
### 语法
man [选项] [参数]
### 功能
查看 Linux 中的指令帮助。
> **man 命令** 是 Linux 下的帮助指令，通过 man 指令可以查看 Linux 中的指令帮助、配置文件帮助和编程帮助等信息。

### 选项

- -a：在所有的 man 帮助手册中搜索；
- -f：等价于 whatis 指令，显示给定关键字的简短描述信息；
- -P：指定内容时使用分页程序；
- -M：指定 man 手册搜索的路径。
### 参数

- 数字：指定从哪本 man 手册中搜索帮助；
- 关键字：指定要搜索帮助的关键字。
#### 数字代表内容
> 1：用户在 shell 环境可操作的命令或执行文件；
> 2：系统内核可调用的函数与工具等
> 3：一些常用的函数 (function) 与函数库 (library)，大部分为 C 的函数库 (libc)
> 4：设备文件说明，通常在/dev 下的文件
> 5：配置文件或某些文件格式
> 6：游戏 (games)
> 7：惯例与协议等，如 Linux 文件系统，网络协议，ASCII code 等说明
> 8：系统管理员可用的管理命令
> 9：跟 kernel 有关的文件

其实这不是很重要，虽然它很方便，但是作为以中文为母语的 Linux 使用者，还是 Google 来的方便。ps：也可以汉化 man。
### 示例
查看手册
```cpp
man ls
```
<img src="Linux基本操作【上】.IMG/cb574b124c49790ae01fb051946e810e.png" alt="image.png" style="zoom:40%;" />
实际上它很长，毕竟是使用手册。
查看 sleep 命令手册

```cpp
man sleep
```
<img src="Linux基本操作【上】.IMG/427eaa4e180a960efe62c7e52dda9f7f.png" alt="image.png" style="zoom:40%;" />
## *7. cp 指令
### 语法
cp [选项] [源文件/目标文件  +  目录]
### 功能
**cp 命令** 用来将一个或多个源文件或者目录复制到指定的目的文件或目录。它可以将单个源文件复制成一个指定文件名的具体的文件或一个已经存在的目录下。
注意：cp 命令还支持同时复制多个文件，当一次复制多个文件时，目标文件参数必须是一个已经存在的目录，否则将出现错误。
### 选项

- -a：此参数的效果和同时指定"-dpR"参数相同；
- -d：当复制符号连接时，把目标文件或目录也建立为符号连接，并指向与源文件或目录连接的原始文件或目录；
- -f：强行复制文件或目录，不论目标文件或目录是否已存在；
- -i：覆盖既有文件之前先询问用户；
- -l：对源文件建立硬连接，而非复制文件；
- -p：保留源文件或目录的属性；
- -R/r：递归处理，将指定目录下的所有文件与子目录一并处理；
- -s：对源文件建立符号连接，而非复制文件；
- -u：使用这项参数后只会在源文件的更改时间较目标文件更新时或是名称相互对应的目标文件并不存在时，才复制文件；
- -S：在备份文件时，用指定的后缀“SUFFIX”代替文件的默认后缀；
- -b：覆盖已存在的文件目标前将目标文件备份；
- -v：详细显示命令执行的操作。
### 注意

- 源文件：制定源文件列表。默认情况下，cp 命令不能复制目录，如果要复制目录，则必须使用-R 选项；
- 目标文件：指定目标文件。当“源文件”为多个文件时，要求“目标文件”为指定的目录。
### 示例
将一个目录下（/home/xy/Code）的某个文件（test.txt）拷贝到另一个目录（/home/xy/test）下
```cpp
pwd
/home/xy/Code
ls
test.txt

cp test.txt /home/xy/test

ls
CppCode  test.txt
cd ..
cd /home/xy/test
ls
test.txt
```
这是绝对路径。如果要拷贝到上级路径，使用`..`
在当前目录下新建子目录 d1，如果要拷贝 d1 目录到当前目录的上级目录，需要使用-rf，递归、强制地拷贝目录。
```cpp
pwd
/home/xy/Code
mkdir d1
ls
CppCode  d1  test.txt
cp -rf d1 ../
ls ../
clash  Code  d1  Git  test
```
d1 便是拷贝的目录。
tree 一下上级目录
```cpp
tree ../
../
|-- clash
|   |-- clash
|   `-- nohup.out
|-- Code
|   |-- CppCode
|   |-- d1
|   `-- test.txt
|-- d1
|-- Git
|   `-- linux
|       |-- 22_8_8_cmd.txt
|       |-- LICENSE
|       |-- README.md
|       `-- test.txt
`-- test
    `-- test.txt

8 directories, 8 files
```
## *8. mv 指令
### 语法
mv [选项] [源文件/目标文件  +  目录]
### 功能
**mv 命令** 用来对文件或目录重新命名，或者将文件从一个目录移到另一个目录中。前者为源文件或目录，后者为目标文件或目录。如果将一个文件移到一个已经存在的目标文件中，则目标文件的内容将被覆盖。
### 选项

- --backup=<备份模式>：若需覆盖文件，则覆盖前先行备份；
- -b：当文件存在时，覆盖前，为其创建一个备份；
- -f：若目标文件或目录与现有的文件或目录重复，则直接覆盖现有的文件或目录；
- -i：交互式操作，覆盖前先行询问用户，如果源文件与目标文件或目标目录中的文件同名，则询问用户是否覆盖目标文件。用户输入”y”，表示将覆盖目标文件；输入”n”，表示取消对源文件的移动。这样可以避免误将文件覆盖。
- --strip-trailing-slashes：删除源文件中的斜杠“/”；
- -S<后缀>：为备份文件指定后缀，而不使用默认的后缀；
- --target-directory=<目录>：指定源文件要移动到目标目录；
- -u：当源文件比目标文件新或者目标文件不存在时，才执行移动操作。

实际上，mv 最常用的命令就是它本身，足以应付大多数场景。
### 示例
将当前目录下的 test.txt 移动到上级目录下
```cpp
ls
CppCode  d1  test.txt
mv test.txt ../
ls ../
clash  Code  d1  Git  test  test.txt
ls
CppCode  d1
```
由结果来看，移动就相当于剪切一样，原本的位置文件被删除了。

**mv 修改文件名（经常使用）**
```cpp
ls
clash  Code  d1  Git  test  test.txt
 mv test.txt test1.txt
ls
clash  Code  d1  Git  test  test1.txt
```
可以认为 mv 指令就是拷贝和删除组合成的剪切，如果后面不跟路径，那么默认就是当前路径的文件，将一个文件重命名，只需要以`mv 旧文件 新文件`格式即可。
### 注意
mv 命令可以用来将源文件移至一个目标文件中，或将一组文件移至一个目标目录中。源文件被移至目标文件有两种不同的结果：

1. 如果目标文件是到某一目录文件的路径，源文件会被移到此目录下，且文件名不变。
1. 如果目标文件不是目录文件，则源文件名（只能有一个）会变为此目标文件名，并覆盖己存在的同名文件。如果源文件和目标文件在同一个目录下，mv 的作用就是改文件名。当目标文件是目录文件时，源文件或目录参数可以有多个，则所有的源文件都会被移至目标文件中。所有移到该目录下的文件都将保留以前的文件名。

注意：mv 与 cp 的结果不同，mv 好像文件“搬家”，文件个数并未增加。而 cp 对文件进行复制，文件个数增加了。
## 9. cat 指令
### 语法
cat [选项] [文件]
### 功能

- 显示文件内容，如果没有文件或文件为-则读取标准输入。
- 将多个文件的内容进行连接并打印到标准输出。
- 显示文件内容中的不可见字符（控制字符、换行符、制表符等）。
### 选项

- -b 对非空输入行编号
- -n 对输出的所有行编号
- -s 不输出多行空行
### 示例
cat 指令最常用的用途就是打印文件内容，不需要调用记事本或文本编辑器。
```cpp
ls
clash  Code  d1  Git  test  test1.txt
cat test1.txt 
##include <stdio.h>
int main()
{
  pritf("hello cat\n");
  return 0;
}
```
一般内容短小的文件，常常使用 cat 查看。
添加行号：
`cat -n test1.txt`
另外，tac 是从下到上打印文件内容：
```cpp
tac test1.txt 
}
  return 0;
  pritf("hello cat\n");
{
int main()
##include <stdio.h>
```
虽然它看起来没什么用但还是有点用的（存在即合理，大佬考虑的应用场景很多）
### 补充 echo
#### 语法
echo 字符串
#### 功能
打印字符串或将字符串作为内容填入或覆盖文本中。
#### 示例
打印内容到显示器
```cpp
echo "hello world"
hello world
```
输出重定向
```cpp
echo "hello world" > file.txt
ls
file.txt
cat file.txt
hello world
```
何为输出重定向？简单地说，本来 echo 后面跟的字符串是要被打印到显示器上的，是要输出到显示器上的。但是它被写入到文件中（如果这个文件不存在，会自动创建文件）。这就叫做输出重定向。

---
```c
8/9/22
```