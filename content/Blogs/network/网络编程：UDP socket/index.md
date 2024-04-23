---
title: 网络编程：UDP socket
weight: 3
open: true
---
## 阅读前导

UDP（User Datagram Protocol，用户数据报协议）是一个简单的面向数据报的运输层协议。它不提供可靠性，只是把应用程序传给 IP 层的数据报发送出去，但是不能保证它们能到达目的地。由于 UDP 在传输数据报前不用再客户和服务器之间建立一个连接，且没有超时重发等机制，所以传输速度很快。

友情链接：[网络基础：socket 套接字](https://blog.csdn.net/m0_63312733/article/details/130441666?spm=1001.2014.3001.5501)

# 服务端

实现一个 UDP 服务器通常需要以下几个步骤：

1. 创建一个套接字（socket），使用`socket()`函数。
2. 将套接字绑定到一个地址和端口上，使用`bind()`函数。
3. 接收客户端发送的数据，使用`recvfrom()`函数。
4. 处理接收到的数据。
5. 向客户端发送响应数据，使用`sendto()`函数。
6. 关闭套接字，使用`close()`函数。

以上是实现一个简单的 UDP 服务器的基本步骤。在实际应用中，还可能需要进行更多的操作，例如错误处理、超时处理等。

本小节将实现一个简单的回声服务器（echo server），即像`echo`指令一样回显内容：

<img src="./网络编程：UDP socket.IMG/image-20230430125735059.png" alt="image-20230430125735059" style="zoom: 33%;" />	

## 定义

服务端的逻辑将被定义在`UdpServer.cc`中，它包含了头文件`UdpServer.hpp`。

而且服务端使用各种 socket 接口的操作将被封装为一个`UdpServer`类，这个类型的对象就可以被称之为服务端。它将在头文件中被定义，在源文件中被使用。

## 日志

在调试过程中，我们经常使用打印语句打印提示信息，虽然“打印大法”在很多时候很有用，但产品始终是面向用户的，因此提示信息既要使用用户看得懂的话呈现，又要将错误信息保存起来，以供开发者修复。日志信息通常保存在日志文件中，它的文件后缀是`.log`

通常情况下，日志信息被保存在文件中，但是这里为了更方便地观察现象，将本应该写入文件的信息通过标准错误流`cerr`输出到屏幕上（直接使用`cout`也可以，不过日志一般使用`cerr`）。

在这里使用日志的另一个必要性是如果函数执行失败，将会设置一个全局的错误码，它在查错时是有必要的。除此之外，当通过返回值发现函数执行错误时，使用`exit()`函数强制退出设置的退出码也可以有一个表来保存错误码和错误信息的映射关系。

```cpp
// Log.hpp
#pragma once

#include <iostream>
#include <cstdarg>
#include <ctime>
#include <string>

// 日志级别
#define DEBUG   0
#define NORMAL  1
#define WARNING 2
#define ERROR   3
#define FATAL   4

const char *LevelMap[] = 
{
    "DEBUG",
    "NORMAL",
    "WARNING",
    "ERROR",
    "FATAL"
};

// 打印版本
void logMessage(int level, const char *format, ...)
{
#ifndef DEBUG_SHOW
    if(level== DEBUG) return;
#endif
    // 标准部分
    char stdBuffer[1024];
    time_t timestamp = time(nullptr);
    snprintf(stdBuffer, sizeof stdBuffer, "level[%s], time[%ld] ", LevelMap[level], timestamp);
    // 自定义部分
    char logBuffer[1024];
    va_list args;
    va_start(args, format);
    vsnprintf(logBuffer, sizeof logBuffer, format, args);
    va_end(args);
    // 打印
    printf("%s%s\n", stdBuffer, logBuffer);
}
```

注意：

- 日志的设计可以根据需要，但是日志需要实现最基本的功能：日志等级、日期和时间、内容，以及支持用户自定义等（可以使用可变参数实现用户自定义的日志信息）。
- 根据日志的重要性，赋予日志以优先级，以保证重要的问题最先被处理。用一个数组`LevelMap[]`保存这些宏，以便使用，且下标和它们的值对应。
  - 值为 0 的宏`DEBUG`是用于调试的日志，仅用于调试，在产品发布时可以删除它。
  - `NORMAL`：日常日志。
  - `WARNING`：告警日志。
  - `ERROR`：错误但不影响任务执行。
  - `FATAL`：致命错误。
  - `if(level== DEBUG) return;`：预处理命令，在编译时添加`-DDEBUG_SHOW`选项，这个语句就会失效。

关于可变参数的说明，可以看这里：[stdarg.h](https://gitee.com/shawyxy/2023-linux/blob/main/UdpSocket/SingleProcess/stdarg.md)

## 框架

### 成员属性

一个服务端进程要对数据进行处理，必须要知道数据是谁发送的，因此需要 IP 地址；除此之外，处理数据的主体是进程，网络通信的本质是跨网络的进程间通信，因此需要用端口号标识进程的唯一性。除此之外，每个服务端都需要一个套接字来传输信息。它本质是一个文件，因此使用 int 类型的变量保存它的文件描述符。

值得注意的是，这里的端口号指的是发送数据的主机（即客户端）的端口号，而不是本机（即服务器）的端口号。服务器可以使用这些信息来确定客户端的身份，并向客户端发送响应。

```cpp
// UdpServer.hpp
#include <iostream>
#include <string>

class UdpServer
{
public:
    UdpServer(uint16_t port, std::string ip = "0.0.0.0")
    : _port(port)
    , _ip(ip)
    , _sockfd(-1)
    {}
    ~UdpServer()
    {}
private:
    uint16_t _port;     // 端口号
    std::string _ip;    // IP 地址
    int _sockfd;        // 套接字文件描述符
};
```

这只是服务端类的一个框架，后续会根据需要进行修改。

注意：构造函数中的`ip`赋予了缺省值，`0.0.0.0`表示允许接收来自任何 IP 地址的数据，稍后会做详细解释。在正常情况下，它不会被赋予缺省值。

### 服务端框架

- 控制命令行参数：在运行程序的同时将 IP 和 PORT 作为参数传递给进程，例如`./[name] [IP] [PORT]`这就需要提取出命令行参数`IP`和`PORT`。除此之外，通常的做法是通过打印一个语句来显示它的使用方法，一般使用一个函数`usage()`封装。
- 参数类型转换：我们知道，IP 和 PORT 都是整数，而命令行参数是一个字符串，所以提取出参数以后，要对它们进行类型转换。由于这里的 IP 地址稍后要用其他函数转换，所以只有 PORT 使用了`atoi()`函数转换为整数。
- 以防资源泄露，这里使用了`unique_ptr`智能指针管理服务器的资源，不必在此深究，这里的程序比较简单，用一对`new`和`delete`也能实现资源的申请与回收。注意调用构造函数的时候需要传递参数。智能指针的头文件是`<memory>`

```cpp
#include "UdpServer.hpp"
#include <memory>
#include <cstdio>

static void usage(std::string proc)
{
    std::cout << "\n Usage: " << proc << " [IP] [PORT]\n" << std::endl;
}

// 指令：{ ./UdpServer [IP] [PORT] }
int main(int argc, char* argv[])
{
    if(argc != 3)
    {
        usage(argv[0]);
        exit(1);
    }

    std::string ip = argv[1];
    uint16_t port = atoi(argv[2]);
    std::unique_ptr<UdpServer> server_ptr(new UdpServer(port, ip));
    
    return 0;
}
```

后续代码中重复的头文件将会被省略，只显示新增的头文件。

> 提供使用说明是规范的，大多数程序都会提供，例如：
>
> <img src="./网络编程：UDP socket.IMG/image-20230429173832545.png" alt="image-20230429173832545" style="zoom:50%;" />

## 初始化服务器

初始化服务器的逻辑将被封装在`UdpServer`类的`initServer()`成员函数中。

### 创建套接字

当服务器对象被创建出来，就要立马初始化它，初始化的第一件事就是创建套接字，这个操作相当于构建了网络通信信道的一端。`socket()`函数用于创建套接字。

```c
int socket(int domain, int type, int protocol);
```

参数：

- domain（域）：指定套接字家族，简单地说就是指定通信的方式是本地还是网络：
  - `AF_INET`：网络通信。
- type：指定套接字的类型，即传输方式：
  - `SOCK_DGRAM`：无连接的套接字/数据报套接字。
- protocol（协议）：指定传输协议，默认设置为`0`，此函数内部会根据前两个参数推导出传输协议。

返回值：

- 成功：返回一个 int 类型的文件描述符。这个 socket 描述符跟文件描述符一样，后续的操作都有用到它，把它作为参数，通过它来进行一些读写操作。
- 失败：返回-1，同时设置错误码。

> 其中，`AF_INET`是一个宏，表示基于网络的套接字。`SOCK_DGRAM`也是宏，表示套接字类型是面向数据报的。

> 数据报套接字和流套接字有什么区别？

数据报套接字（SOCK_DGRAM）和流套接字（SOCK_STREAM）是两种不同类型的套接字。数据报套接字基于 UDP 协议，提供无连接的不可靠传输服务，而流套接字基于 TCP 协议，提供面向连接的可靠传输服务。

数据报套接字适用于传输数据量小、对实时性要求较高的应用场景，它可以快速地发送和接收数据，但不能保证数据的顺序和完整性。流套接字适用于传输数据量大、对可靠性要求较高的应用场景，它能够保证数据按顺序、完整地传输，但传输速度相对较慢。

下面是创建套接字和差错处理的逻辑：

```cpp
#include "Log.hpp"
#include <cerrno>
#include <cstring>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>

class UdpServer{    
	bool initServer()
    {
        // 1. 创建套接字
        _sockfd = socket(AF_INET, SOCK_DGRAM, 0);
        if(_sockfd < 0)
        {
            logMessage(FATAL, "%d : %s", errno, strerror(errno));
            exit(2);
        }
    }
    ~UdpServer()
    {
        if(_sockfd >= 0) close(_sockfd);
    }
    return true;
}
```

注意：这里使用了`string.h`中的`strerror()`函数，strerror() 函数用于将错误码转换为对应的错误信息字符串。它接受一个错误码作为参数，返回一个指向描述该错误的字符串的指针。这个字符串描述了错误码所代表的错误原因。

例如，当一个库函数调用失败时，通常会产生一个错误码，这个错误码会被存储在全局变量 errno 中。可以使用 strerror(errno) 来获取对应的错误信息字符串。

对应地，在析构函数中可以将正常打开的文件描述符关闭。这样做是规范的，实际上一个服务器运行起来以后非特殊情况将会一直运行，调用析构函数的次数寥寥无几。

---

简单测试一下服务端，并增加调试信息：

```cpp
// UdpServer.cc
int main(int argc, char* argv[])
{
    // ...
    std::unique_ptr<UdpServer> server_ptr(new UdpServer(port, ip));
    server_ptr->initServer();
    
    return 0;
}
// Makefile
UdpServer : UdpServer.cc
	g++ -o $@ $^ -std=c++11 -DDEBUG_SHOW
```

结果：

<img src="./网络编程：UDP socket.IMG/image-20230429194023669.png" alt="image-20230429194023669" style="zoom:33%;" />

如果使用了错误的参数，会出现提示内容：

<img src="./网络编程：UDP socket.IMG/image-20230430000538861.png" alt="image-20230430000538861" style="zoom:33%;" />

### 绑定

上面只完成了初始化服务器的第一步，只是过滤了一些不利条件，但是成员属性的 IP 和 PORT 都还未被使用。如果不用它们的话就没办法传输数据。因此要将用户在命令行传入的 IP 地址和 PORT 在内核中与当前进程强关联起来，也就是绑定（bind）。即通过绑定，在后续的执行逻辑中这个端口号就对只对应着被绑定的服务器进程，因为端口号标定着主机中进程的唯一性，服务器运行起来本身就是一个进程。

`bind()`函数用于将套接字与指定的 IP 地址和端口号绑定。通常在 TCP 协议或 UDP 协议的服务端设置。

```c
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
int bind(int sockfd, const struct sockaddr *addr,
                socklen_t addrlen);
```

参数：

- sockfd：要绑定的套接字文件描述符，它的本质是一个数组下标。
- addr：是一个指向`struct sockaddr`类型结构体的指针，该结构体中包含了要绑定的 IP 地址和端口号。
- addrlen 是`addr`所指向的地址结构体的大小。

实际上，第二个参数是一个被强转为`struct sockaddr*`类型的结构体，它原本是`struct sockaddr_in`类型的，在传入参数绑定之前，需要将用户设置的 IP 地址和 PORT 填充到这个结构体的属性中。

友情链接：[sockaddr 结构体](https://gitee.com/shawyxy/2023-linux/blob/3550a916d5ad03043c597f80d5cf4cd8f861e3ce/UdpSocket/SingleProcess/sockaddr.md)

简单地说，`sockaddr_in`类型的结构体相当于`sockaddr`类型的一个子类，父类能通过强转，获取到子类中父类那一部分信息。`sockaddr`的属性有这些需要手动处理的：

- sin_family：表示协议家族。选择`AF_INET`，表示网络通信。
- sin_port：表示端口号，是一个 16 位的整数。
- sin_addr：表示 IP 地址，是一个 32 位的整数，一般情况下设置为`INADDR_ANY`，它是一个值为 0 的宏，表示接收来自任意 IP 地址的数据。

除此之外，我们从命令行参数列表中获取到用户指定的 IP 地址和 PORT 的格式依然有问题，PORT 在提取命令行参数时就已经完成了从字符串到整数的转换，剩下的 IP 地址是一个字符串。

> 点分十进制表示法是一种用于表示数字数据的格式。它由一串十进制数字组成，使用句号（点）作为分隔符。在计算机网络中，IPv4 地址通常使用四个十进制整数的四点表示法来表示，每个整数的范围为 0 到 255。将 IP 地址从字符串转换为整数是一个常见的操作。这样做可以更方便地进行比较和排序。可以使用位运算符来实现这个转换。

对于类似`127.127.127.127`这样的字符串，它占用了十几个字节，而 IP 地址本身是 4 字节，要知道在网络数据传输中是寸土寸金的，这个字符串格式的 IP 地址通常是显示给用户看的（例如`ifconfig`指令）。

---

在定义好`sockaddr_in`结构体对象后，对其进行初始化是为了确保其成员变量的值是确定的。如果不进行初始化，那么这些成员变量的值将是不确定的，可能会导致程序出现错误。

通常情况下，我们会使用`memset()`或`bzero()`函数来将`sockaddr_in`结构体对象的空间清零。这样可以确保其成员变量的值都为 0。

由于`memset()`我们较为熟悉，所以下面使用一下陌生的`bzero()`。

> `bzero()`函数用于将内存块（字符串）的前 n 个字节清零。它的原型为`void bzero(void *s, size_t n)`，其中`s`为内存（字符串）指针，`n`为需要清零的字节数。
>
> 值得注意的是，`bzero()`函数已经被弃用（在 POSIX.1-2001 中标记为 LEGACY），并且在 POSIX.1-2008 中被删除了。在新程序中，建议使用`memset()`函数来代替`bzero()`函数。
>

下面是绑定和差错处理的逻辑：

```cpp
bool initServer()
{
    // 1. 创建套接字
    // ... 
    // 2. 绑定：将用户设置的 IP 和 PORT 在内核中与当前进程强关联
    // 2.1 填充属性
    struct sockaddr_in local;
    bzero(&local, sizeof(local));
    local.sin_family = AF_INET;
    local.sin_port = htons(_port);
    local.sin_addr.s_addr = _ip.empty() ? INADDR_ANY : inet_addr(_ip.c_str());
    if(bind(_sockfd, (struct sockaddr *)&(local), sizeof(local)) < 0)
    {
        logMessage(FATAL, "bind():errno:%d:%s", errno, strerror(errno));
        exit(2);
    }
	logMessage(NORMAL, "initialize udp server...%s", strerror(errno));
    return true;
}
```

注意：

- 在设置 PORT 属性时，注意要保证它是大端序列的。

- IP 地址被封装了好几层，它的结构层次是：`struct sockaddr_in [sin_addr]`->`struct in_addr [s_addr]`->`in_addr_t [s_addr]`->`uint32_t [s_addr]`。

- 注意此时构造函数中的`_ip`的缺省值被设置为`""`，表示空串，如果为空则设置为`INADDR_ANY`，表示接收来自任意 IP 地址的数据；否则只能接收特定 IP 地址的发送的数据（缺省值）。

- `inet_addr()`函数用于将 IPv4 点分十进制地址字符串转换为网络字节顺序的二进制数据。它的原型为`unsigned long inet_addr(const char *cp)`，其中`cp`是一个以点分十进制表示法表示的 IPv4 地址字符串。

  > 如果输入的字符串格式不正确，`inet_addr()`函数将返回`INADDR_NONE`（通常为-1）。需要注意的是，由于-1 是一个有效的地址（255.255.255.255），因此使用这个函数可能会有问题。建议避免使用这个函数，而使用其他函数，如`inet_pton()`。在此为了接口名称上的统一，使用了前者。

- 在调用 bind() 函数时，第二个参数注意要类型转换为`struct sockaddr *`类型。

- 在执行 bind() 函数之前，定义的数据包`local`是一个局部对象，因此它是被存储在栈区的。通过 bind() 函数，这个局部对象中的属性就会被内核绑定。

自此服务器初始化的操作已经完成一半，测试一下：

<img src="./网络编程：UDP socket.IMG/image-20230430000153690.png" alt="image-20230430000153690" style="zoom:33%;" />

## 运行服务端

UDP 的服务端的初始化非常简单，只要创建套接字并绑定用户提供的 IP 地址和端口号到内核即可，剩下的操作将由操作系统协助完成。只要启动服务端进程，就能直接接收客户端发送的数据。

所谓网络服务器，在正常情况下它的进程应该是永不退出的，也就是服务器的逻辑应该在一个死循环中执行，我们把这样的进程叫做常驻进程，即一直存在于内存中（除非它挂了或者宕机）。因此使用 C/C++实现服务器的逻辑应该尽量杜绝内存泄漏问题。

### 读取数据

`recvfrom()`函数用于从套接字接收消息。它可以用于连接模式或非连接模式的套接字，并且通常与非连接模式套接字一起使用，因为它允许应用程序检索接收数据的源地址。

```c
ssize_t recvfrom(int sockfd, void *buf, size_t len, int flags, 
                 struct sockaddr *src_addr, socklen_t *addrlen)
```

参数：

- sockfd 是套接字文件描述符。只要在初始化服务器逻辑中创建套接字成功，并填入了信息，那么这个函数就能通过它（网络文件）获取信息。
- buf 指向用于存储消息的缓冲区。
- len 指定缓冲区的长度（以字节为单位）。
- flags 指定消息接收类型。通常设置为`0`，表示进程以阻塞方式读取数据。
- src_addr 是一个指向`sockaddr`结构体的指针，用于存储发送地址（如果协议提供了源地址）。这是属于数据本身之外的信息。
- addrlen 是一个值-结果参数，调用者应在调用前将其初始化为与`src_addr`关联的缓冲区的大小，并在返回时修改为实际源地址的大小。

返回值：

- 成功：返回写入缓冲区的消息长度。如果消息太长而无法放入提供的缓冲区，则根据从中接收消息的套接字类型，可能会丢弃多余的字节。
- 失败：返回-1，设置错误码。

---

#### 参数解读

在客户端-服务端模式中，服务端除了使用 recvfrom() 函数获取数据本身之外，还要获取客户端的 IP 地址和端口号，反之也是如此。因此后两个参数起着非常大的作用：

- `src_addr`：`sockaddr`类型的**输出型参数**。用于服务端获取客户端的 IP 地址和端口号；如果它的值为`NULL`，那么表示客户端的底层协议没有提供源地址，因此`addrlen`也将会为`NULL`。
- `addrlen`：`unsigned int`类型的==输入输出型参数==：
  - 作为参数时：指定 recvfrom() 函数读取数据的长度；
  - 作为返回值时：返回源地址的实际大小。

> 到目前为止，这个输入输出型参数是第一次遇见，感觉好妙。

### 处理数据

实现回显（echo）功能：其实就是将接收到的数据打印出来。

### 向客户端发送响应数据

这个步骤是必要的，向客户端发送响应数据是为了让客户端知道它的请求已被服务器接收并处理。这样客户端就可以根据服务器的响应来执行下一步操作，例如更新界面或显示错误信息。而且客户端也可能需要获取服务端处理的结果。

实现回声服务器，就是将客户端发送的数据原封不动地返回。

`sendto`是 Linux 中用于发送数据的系统调用之一。它用于在无连接的套接字（如 UDP 套接字）上发送数据。`sendto`函数的原型如下：

```c
ssize_t sendto(int sockfd, const void *buf, size_t len, int flags,
               const struct sockaddr *dest_addr, socklen_t addrlen);
```

参数：

- `sockfd`是要发送数据的套接字描述符。
- `buf`是指向要发送数据的缓冲区。
- `len`是要发送数据的长度。
- `flags`用于指定发送操作的一些选项。默认设置为`0`。
- `dest_addr`是指向目标地址结构体的指针，用于指定数据发送的目标地址。
- `addrlen`是目标地址结构体的长度。

返回值：

- 成功：返回实际发送的字节数。
- 失败：返回-1，并设置相应的错误码。

> 除了最后一个参数不是指针类型以外，这个函数的参数和`recvfrom`是一样的。

---

下面是服务端运行的逻辑：

```cpp
void Start()
{
    char buffer[SIZE]; // 用来存放读取的数据
    for(;;)
    {
        struct sockaddr_in peer; // 客户端属性集合 [输出型参数]
        bzero(&peer, sizeof(peer)); // 初始化空间
        // 输入：peer 缓冲区的大小；
        // 输出：实际读到的 peer 大小 [输入输出型参数]
        socklen_t len = sizeof(peer); 
        // 1. 读取数据
        ssize_t s = recvfrom(_sockfd, buffer, sizeof(buffer), 0, 
                            (struct sockaddr*)&peer, &len);
        // 2. 处理数据 - echo
        if(s > 0)
        {
            buffer[s] = 0; // 把数据当做字符串
            // 2.1 输出数据的属性
            // 数据从网络中来，网络字节序->主机字节序
            std::string client_ip = inet_ntoa(peer.sin_addr); 
            uint16_t client_port = ntohs(peer.sin_port);
            // 2.2 打印数据来源及数据本身
            printf("[%s:%d]# %s\n", client_ip.c_str(), client_port, buffer);
        }
        // 3. 写回数据
        sendto(_sockfd, buffer, sizeof(buffer), 0, 
              (struct sockaddr*)&peer, len);
    }
}
```

测试一下：

```cpp
int main(int argc, char* argv[])
{
    // ...
    std::unique_ptr<UdpServer> server_ptr(new UdpServer(port, ip));
    
    server_ptr->initServer();
    server_ptr->Start(); // 执行 Start()
    return 0;
}
```

<img src="./网络编程：UDP socket.IMG/image-20230430135925106.png" alt="image-20230430135925106" style="zoom:33%;" />

注意，只有客户端对服务端进程发送数据，`recvfrom()`函数才会读取成功，返回值才会大于零，处理数据的逻辑才会执行。

### 关闭文件描述符

在定义`UdpServer`类的时，在析构函数中调用`close()`函数关闭。

# 客户端

实现一个 UDP 客户端通常需要以下步骤：

1. 创建一个 UDP 套接字，可以使用`socket`函数来完成。
2. （可选）如果需要，可以使用`bind`函数将套接字绑定到一个特定的地址和端口。
3. 准备要发送的数据，并使用`sendto`函数将数据发送到服务器。
4. 使用`recvfrom`函数接收服务器的响应数据。
5. 处理接收到的响应数据。
6. 重复步骤 3-5，直到通信完成。
7. 使用`close`函数关闭套接字。

以上是一个简单的 UDP 客户端实现的基本步骤，和服务端的实现非常类似。根据具体需求，可以在这些步骤中添加更多的逻辑和处理。

## 定义

客户端的逻辑将被定义在`UdpClient.cc`中，它包含了头文件`UdpClient.hpp`。

而且客户端使用各种 socket 接口的操作将被封装为一个`UdpClient`类，这个类型的对象就可以被称之客户务端。它将在头文件中被定义，在源文件中被使用。

下面是类和主体逻辑的框架：

```cpp
// UdpClient.hpp
class UdpClient
{
public:
    UdpClient(uint16_t port, std::string ip = "")
    : _ip(ip)
    , _port(port)
    , _sockfd(-1)
    {}
    ~UdpClient()
    {
        if(_sockfd >= 0) close(_sockfd);
    }
private:
    uint16_t _port;     // 端口号
    std::string _ip;    // IP 地址
    int _sockfd;        // 套接字文件描述符
};
```

注意：

- 对于客户端，它寻求的是服务端的服务，因此需要知道服务端的 IP 和 PORT。这里提前将文件描述符的关闭操作写在了析构函数内。
- 在运行客户端程序输入的 IP 和 PORT 应该是被指定的服务端的地址，因此服务端的 IP 地址可以不赋予缺省值。

```cpp
// UdpClient.cc
#include "UdpClient.hpp"
#include <memory>
#include <cstdio>

static void usage(std::string proc)
{
    std::cout << "\nUsage: " << proc << " [IP] [PORT]\n" << std::endl;
}
// 指令：{ ./UdpClient [IP] [PORT] }
int main(int argc, char* argv[])
{
    if(argc != 3)
    {
        usage(argv[0]);
        exit(1);
    }

    std::string ip = argv[1];
    uint16_t port = atoi(argv[2]);
    std::unique_ptr<UdpClient> client_ptr(new UdpClient(port, ip));
    
    return 0;
}
```

类似地，需要提取命令行参数，然后将它们作为参数传递给类`UdpClient`的构造函数中，以便后续使用。

## 创建套接字

客户端创建套接字的逻辑和服务端是一样的：

```cpp
bool initClient()
{
    // 1. 创建套接字
    _sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if(_sockfd < 0)
    {
        logMessage(FATAL, "%d:%s", errno, strerror(errno));
        exit(2);
    }
    logMessage(DEBUG, "%s: %d", "create socket success, sockfd", _sockfd);

    return true;
}
```

## 绑定

按照常理，不论是客户端还是服务端，除了数据本身，IP 地址和 PORT 对它们都是有用的，bind 到内核也是合理的。但是它们面向的用户群体不同，服务端面向的是程序员，客户端面向的是用户。而客户端是被很多人使用的，每个人的机器上肯定有不止一个客户端进程在运行，我们知道，端口号标识着一台机器中进程的唯一性，即在一台机器中一个端口号只能被一个进程占用，因此，如果客户端自己将端口号 bind 到内核，而其他客户端进程可能也需要这个端口号，那么它就会导致其他进程无法正常工作。

所以程序员在设计客户端逻辑时，一般不会手动地绑定 IP 地址和 PORT（尤其），而是让操作系统随机选择 PORT。也就是说，bind 操作一定会被执行，只不过客户端中执行它的主题是操作系统。

> 操作系统什么时候会执行 bind?

当客户端第一次使用`sendto`函数发送数据时，如果套接字没有绑定到特定的地址和端口，操作系统会在内部自动执行一个隐式的`bind`操作，为套接字分配一个临时的端口。这个过程对程序员是透明的，不需要程序员手动调用`bind`函数。

这个临时端口是由操作系统动态分配的，通常是在动态端口范围内选择一个未被占用的端口。客户端可以使用这个临时端口来接收服务器的响应数据。

## 发送数据

省去了 bind 操作，UDP 的客户端就只要发送数据给服务端即可。发送数据的前提是要获取服务器的 IP 和 PORT，它将从命令行参数中被提取。

`sendto()`函数的使用方法在服务端已经介绍过，在使用它传输数据之前。和服务端一样，要事先定义一个`sockaddr_in`类型的数据包，然后将获取到的 IP 地址和端口号以及传输方式填充进这个结构体中，在传参时类型转换为`sockaddr*`即可。

```cpp
void Start()
{
    // 3. 发送数据
    struct sockaddr_in server;                       // 创建数据包
    memset(&server, 0, sizeof(server));              // 初始化为 0
    server.sin_family = AF_INET;                     // 指定通信协议
    server.sin_addr.s_addr = inet_addr(_ip.c_str()); // 将点分十进制的 IP 字符串转化为二进制的网络字节序
    server.sin_port = htons(_port);                  // 主机字节序->网络字节序
    std::string message;
    while (1)
    {
        std::cout << "请输入信息# ";
        std::getline(std::cin, message); // 输入数据
        if (message == "quit")
            break;
        // 3.1 发送数据
        sendto(_sockfd, message.c_str(), message.size(), 0,
               (struct sockaddr *)&server, sizeof(server));
    }
}
```

注意：

- 这里使用了较为规范的`memset()`将结构体 server 中的值设置为 0。
- 设置了退出分支。

## 接收服务器的响应数据

到目前为止，客户端已经完成了“要向谁发送数据”这个操作，客户端可能会需要服务端执行的结果，因此客户端也要接收服务器的响应数据。

> 客户端和服务端是相对的。

但是在本次的实验中，我们实现的回声服务器并未对数据进行处理，客户端也就没有接收服务端返回的数据的必要，不过为了规范性，仍然使用`recvfrom()`函数接收服务端传回的数据。形式上可以定义一个结构体接收数据，充当占位符的作用。

```cpp
#define SIZE 1024
void Start()
{
    // 3. 发送数据
    // ...
    char buffer[SIZE];
    while (1)
    {
        // ...
        // 4. 处理服务器返回的响应数据
        // 4.1 定义一个临时结构体
        struct sockaddr_in tmp;
        socklen_t len = sizeof(tmp);
        ssize_t s = recvfrom(_sockfd, buffer, sizeof(buffer), 0,
                             (struct sockaddr *)&tmp, &len);
        if (s > 0)
        {
            buffer[s] = 0;
            std::cout << "server echo# " << buffer << std::endl;
        }
        // else 省略差错处理
    }
}
```

注意：

- 尽管`tmp`只是起着占位符的作用，在这个回声程序中也不会再使用它，但是不能将它设置为`NULL/nullptr`，这是因为`recvfrom()`函数在内部会对它解引用并修改它的值。
- 服务端返回的响应数据对于客户端是有用的，那么这个`tmp`中的成员就会被填充，就能在客户端中取出并使用。
- 在打印返回的数据时，`recvfrom()`的返回值是返回的数据的大小，`buffer[s] = 0`表示将字符串中的最后一个元素设置为`\0`，这样打印时就不会出现问题。

> `for(;;)`和`while(1)`都可以用来实现无限循环。它们的效果是相同的，都会一直执行循环体中的代码，直到遇到`break`语句或其他跳出循环的语句。
>
> 在实现服务器逻辑时，使用`for(;;)`或`while(1)`都是可以的。两者之间没有本质区别，选择哪种写法主要取决于个人习惯和编码风格。
>
> 有些程序员更喜欢使用`for(;;)`，因为它更简洁，也更容易让人一眼看出这是一个无限循环。而有些程序员则更喜欢使用`while(1)`，因为它更符合自然语言的表达方式。 

## 关闭文件描述符

在定义`UdpClient`类的时，在析构函数中调用`close()`函数关闭。

# 测试 1

## 本地环回

本地环回（Loopback）是指一种网络接口，它可以将发送的数据返回给发送者，而不是将数据发送到外部网络。

在大多数操作系统中，本地环回接口的 IP 地址为`127.0.0.1`，主机名为`localhost`。当应用程序向这个地址发送数据时，数据不会离开主机，而是直接返回给发送者。这样，应用程序就可以在不依赖外部网络的情况下进行测试和调试。

### 作用

本地环回接口通常用于测试和诊断网络应用程序。由于本地环回接口可以将发送的数据返回给发送者，因此可以用来测试应用程序的网络功能，而无需连接到外部网络。

例如，开发人员可以在本地计算机上同时运行客户端和服务器程序，并使用本地环回接口进行通信。这样，开发人员就可以在不依赖外部网络的情况下测试客户端和服务器之间的通信功能。

此外，本地环回接口还可以用来测试网络协议栈的功能，以及诊断网络配置问题。

也就是说，通过本地环回传输数据，数据的传输只会从上至下、从下至上地经过协议栈，而不会经过网络。

## 本地测试

在下面的测试中，可以使用`127.0.0.1`本地环回地址测试一下上面写好的服务端和客户端程序。端口号随便设置，在这里设置为`8080`。

注意，上面的代码中使用了日志，有的日志级别是`DEBUG`，在测试中可以在编译选项中加上`DDUBUG_SHOW`以更好地观察现象，这是一个自定义预处理命令。

<img src="./网络编程：UDP socket.IMG/屏幕录制 2023-04-30 17.49.17.gif" alt="屏幕录制 2023-04-30 17.49.17" style="zoom:50%;" />

注意：首先要将服务端运行起来。通过实验结果来看，简易的回声服务端就被实现了，服务端将会在自己的进程中打印客户端发送的数据，并将数据原封不动地返回给客户端，`server echo#`后面的内容就是客户端返回的数据。

## netstat 指令

`netstat`是一个用于显示网络状态信息的命令行工具。它可以显示各种网络相关的信息，包括活动的网络连接、路由表、接口统计信息等。

`netstat`命令有许多选项，可以用来控制显示的信息类型和格式。例如，可以使用`-a`选项来显示所有活动的网络连接，使用`-r`选项来显示路由表，使用`-i`选项来显示网络接口信息等。

下面是一些常用的`netstat`命令示例：

- `netstat -a`：显示所有活动的网络连接。
- `netstat -at`：显示所有活动的 TCP 连接。
- `netstat -au`：显示所有活动的 UDP 连接。
- `netstat -l`：显示正在监听的套接字。
- `netstat -r`：显示路由表。
- `netstat -i`：显示网络接口信息。

以上是对`netstat`命令的简要介绍。更多详细信息可以参考相关文档或使用`man netstat`命令查看手册页。

### 使用

可以用这个工具查看刚才的程序对应的网络信息：

<img src="./网络编程：UDP socket.IMG/image-20230430175930009.png" alt="image-20230430175930009" style="zoom:33%;" />

再测试一次：

<img src="./网络编程：UDP socket.IMG/image-20230430180151102.png" alt="image-20230430180151102" style="zoom:33%;" />

可以看见，两次客户端的端口号都是不一样的，这说明操作系统自动绑定的端口号是不确定的。

## 公网 IP 问题

对于一台云服务器，它的公网 IP 通常是由云服务提供商提供的虚拟公网 IP。这个虚拟公网 IP 并不是服务器真正的物理 IP 地址，而是通过网络地址转换（NAT）技术映射到服务器的私有 IP 地址上。

使用虚拟公网 IP 的主要原因是 IPv4 地址资源的紧缺。由于 IPv4 地址空间有限，全球可用的 IPv4 地址已经基本分配完毕。为了解决这个问题，云服务提供商通常会使用 NAT 技术，将一个公网 IP 地址映射到多台云服务器上，从而实现 IP 地址的复用。

此外，使用虚拟公网 IP 还可以提供更好的安全性和灵活性。由于服务器的真实 IP 地址对外不可见，因此可以有效防止直接攻击。同时，云服务提供商还可以通过调整 NAT 映射规则来快速更换服务器的公网 IP 地址，以应对不同的网络需求。

### 测试

如果将服务器的构造函数中 IP 的默认值保持`""`或不设置缺省值，然后在绑定之前的 IP 地址填充操作改为`local.sin_addr.s_addr = inet_addr(_ip.c_str())`，表示以用户设置的 IP 地址填充。

我的服务器厂商提供的虚拟公网 IP 地址是`8.130.106.177`，那么直接使用刚才的程序：

<img src="./网络编程：UDP socket.IMG/image-20230430185800258.png" alt="image-20230430185800258" style="zoom:50%;" />

服务端无法绑定，这是因为提供的 IP 地址不是物理上真正的 IP 地址。客户端一直处于阻塞状态，原因是陷入了`recvfrom()`无法退出（这可以通过在这个函数前后打印语句判断）。

原因是在云服务器中，`bind()`函数无法绑定一个具体的（公网）IP 地址，也不建议。如果没有这样的限制，那么在服务器的初始化中，`bind()`函数只会被调用一次，那么第一次绑定时应该会成功将用户提供的 IP 地址和 PORT 成功绑定到内核中，那么就意味着这个客户端只能接受来自特定的 IP 地址和特定端口号对应的进程发送的数据，在绝大多数情况下都不会有这样的需求，因为服务器面向的是多个客户端。

所以在服务端（尤其）和客户端的构造函数中赋予 IP 地址以缺省值`""`，然后在绑定之前的 IP 地址填充操作设置用这样的逻辑控制：`local.sin_addr.s_addr = _ip.empty() ? INADDR_ANY : inet_addr(_ip.c_str())`，这样就能兼容上述两种情况了。

### INADDR_ANY

注意`INADDR_ANY`，它的本质是一个值为`0`的宏，定义如下：

```c
/* Address to accept any incoming messages.  */
#define	INADDR_ANY		((in_addr_t) 0x00000000)
```

当服务器端的 IP 地址设置为`INADDR_ANY`时，意味着服务器将监听所有可用的网络接口上的客户端连接请求。也就是说，无论客户端使用哪个 IP 地址来连接服务器，服务器都能够接受连接。

在这种情况下，如果服务器所在的主机拥有多个 IP 地址（包括虚拟 IP 地址），那么客户端可以使用任意一个 IP 地址来连接服务器。服务器会自动处理来自不同 IP 地址的客户端连接请求。

#### 优点

将服务器端的 IP 地址绑定到`INADDR_ANY`有以下几个好处：

1. 简化配置：当服务器所在的主机拥有多个网络接口和 IP 地址时，如果要监听所有接口上的客户端连接请求，需要为每个接口单独绑定 IP 地址。而使用`INADDR_ANY`可以简化这个过程，只需一次绑定操作即可监听所有接口。

   > 对于网络传输的 IO 效率，除了带宽以外最大的限制因素就是机器接收数据的能力。因此一台服务器可能装有多张网卡，每张网卡都有对应的 IP 地址，但是一个端口号只能对应一个进程。如果服务端接收到的数据指定了端口号进程的服务，而服务端绑定的也是`INADDR_ANY`，那么所有网卡都会一起工作，提高效率；反之服务器绑定的是某个特定网卡的 IP 地址，那么服务端进程在接收数据时，只能由那个特定的网卡呈递数据，效率就显得更低。

2. 提高灵活性：使用`INADDR_ANY`可以让服务器自动适应网络环境的变化。例如，当服务器所在的主机的网络配置发生变化时，服务器无需重新绑定 IP 地址，仍然可以正常接受客户端连接请求。

3. 支持多种访问方式：当服务器绑定到`INADDR_ANY`时，客户端可以使用多种方式来访问服务器。例如，客户端可以使用服务器的公网 IP 地址、私有 IP 地址或本地环回地址来连接服务器，服务器都能够正常处理客户端的连接请求。

以上是将服务器端的 IP 地址绑定到`INADDR_ANY`的一些好处。当然，这种做法也有一些局限性，例如无法限制客户端只能使用特定的 IP 地址来连接服务器。因此，在实际应用中需要根据具体需求来决定是否使用`INADDR_ANY`。

在上面的测试中，被绑定的 IP 地址设置为`0`，查看进程网络信息时就能看到它的 IP 地址的值为 0。<img src="./网络编程：UDP socket.IMG/image-20230430191914226.png" alt="image-20230430191914226" style="zoom:50%;" />

因此服务端的逻辑中 IP 地址就不用填充到结构体中了。

## 网络测试

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/UdpSocket/SingleProcess)

网络测试可以再同一台主机上，也可以在不同主机上。

首先说不同主机，可以使用`sz`命令将实现的可执行程序传输到本地计算机，然后发送给别人。为了保证程序在不同机器上能够运行，可以在编译客户端程序时增加`-static`选项，表示静态编译。当然也可以让朋友用源文件在他的机器上编译。如果别人要使用导入的可执行程序，需要用`chmod +x`修改权限。

下面将在一台主机上进行网络测试，需要用到运营商提供的私有 IP，和用本地环回地址测试不同，私有 IP 能实现在一台主机上进行网络测试，能降低网络测试的成本。

> 云服务器提供的私有地址不是公网 IP 地址。私有地址是指在云服务提供商的内部网络中使用的 IP 地址，它只能在云服务提供商的内部网络中访问，无法从外部网络直接访问。
>
> 私有地址通常用于云服务器之间的内部通信，例如在同一虚拟私有云（VPC）内的云服务器之间进行数据传输。由于私有地址只能在内部网络中访问，因此可以提供更好的安全性和隔离性。
>
> 如果需要从外部网络访问云服务器，需要使用公网 IP 地址。公网 IP 地址是指在 Internet 上可以访问的 IP 地址，可以通过网络地址转换（NAT）技术将公网 IP 地址映射到云服务器的私有地址上，从而实现外部网络对云服务器的访问。

例如运营商提供给我的私有 IP 是`172.17.177.235`：

<img src="./网络编程：UDP socket.IMG/屏幕录制 2023-04-30 21.43.41.gif" alt="屏幕录制 2023-04-30 21.43.41" style="zoom:50%;" />

# 解析命令版

上面实现了一个简单的回声服务器，是将数据看作字符串的。有时候客户端发送的数据中可能包含让对端主机执行任务的语句（例如`ls -a -l`），那么就要对字符串进行分割，然后在服务器中调用字符串对应的指令。这里的字符串分割当然可以自己实现，但本节的终点是实现功能，实际上也是直接把成熟的工具或框架拿来用，这样能保证安全性。

## popen 函数

`popen`是一个 Linux 函数，用于通过创建管道、分叉和调用 shell 来打开进程。由于管道本质上是单向的，因此`type`参数只能指定读取或写入，不能同时指定两者；因此，所得到的流分别是只读或只写的。

```c
#include <stdio.h>

FILE *popen(const char *command, const char *type);

int pclose(FILE *stream);
```

参数：

- command 参数是一个指向以空字符结尾的字符串的指针，其中包含一个 shell 命令行。该命令使用-c 标志传递给/bin/sh；解释（如果有）由 shell 执行。
- type 参数是一个指向以空字符结尾的字符串的指针，其中必须包含字母`'r'`（用于读取）或字母`'w'`（用于写入）。

返回值：

从 popen() 返回的值是一个正常的标准 I/O 流，除了它必须使用`pclose()`而不是 fclose(3) 关闭。向这样的流写入会将数据写入命令的标准输入；命令的标准输出与调用 popen() 的进程相同，除非命令本身更改了这一点。相反，从流中读取会读取命令的标准输出，并且命令的标准输入与调用 popen() 的进程相同。

> 不可以直接对字符串进行分析，然后调用字符串对应的指令吗？为什么要先用 popen 打开这个缓冲区？

当然可以直接分析字符串并调用相应的指令，但是`popen`函数提供了一种更方便的方法来执行这些操作。使用`popen`函数，您可以在脚本中运行程序并对其执行 I/O 操作，而无需手动创建管道、分叉和调用 shell。这样可以简化代码，并使其更容易阅读和维护。

此外，`popen`函数还提供了一些其他优点。例如，它允许用户从脚本中读取程序的输出或向程序写入输入，而无需手动管理管道和进程间通信。这样可以让用户更快速、更容易地实现复杂的功能。

---

在这段代码中，`popen`函数用于执行客户端发送的命令。服务器从客户端接收数据并将其存储在`buffer`中，然后使用`popen`函数打开一个进程来执行命令。`popen`函数通过创建管道、分叉和调用 shell 来打开进程，以便在脚本中运行程序并对其执行 I/O 操作。

如果命令包含非法指令（例如`rm`或`rmdir`），服务器将向客户端发送一条错误消息并继续读取数据。否则，服务器将读取命令的输出并将其存储在`cmd`字符串中。最后，服务器使用`sendto`函数将命令的输出发送回客户端。

```cpp
#define SIZE 1024
void Start()
{
    char buffer[SIZE]; // 用来存放读取的数据
    char result[256];  // 保存处理结果
    std::string cmd;   // 保存命令，用于回写
    for (;;)
    {
        struct sockaddr_in peer;    // 客户端属性集合 [输出型参数]
        bzero(&peer, sizeof(peer)); // 初始化空间
        socklen_t len = sizeof(peer);
        // 1. 读取数据
        ssize_t s = recvfrom(_sockfd, buffer, sizeof(buffer), 0,
                             (struct sockaddr *)&peer, &len);
        // 2. 处理数据：提取缓冲区中的命令
        if (s > 0)
        {
            buffer[s] = '\0';
            FILE *fp = popen(buffer, "r");
            if (fp == nullptr) // 读取失败
            {
                logMessage(ERROR, "popen: %d:%s", errno, strerror(errno));
                continue; // 继续读取
            }
            // 过滤非法指令
            if (strcasestr(buffer, "rm") != nullptr || strcasestr(buffer, "rmdir") != nullptr)
            {
                std::string err_msg = "非法指令：rm/rmdir...";
                std::cout << err_msg << buffer << std::endl;
                sendto(_sockfd, err_msg.c_str(), err_msg.size(), 0,
                       (struct sockaddr *)&peer, len);
            }
            while (fgets(result, sizeof(result), fp) != nullptr)
            {
                cmd += result;
            }
            pclose(fp);
        }
        // 3. 写回数据
        sendto(_sockfd, cmd.c_str(), cmd.size(), 0,
               (struct sockaddr *)&peer, len);
    }
}
```

在这段代码中，`popen`函数用于执行客户端发送的命令并获取命令的输出，以便服务器可以将其发送回客户端。

注意：

- 逻辑中使用了`strcasestr()`函数来查找子串。以过滤非法指令。

## 测试

<img src="../../../../var/folders/rn/x47kmrnj7v31hpbbfhlzd2m00000gn/T/com.sindresorhus.Gifski/TemporaryItems/NSIRD_Gifski_NEs8Xj/屏幕录制 2023-04-30 23.02.07.gif" alt="屏幕录制 2023-04-30 23.02.07" style="zoom:50%;" />

> 这个程序在缓冲区中还是有一些问题，如果频繁输入不存在的命令将会使`popen()`函数处于阻塞状态。
>
> 如果客户端发送了`rm`或`rmdir`等非法指令，那么客户端将会记录错误信息，并直接返回错误信息。
>
> <img src="./网络编程：UDP socket.IMG/image-20230430231042147.png" alt="image-20230430231042147" style="zoom:50%;" />

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/UdpSocket/SingleProcess_command)--实际上只修改了`UdpServer.hpp`中成员函数`Start()`的逻辑，为了方便编译依然将所有文件打包。（实际上也能打包成一个库以供别人使用，不过这样的话就没办法看到代码中的细节了）

# 群聊版（单进程）

上面的例子是一个服务端进程对应一个客户端进程，要实现群聊版的服务端程序，（想象我们在群里的情景）其实就是将每个用户发送的数据在客户端中收集起来，然后统一发送给每一个客户端。这样就实现了全员广播通信，从效果上看，每个客户端能看见自己和别人发送的信息。

## 用户管理

在这里，使用 STL 中的哈希表（也就是`unordered_map`）保存用户的信息，以不同客户端的 IP 和 PORT 来标识它们的身份，如果可能的话，我们可以将 IP 地址与用户设置的昵称映射起来，这就是我们在一个新网站注册的行为。

哈希表被保存在`UdpServer`类的成员属性中。

```cpp
#include <unordered_map>
class UdpServer
{
private:
	// ...
    std::unordered_map<std::string, struct sockaddr_in> _users; // 用户信息
};
```

## 新增用户

通过`recvfrom()`函数获取客户端发送过来的数据包`peer`，然后提取出它里面包含的客户端 IP 和 PORT，并将它们拼接在一起，以字符串的格式写入到缓冲区`info[]`中。

在哈希表中查找`info[]`对应的元素，如果不存在的话，说明此时的`info[]`就是新元素，插入到哈希表中。

```cpp
void Start()
{
    char buffer[SIZE]; // 用来存放读取的数据
    char info[64];     // 用来存放客户端的数据：IP 和 PORT
    for (;;)
    {
        struct sockaddr_in peer;
        memset(&peer, 0, sizeof(peer));
        socklen_t len = sizeof(peer);
        // 1. 读取数据
        ssize_t s = recvfrom(_sockfd, buffer, sizeof(buffer), 0,
                             (struct sockaddr *)&peer, &len);
        // 2. 处理数据：提取缓冲区中的命令
        if (s > 0)
        {
            buffer[s] = '\0';
            // 方便显示，将 4 字节网络字节序->字符串格式主机字节序
            std::string client_ip = inet_ntoa(peer.sin_addr);
            uint16_t client_port = ntohs(peer.sin_port); // 字节序：网络->主机
            // 将客户端的 IP 和 PORT 以特定格式写入 info[] 中
            snprintf(info, sizeof(info), "[IP:%s : PORT:%u]", client_ip.c_str(), client_port);
            // 找不到 info 对应的元素，说明这个元素还未被添加到哈希表
            auto it = _users.find(info);
            if (it == _users.end())
            {
                logMessage(NORMAL, "add new user: %s...success", info);
                _users.insert({info, peer}); // 插入哈希表中
            }
        }
	}
}
```

注意：

- 这是在类中的成员函数，因此仍然以字符串格式的 IP 地址处理。客户端传递的数据包是从网络接收的，因此要将网络字节序转为主机字节序。
- `buffer[s] = '\0'`和`buffer[s] = 0`是等价的（`'\0'`的 ASCII 码为`0`），前者更规范些。

## 向客户端发送响应数据

客户端记录服务端的信息就是以键值对`<IP+PORT, 数据包>`保存在哈希表中，由于要向客户端发送响应数据，因此除了返回数据本身之外，还要将用户的信息和数据本身拼接起来一起返回。

```cpp
void Start()
{
    char buffer[SIZE]; // 用来存放读取的数据
    char info[64];     // 用来存放客户端的数据：IP 和 PORT
    for (;;)
    {
        // 1. 读取数据。..
        // 2. 处理数据。..
        
        // 3. 处理数据
        for (auto& iter : _users) // 遍历哈希表
        {
            // 3.1 将客户端的信息和数据本身拼接起来
            // 格式：[IP][PORT]# [信息]
            std::string sendMessage = info;
            sendMessage += "# ";
            sendMessage += buffer;
            logMessage(NORMAL, "return [info+data] to user:%s", iter.first.c_str());
            // 3.2 写回数据
            sendto(_sockfd, sendMessage.c_str(), sendMessage.size(), 0,
                   (struct sockaddr *)&(iter.second), sizeof(iter.second));
        }
    }
}
```

## 测试

下面将用 2 个客户端和 1 个服务端进行测试。

<img src="./网络编程：UDP socket.IMG/屏幕录制 2023-05-01 15.14.35.gif" alt="屏幕录制 2023-05-01 15.14.35" style="zoom:50%;" />

但是这并不是我们想象中的群聊，这里只有发送信息的客户端才能收到自己发送的消息，而不会立刻显示另一个客户端发送的消息，而是在回显自己发送的几条信息之后才显示。而且我们通过服务端的日志可以看到，实际上客户端是有将每条接收到的数据发送给两个客户端的：

<img src="./网络编程：UDP socket.IMG/image-20230501151941073.png" alt="image-20230501151941073" style="zoom:50%;" />

出现这样的情况的原因并非客户端拒绝了服务端进程发送的消息，而是 IO 被阻塞了。在上面的客户端程序中，使用的是`getline()`函数获取用户输入的数据，也就是从标准输入读取数据，那么如果数据没有流向标准输入，`getline()`后面的逻辑都不会被执行，程序将会在`getline()`一直等待标准输入的数据。对于群聊中的每一个客户端，它们接收消息和发送消息应该是互不干扰的，就像我们在群里聊天一样。

> 最主要的原因是，单进程执行任务，只要在任意地方发生阻塞，而恰好客户端读取用户输入信息的逻辑必须要在死循环内部（表示不断读取），因此`getline()`阻塞会造成整个客户端的 IO 发生阻塞。

因此我们可以考虑使用多线程，各自负责输入和输出的操作，这样接收消息和发送消息就可以并发地执行。

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/UdpSocket/SingleProcess_GroupChat)--实际上只修改了`UdpServer.hpp`中成员函数`Start()`的逻辑，为了方便编译依然将所有文件打包。

# 群聊版（多线程）

对于上面实现的群聊版的服务端，它的逻辑是没有问题的，问题就在于只用一个进程同时实现客户端发送信息和接收信息会产生 IO 阻塞，因此考虑使用多线程。这里先用 2 个线程，分别发送消息和接收消息。

既然是多线程，那么创建的套接字就是被所有执行流共享的，恰好我们用类封装了客户端，因此它作为成员变量，会被所有执行流共享。如果没有封装的话，那么就要将创建的套接字设置为全局的。

> 它是全局/被所有执行流共享，这样会产生竞争问题吗？

不会，因为套接字只会在初始状态修改它，后续只是访问它，不会对其修改，因此不会产生并发问题。

## 封装

在这篇文章中（[线程池](https://blog.csdn.net/m0_63312733/article/details/130396163?spm=1001.2014.3001.5501)），简单介绍了将`pthread`库中的多线程的操作函数封装为了一个`Thread`类，而且还将`pthread`库中的互斥锁的操作函数封装为一个（RAII 的）`Mutex`类，并用它们实现了一个简单的线程池`ThreadPool`，其中的线程函数由于并没有什么真正的需求，所以当时只在里面随便打印了一些语句作为线程函数的任务，现在这些数据从网络中来，而且也有真正的任务，因此到这里才算是线程池较为完善的实现。

> 在本小节中，只需要实现 2 个线程，因此只需要了解`Thread`类的实现即可。在文章的最后有完整的源代码。

为了管理线程资源，新增两个智能指针类型的成员属性，以便在类中供构造函数赋值、其他函数使用。

```cpp
class UdpClient
{
private:

    std::unique_ptr<Thread> send_ptr; // 指向发送数据的线程的指针
    std::unique_ptr<Thread> recv_ptr; // 指向接收数据的线程的指针
};
```

> 使用普通的指针也可以，这里只是想规范一些，而且也想使用一下 C++11 的新工具。

## 创建线程

这里创建线程的主体是客户端，目的是将发送数据和接收数据的操作解耦。

在客户端的构造函数中创建两个线程，分别代表发送数据的线程和接收数据的线程，由于线程是由`Thread`类封装的，所以可以直接用`new`操作符创建线程对象，分配空间；在客户端的构造函数中调用成员函数`start()`（其实就是调用`pthread_create()`）创建线程，并调用各自的线程函数；在客户端的析构函数中调用成员函数`join()`（其实就是调用`pthread_join()`）回收线程资源。

```cpp
class UdpClient
{
public:
    UdpClient(uint16_t port, std::string ip = "")
        : _ip(ip), _port(port), _sockfd(-1)
    {
        // 参数：[线程编号][线程函数][线程参数]
        send_ptr = std::unique_ptr<Thread>(new Thread(1, udpSend, (void *)this));
        recv_ptr = std::unique_ptr<Thread>(new Thread(2, udpRecv, (void *)this));
    }
};
~UdpClient()
{
    send_ptr->join();
    recv_ptr->join();

    if (_sockfd >= 0)
        close(_sockfd);
}
```

注意：

- 在这里智能指针作为类的成员，以缺省值的方式在定义它的同时初始化是可以的，但是个人更偏向于在构造函数中进行大部分「初始化」的操作。
- 智能指针`unique_ptr`只能被直接赋值一次（`=`），也就是第一次。在构造函数中可以通过创建一个临时对象来初始化它。
- 这里的`Thread`的构造函数的参数列表见注释。至于为什么最后一个参数是`this`指针，见下。

## 线程函数

定义两个线程函数`udpSend`和`udpRecv`，分别对应两个线程。

值得注意的是，这里的线程函数进行的是发送数据和接收数据的任务，那么就需要获取客户端的 IP 地址和 PORT，而它们恰好是类的成员。因此线程函数必须设置为类的成员函数，那么新的问题又来了。类的成员函数都有一个隐藏的`this`指针，它是每个成员函数的第一个参数，在编译时很有可能会出现（取决于具体版本）参数列表不匹配的问题，那么我们就得把这个`this`指针给去掉，因此用`static`修饰线程函数。那么新的问题又又又来了，静态成员函数只能访问静态成员变量，但显然客户端的 IP 地址和 PORT 等成员变量设置为静态会很难搞。.....

解决办法是：将 this 指针作为参数传递给线程函数，在线程函数内部就能够通过它直接访问客户端对象中的 IP 地址和 PORT 了。

> 为什么在类的内部还能传`this`指针给成员函数呢？

类的初始化工作分为两部分：

- 构造函数的初始化列表，也就是`{}`之外的部分，相当于给对象开辟了空间
- 构造函数的主体，进行初始化、赋值或其他操作。

`this`指针指向对象的起始地址。

而实现这两个线程函数最难的步骤就是如何解决上面这个问题，实际上就是将之前客户端接收和发送数据的逻辑拆分开（在成员函数`Start()`中），分别放到这两个线程函数中。

### udpSend() 线程函数

- 提取信息：由于传递给线程的参数实际上是被`ThreadData`类封装起来的（详细请看`Thread`的实现），因此首先要提取出真正的线程参数。其次由于传入的参数是指向对象的`this`指针，所以用一个指针`client_ptr`保存它，以便后续使用。
- 填充 socket 信息和发送信息的步骤和之前一模一样。

```cpp
// 发送数据的线程函数
static void *udpSend(void *args)
{
    // 准备工作：提取信息
    ThreadData *tdata = (ThreadData *)args;        // 提取线程信息
    UdpClient *client_ptr = (UdpClient *)tdata->_args; // this 指针

    // 填充 socket 信息
    struct sockaddr_in server;
    memset(&server, 0, sizeof(server));
    server.sin_family = AF_INET;
    server.sin_addr.s_addr = inet_addr(client_ptr->_ip.c_str());
    server.sin_port = htons(client_ptr->_port);

    std::string message;
    // 发送数据
    while (1)
    {
        std::cerr << "请输入信息# ";
        std::getline(std::cin, message); // 输入数据
        if (message == "quit")
            exit(3);
        sendto(client_ptr->_sockfd, message.c_str(), message.size(), 0,
               (struct sockaddr *)&server, sizeof(server));
    }
    return nullptr;
}
```

注意：

- 这里是两个线程并发地执行任务，所以如果在客户端输入`quit`，那么只会退出这个发送信息的线程，另一个线程还在不断（死循环）等待接收信息。因此我认为`quit`的含义应该是退出客户端，因此使用`exit`退出进程。

- 最后的返回值在这个客户端程序中并没有需求使用它，因此为了通过编译直接返回了`nullptr`。
- 非常需要注意的是，这里的`client_ptr`指针保存着客户端对象的起始地址，但不能因为它的名字而误以为它的成员属性 IP 和 PORT 都是客户端的。客户端在命令行输入的 IP 和 PORT 都是服务端的，它们将在构造函数中被填充。

> 注意`exit`函数终止的对象是进程而不是线程，它会使主线程（main() 进程）和所有线程都退出。

### udpRecv() 线程函数

提取信息和接收数据的操作已经介绍过，在此不再赘述。

```cpp
// 接收数据的线程函数
static void *udpRecv(void *args)
{
    ThreadData *tdata = (ThreadData *)args;
    UdpClient *client_ptr = (UdpClient *)tdata->_args;
    char buffer[SIZE];
    while (1)
    {
        struct sockaddr_in tmp;
        socklen_t len = sizeof(tmp);
        ssize_t s = recvfrom(client_ptr->_sockfd, buffer, sizeof(buffer), 0,
                             (struct sockaddr *)&tmp, &len);
        if (s > 0) // 读取成功
        {
            buffer[s] = '\0';
            std::cout << buffer << std::endl;
        }
    }
    return nullptr;
}
```

## 测试

### 本地测试

下面用两个客户端和一个服务端进行群聊测试。

```cpp
// UdpClient.cc
int main(int argc, char* argv[])
{
	// ...
    std::unique_ptr<UdpClient> client_ptr(new UdpClient(port, ip));
    
    client_ptr->initClient();
    client_ptr->Start();
    return 0;
}
```

<img src="./网络编程：UDP socket.IMG/屏幕录制 2023-05-01 19.36.33.gif" alt="屏幕录制 2023-05-01 19.36.33" style="zoom:50%;" />

注意：由于使用了`pthread`库，因此要增加编译选项：`-pthread`。

不论是读还是写的两个线程，它们使用的 socket 都是同一个，那么 sockfd 对应的就是同一个文件。常规情况下，同时对一个文件进行读写会出现问题。但是 UDP/TCP 中的 socket 是全双工的，这意味着它可以同时进行读写操作而不干扰对方线程。

### 管道测试

除了 `mkfifo` 函数之外，还有一个 `mkfifo` 命令。这个命令可以在 Linux 命令行中使用，它允许用户创建命名管道（FIFO）。它的基本语法是 `mkfifo [OPTION]... NAME...` 。

通过这个工具，我们可以在命令行中为客户端进程和服务端进程之间创建一个缓冲区，例如客户端 A 和服务端的缓冲区名称叫做`bufferA`，客户端 B 和服务端的缓冲区名称叫做`bufferB`。

缓冲区的作用是：

- 输入时：通过工具`>`将客户端输入的数据重定向到它的空间中；
- 输出时：通过工具`cat`显示服务端返回的数据。

首先创建两个缓冲区：

<img src="./网络编程：UDP socket.IMG/image-20230501201002778.png" alt="image-20230501201002778" style="zoom:33%;" />

<img src="./网络编程：UDP socket.IMG/屏幕录制 2023-05-01 20.15.32.gif" alt="屏幕录制 2023-05-01 20.15.32" style="zoom:33%;" />

通过管道作为客户端和服务端之间的缓冲区，就可以实现在专门的模块中输入（右边）和输出（中间），这样就不会像上面一样输入和输出乱成一锅粥了。

这里有一个 bug，就是缓冲区 B 不能收到客户端 A 发送的第一条数据，在测试中也就是“你好，我是客户端 A”这条消息。出现这种情况的原因是没有设计注册的逻辑，这里服务端中添加用户的逻辑是用户端发送第一条消息时判断它是不是新用户，是则添加到哈希表中。因为客户端 A 在发送这条消息时，客户端 B 还没有被添加到表中，因此服务端在群发消息时也就不回将消息发送给客户端 B 了。

<img src="./网络编程：UDP socket.IMG/image-20230501202604922.png" alt="image-20230501202604922" style="zoom:50%;" />

因此如果实现了一个注册功能，在发送信息之前就已经把用户的标识信息保存起来，在实现群聊时，即使用户没有发送过消息也能收到其他成员的消息。

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/UdpSocket/Threads_GroupChat)--修改了客户端的逻辑、Makefile 以及线程封装时格式化写入的部分逻辑。

## 优化

即使是这样，打印出来的信息也是比较混乱的，可以再进一步优化。

优化的思路基于生产消费模型，用一个队列保存信息，两个线程分别系那个队列中存入信息、从队列中取出信息并发送。这可以用一个线程池实现，也就是再让其他线程帮忙搞定队列中数据的挪动操作，这样刚才实现的两个接受数据和发送数据的线程就只要从队列中取出和存放数据就行了，这也是解耦操作。

> 也可以进一步解耦，用两个队列分别保存客户端发送的消息和客户端接收到的消息。

另外，在没有用管道测试时，输入的提示语句`请输入信息# `和服务端回显的语句粘在了一起，虽然从使用上没什么问题。出现这种情况的原因是打印提示语句和打印服务端回显语句分别属于两个线程的操作，而这两个线程的调度是不确定的。正常情况下应该是先打印提示语句，然后再换行打印回显语句，而不是粘在一起。所以需要用互斥锁或条件变量限制它们的行为是同步的（也就是按顺序的），这样就能保证某一个线程一定在其他线程之前。

> 关于互斥锁和条件变量，在上面的《线程池》一文中有作出介绍。

# 群聊版（线程池）
