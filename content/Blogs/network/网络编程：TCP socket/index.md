---
title: 网络编程：TCP socket
weight: 3
open: true
---

## 阅读前导

TCP（Transmission Control Protocol，传输控制协议）提供的是面向连接，可靠的字节流服务。即客户和服务器交换数据前，必须现在双方之间建立一个 TCP 连接，之后才能传输数据。并且提供超时重发，丢弃重复数据，检验数据，流量控制等功能，保证数据能从一端传到另一端。

TCP 不同于 UDP，不仅需要实现 UDP 的步骤，还要以一定的手段保证连接的安全性。

关于 UDP socket 的实践，可以看：[网络编程：UDP socket](https://blog.csdn.net/m0_63312733/article/details/130465194?spm=1001.2014.3001.5501)，本文同样按照这篇文章的结构叙述，许多重复的内容也是类似的，部分前导内容也在其中介绍。

TCP 套接字编程的基本流程是这样的：

- 服务器端：
  - 创建一个监听套接字（socket），指定使用 TCP 协议和监听的端口号
  - 绑定监听套接字到本地的 IP 地址（bind）
  - 开始监听客户端的连接请求（listen）
  - 接受客户端的连接请求，返回一个新的连接套接字（accept）
  - 通过连接套接字与客户端进行数据交互（send/recv 或 read/write）
  - 关闭连接套接字和监听套接字（close）

- 客户端：
  - 创建一个连接套接字（socket），指定使用 TCP 协议
  - 连接到服务器的监听套接字，建立连接（connect）
  - 通过连接套接字与服务器进行数据交互（send/recv）
  - 关闭连接套接字（close）

# 服务端

## 定义

服务端的逻辑将被定义在`TCPServer.cc`中，它包含了头文件`TCPServer.hpp`。

而且服务端使用各种 socket 接口的操作将被封装为一个`TCPServer`类，这个类型的对象就可以被称之为服务端。它将在头文件中被定义，在源文件中被使用。

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

和 UDP 的实现类似，服务器要接收所有可能的 IP 地址发送的数据，因此在大多数情况下不需要限定数据的来源 IP 地址。除此之外，网络中数据的传输本质上是跨网络的进程间通信，通过端口号标定主机中进程的唯一性。

值得注意的是，这里的端口号指的是发送数据的主机（即客户端）的端口号，而不是本机（即服务器）的端口号。服务器可以使用这些信息来确定客户端的身份，并向客户端发送响应。

除了处理 IP 地址和 PORT，还要用一个变量保存打开的文件描述符，以便对客户端传送的数据进行处理。

```cpp
// TcpServer.hpp 
#include <iostream>
#include <string>
#include <cerrno>
#include <cstring>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "Log.hpp"
class TcpServer
{
public:
    TcpServer(uint16_t port, std::string ip = "")
        : _port(port)
        , _ip(ip)
        , _sockfd(-1)
    {}
    ~TcpServer()
    {
        if(_sockfd >= 0) close(_sockfd);
    }
    bool initServer()
    {
        
    }
    void start()
    {
        
    }
private:
    int _sockfd;
    int16_t _port;
    std::string _ip;
};
```

注意：

- 在构造函数中赋予 IP 地址以缺省值`""`，这么做的目的是兼容可能需要限定特定 IP 地址的数据的需求。
- 在析构函数中关闭文件描述符。
- `initServer()`是初始化服务器的逻辑。
- `start()`是服务器对数据处理的逻辑。

### 服务端框架

- 控制命令行参数：在运行程序的同时将 IP 和 PORT 作为参数传递给进程，例如`./[name] [PORT]`这就需要提取出命令行参数和`PORT`。除此之外，通常的做法是通过打印一个语句来显示它的使用方法，一般使用一个函数`usage()`封装。

  > 这样做是合理的，例如在命令行随意输入一个命令的名字，但没有参数，就会有以下提示：
  >
  > <img src="./.网络编程：TCP socket.IMG/image-20230507221335105.png" alt="image-20230507221335105" style="zoom:40%;" />
- 参数类型转换：我们知道，PORT 都是整数，而命令行参数是一个字符串，所以提取出参数以后，要对它们进行类型转换。PORT 使用了`atoi()`函数转换为整数。
- 以防资源泄露，这里使用了`unique_ptr`智能指针管理服务器的资源，不必在此深究，智能指针的使用就像普通指针一样。这里的程序比较简单，用一对`new`和`delete`也能实现资源的申请与回收。注意调用构造函数的时候需要传递参数。智能指针的头文件是`<memory>`。

```cpp
// TcpServer.cc
#include "TcpServer.hpp"
#include <memory>

static void usage(std::string name)
{
    std::cout << "\nUsage: [PORT]" << name << std::endl;
}
// ./TcpServer [PORT]
int main(int argc, char* argv[])
{
    if(argc != 2)
    {
        usage(argv[0]);
        exit(1);
    }
    uint16_t port = atoi(argv[1]);
    std::unique_ptr<TcpServer> server_ptr(new TcpServer(port));
    server_ptr->initServer();

    return 0;
}
```

后续代码中重复的头文件将会被省略，只显示新增的头文件。

## 初始化服务器

### 创建套接字

当服务器对象被创建出来，就要立马初始化它，初始化的第一件事就是创建套接字，这个操作相当于构建了网络通信信道的一端。`socket()`函数用于创建套接字。

```c
int socket(int domain, int type, int protocol);
```

参数：

- domain（域）：指定套接字家族，简单地说就是指定通信的方式是本地还是网络：
  - `AF_INET`：网络通信。
- type：指定套接字的类型，即传输方式：
  - 适用于 UDP：`SOCK_DGRAM`：无连接的套接字/数据报套接字。
  - *适用于 TCP：`SOCK_STREAM`：有序的、可靠的、全双工的、基于连接的流式服务。
- protocol（协议）：指定传输协议，默认设置为`0`，此函数内部会根据前两个参数推导出传输协议。

返回值：

- 成功：返回一个 int 类型的文件描述符。这个 socket 描述符跟文件描述符一样，后续的操作都有用到它，把它作为参数，通过它来进行一些读写操作。
- 失败：返回-1，同时设置错误码。

> 其中，`AF_INET`是一个宏，表示基于网络的套接字。`SOCK_STREAM`也是宏，表示套接字类型是面向连接的。

> 数据报套接字和流套接字有什么区别？

数据报套接字（SOCK_DGRAM）和流套接字（SOCK_STREAM）是两种不同类型的套接字。数据报套接字基于 UDP 协议，提供无连接的不可靠传输服务，而流套接字基于 TCP 协议，提供面向连接的可靠传输服务。

数据报套接字适用于传输数据量小、对实时性要求较高的应用场景，它可以快速地发送和接收数据，但不能保证数据的顺序和完整性。流套接字适用于传输数据量大、对可靠性要求较高的应用场景，它能够保证数据按顺序、完整地传输，但传输速度相对较慢。

下面是创建套接字和差错处理的逻辑：

```cpp
class TcpServer
{
public:
    bool initServer()
    {
        _sockfd = socket(AF_INET, SOCK_STREAM, 0);
        if(_sockfd < 0)
        {
            logMessage(FATAL, "%d:%s", errno, strerror(errno));
            exit(2);
        }
        logMessage(DEBUG, "%s: %d", "create socket success, sockfd", _sockfd);
        return true;
    }
};
```

注意：这里使用了`string.h`中的`strerror()`函数，`strerror()`函数用于将错误码转换为对应的错误信息字符串。它接受一个错误码作为参数，返回一个指向描述该错误的字符串的指针。这个字符串描述了错误码所代表的错误原因。

例如，当一个库函数调用失败时，通常会产生一个错误码，这个错误码会被存储在全局变量`errno`中。可以使用`strerror(errno)`来获取对应的错误信息字符串。

对应地，在析构函数中可以将正常打开的文件描述符关闭。这样做是规范的，实际上一个服务器运行起来以后非特殊情况将会一直运行，调用析构函数的次数寥寥无几。

差错处理和日志：

- 当文件描述符`_sockfd` < 0 时，说明打开文件失败了，它是初始化服务器的第一步，这是致命的错误（FATAL），记录日志并调用`exit()`直接退出进程。
- 日志：当创建文件描述符成功以后，记录刚才的操作。为了验证打开的文件描述符的值，可以将`_sockfd`作为日志信息的一部。

简单测试一下：

<img src="./.网络编程：TCP socket.IMG/image-20230507231023100.png" alt="image-20230507231023100" style="zoom:40%;" />

这一步和实现 UDP socket 编程的唯一区别就是使用`socket()`函数的第二个参数不同。

### 绑定

上面只完成了初始化服务器的第一步，下一步要将用户在命令行传入的 PORT 在内核中与当前进程强关联起来，也就是绑定（bind）。即通过绑定，在后续的执行逻辑中这个端口号就对只对应着被绑定的服务器进程，因为端口号标定着主机中进程的唯一性，服务器运行起来本身就是一个进程。

这个操作和 UDP socket 也是没有区别的。

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

> 值得注意的是，`bzero()`函数已经被弃用（在 POSIX.1-2001 中标记为 LEGACY），并且在 POSIX.1-2008 中被删除了。在新程序中，建议使用`memset()`函数来代替`bzero()`函数。

下面是绑定和差错处理的逻辑：

```cpp
bool initServer()
    {
        // 1. 创建套接字
       	// ...
        // 2. 绑定
        // 2.1 填充属性
        struct sockaddr_in local;
        memset(&local, 0, sizeof(local));
        local.sin_family = AF_INET;    // 网络传输
        local.sin_port = htons(_port); // 本地->网络
        local.sin_addr.s_addr = _ip.empty() ? INADDR_ANY : inet_addr(_ip.c_str());

        // 2.2 绑定
        if (bind(_sockfd, (struct sockaddr *)&local, sizeof(local)) < 0)
        {
            logMessage(FATAL, "bind():errno:%d:%s", errno, strerror(errno));
            exit(3);
        }
        logMessage(NORMAL, "initialize udp server...%s", strerror(errno));

        return true;
    }
```

注意：

- `sin_family`指定的是本地传输数据还是网络传输数据，设置为`AF_INET`。

- `sin_port`指定的是稍后要绑定的 PORT，这个 PORT 是要发送到网络中的，因此要使用`htons()`函数将它的主机字节序转换为网络字节序，保证它是大端序列的。

- IP 地址被封装了好几层，它的结构层次是：`struct sockaddr_in [sin_addr]`->`struct in_addr [s_addr]`->`in_addr_t [s_addr]`->`uint32_t [s_addr]`。

  注意此时构造函数中的`_ip`的缺省值被设置为`""`，表示空串，如果为空则设置为`INADDR_ANY`，表示接收来自任意 IP 地址的数据；否则只能接收特定 IP 地址的发送的数据（缺省值）。

- `inet_addr()`函数用于将 IPv4 点分十进制地址字符串转换为网络字节顺序的二进制数据。它的原型为`unsigned long inet_addr(const char *cp)`，其中`cp`是一个以点分十进制表示法表示的 IPv4 地址字符串。

- 在调用 bind() 函数时，第二个参数注意要类型转换为`struct sockaddr *`类型。

- 在执行 bind() 函数之前，定义的数据包`local`是一个局部对象，因此它是被存储在栈区的。通过 bind() 函数，这个局部对象中的属性就会被内核绑定。

测试一下：

<img src="./.网络编程：TCP socket.IMG/image-20230507230939233.png" alt="image-20230507230939233" style="zoom:40%;" />

UDP 服务器的实现就到此为止了，所以 UDP 通信的效率很高，但通过实现它的步骤可以知道，这是要付出代价的。

### 开启监听

TCP 服务器是面向连接的，客户端在向服务器发送数据之前，首先要建立连接才能进行通信。但是建立连接的前提是服务端能及时对客户端发送的连接请求产生回应，因此在建立连接之前，需要让服务端不断接收客户端发送的连接请求。

主机（服务端）随时处于等待被连接的状态，叫做监听状态。

`listen()` 函数用于将套接字标记为被动套接字，即用于使用 `accept()` 接受传入的连接请求的套接字。

```c
#include <sys/types.h>
#include <sys/socket.h>

int listen(int sockfd, int backlog);
```

参数：

- `sockfd` ：指向类型为 `SOCK_STREAM` 或 `SOCK_SEQPACKET` 的套接字的文件描述符。

- `backlog` ：定义了 `sockfd` 的挂起连接队列的最大长度。如果连接请求到达时队列已满，客户端可能会收到带有 `ECONNREFUSED` 指示的错误，或者如果底层协议支持重传，则请求可能会被忽略，以便稍后重新连接成功。否则如果队列已满，那么客户端的请求就会被拒绝。

  > 即全连接队列的最大长度。如果有多个客户端同时发来连接请求，此时未被服务器处理的连接就会放入连接（等待）队列，该参数代表的就是这个全连接队列的最大长度，一般不要设置太大，设置为 5、10 或 20 即可。
  >
  > 这个参数将会在后续 TCP 协议专题中详细介绍，在这里先试着用它。

返回值：

- 成功：返回 0。
- 失败：返回-1，同时设置错误码。

下面是进入监听状态及差错处理的逻辑：
```cpp
class TcpServer
{
private:
    const static int _backlog;
public:
    bool initServer()
    {
        // 1. 创建套接字
        // 2. 绑定
        
        // 3. 监听
        if (listen(_sockfd, _backlog) < 0)
        {
            logMessage(FATAL, "listen()errno:%d:%s", errno, strerror(errno));
            exit(4);
        }

        logMessage(NORMAL, "initialize udp server...%s", strerror(errno));
        return true;
    }
};
```

测试一下：
<img src="./.网络编程：TCP socket.IMG/image-20230507230930768.png" alt="image-20230507230930768" style="zoom:40%;" />

可以验证，打开的文件描述符是 3 号，说明 0、1 和 2 号文件描述符都是默认被打开的状态。

## 运行服务器

### netstat 工具

端口号只能被一个进程使用，如果再用`8080`（随便设置的）端口号初始化服务器，那么会绑定失败，因为这个端口号已经被其他进程占用了。

通过`netstat`工具查看网络相关的进程信息。

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

测试：

首先让服务器运行起来，这里用一个死循环让服务器先不要退出，方便等下查看状态：
```cpp
// TcpServer.hpp
class TcpServer
{
public:    
	void start()
    {
        while(1)
        {
            sleep(1);
        }
    }
};
// TcpServer.cc
int main()
{
    // ...
    std::unique_ptr<TcpServer> server_ptr(new TcpServer(port));
    server_ptr->initServer();
    server_ptr->start(); // 运行服务器   
}
```

<img src="./.网络编程：TCP socket.IMG/image-20230507232320538.png" alt="image-20230507232320538" style="zoom:40%;" />

### 获取连接和通信准备

和 UDP 服务器不一样，TCP 服务器的实现要手动连接。

`accept()` 函数用于基于连接的套接字类型（`SOCK_STREAM`，`SOCK_SEQPACKET`）。它从监听套接字 `sockfd` 的挂起连接队列中提取第一个连接请求，创建一个新的已连接套接字，并返回指向该套接字的新文件描述符。新创建的套接字不处于监听状态。原始套接字 `sockfd` 不受此调用影响。参数 `sockfd` 是一个已使用 `socket(2)` 创建、使用 `bind(2)` 绑定到本地地址且正在监听的套接字。

```cpp
#include <sys/types.h>
#include <sys/socket.h>

int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
```

参数：

- `sockfd` ：一个已使用 `socket(2)` 创建、使用 `bind(2)` 绑定到本地地址且正在监听的套接字。
- `addr` ：指向 `sockaddr` 结构的指针。该结构被填充为对等套接字的地址，由通信层所知。返回的地址的确切格式由套接字的地址族确定（请参阅 `socket(2)` 和相应的协议手册页）。当 `addr` 为 `NULL` 时，不填充任何内容；在这种情况下，`addrlen` 也不使用，也应为 `NULL`。
- `addrlen` ：是一个值-结果参数（输入输出型参数）：调用者必须将其初始化为包含指向 `addr` 的结构的大小（以字节为单位）；返回时，它将包含对等地址的实际大小。如果提供的缓冲区太小，则返回的地址将被截断；在这种情况下，`addrlen` 将返回一个大于调用时提供的值的值。

>`socket(2)` 和 `bind(2)` 都是 Linux 系统调用。`socket(2)` 用于创建套接字，而 `bind(2)` 用于将套接字绑定到本地地址。

返回值：

- 成功：返回创建的新套接字文件描述符。
- 失败：返回-1，同时设置错误码。

> 在初始化服务器时（initServer() 的第一步）也创建了套接字，为什么这里还要创建一次？有什么区别？

实现服务器和客户端的流程（文章首处介绍了）可以看出，服务器端需要创建两个套接字，一个是监听套接字，一个是连接套接字/服务套接字。监听套接字的作用是等待客户端的连接请求，而连接套接字/服务套接字的作用是与客户端进行数据通信。每当有一个客户端连接到服务器时，服务器就会通过 accept 函数返回一个新的连接套接字/服务套接字，这样就可以区分不同的客户端，并且为每个客户端分配一个独立的通信通道。如果只有一个监听套接字，那么服务器就无法同时处理多个客户端的请求，也无法区分不同的客户端。

因此，在实现 TCP 服务器时，初始化服务器时也创建了套接字，为了监听客户端的连接请求；而在服务器获取连接时还要创建一次，为了与客户端进行数据交互。

所以为了符合套接字的用途，将成员函数`_sockfd`改为`_listen_sockfd`，意为监听套接字；稍后接收`accept()`函数的返回值也命名为`service_sockfd`，意为服务套接字，表示服务端将会通过这个套接字对数据进行处理。实际上，服务端在真正使用的套接字是服务套接字（accept() 返回值）。

> accept() 函数和 listen() 函数的关系？

**listen() 函数让服务器准备好接收连接请求，而 accept() 函数从队列中取出一个请求并建立连接。**

- listen() 函数的作用是让一个套接字进入监听状态，也就是说，它可以接收其他套接字的连接请求。

- accept() 函数的作用是从连接请求队列中取出一个请求，并建立一个新的套接字与客户端进行通信。accept() 函数会阻塞当前进程，直到有一个连接请求到达。当 accept() 函数成功返回时，它会返回一个新的套接字描述符，用于与客户端交换数据。同时，原来的监听套接字仍然保持监听状态，可以继续接受其他连接请求。

下面是获取连接和通信的准备逻辑：
```cpp
class TcpServer
{
public:
    void start()
    {
        while (1)
        {
            // 4. 获取链接
            struct sockaddr_in client;
            socklen_t len = sizeof(client);
            int service_sockfd = accept(_listen_sockfd, (struct sockaddr *)&client, &len);
            // 获取连接失败
            if (service_sockfd < 0)
            {
                logMessage(ERROR, "accept()errno:%d:%s", errno, strerror(errno));
                continue; // 继续
            }
            // 获取连接成功
            // 通信准备 （网络->主机）
            uint16_t client_port = ntohs(client.sin_port);
            std::string client_ip = inet_ntoa(client.sin_addr);
            logMessage(NORMAL, "link success, IP[%s], PORT[%u], server sock: %d\n",
                       client_ip.c_str(), client_port, service_sockfd);

            // 5. 通信逻辑
            service(service_sockfd, client_ip, client_port);

            // 关闭文件描述符
            close(service_sockfd);
        }
    }

private:
    int _listen_sockfd; // 监听套接字
};
```

注意：

- 使用`accept()`函数获取连接可能会失败，但是失败的原因可能不是致命的，所以连接失败以后要继续尝试。
- 在连接成功以后，就要进行通信。在通信之前，需要做一些准备工作，例如将获取到的客户端 IP 地址和 PORT 从网络字节序转为主机字节序，以便后续使用。IP 地址通过`inet_ntoa()`还转换为主机字节序的字符串。
- 为了方便观察测试现象，在日志中打印了 IP 地址、端口号以及`accept()`函数获取到的新文件描述符。
- `service()`函数是通信的具体逻辑，由于通信的逻辑不应该和服务器本身封装在一起，因此简单地将通信逻辑定义在服务器的头文件中（实际上如果通信逻辑比较复杂，可以另外用文件封装）。
- 在函数执行的最后要关闭文件描述符。

### 通信逻辑

通信相关的逻辑应该独立于服务器之外，因此在类外部实现通信逻辑。它将会根据需要有多个版本，在此实现一个简单的单进程版本通信逻辑，这样以后要修改具体的通信方式只要修改这个函数即可，不需要修改服务器的逻辑。

根据不同的需要，本文将会从单进程改进到多线程，进而接入线程池。

## 单进程服务端函数（version1）

用 write() 向套接字写入数据，用 read() 从套接字中读取数据。

```c
#include <unistd.h>

ssize_t read(int fd, void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count);
```

- `read()`函数会从文件描述符`fd`中读取`count`个字节并保存到缓冲区`buf`，成功则返回读取到的字节数（但遇到文件结尾则返回 0），失败则返回-1。

目前的服务端函数的任务是实现一个回声服务器（echo），即将客户端发送的数据打印出来，然后原封不动地回发数据。下面是服务端使用`read()`函数和`write()`函数读取数据和差错处理的逻辑：

```cpp
#define NUM 1024
static void service(int service_sockfd, std::string client_ip, uint16_t client_port)
{
    char buffer[NUM]; // 以字符串作为缓冲区
    while (1)
    {
        // 读取缓冲区内容
        ssize_t s = read(service_sockfd, buffer, sizeof(buffer) - 1);
        if (s > 0) // 读取成功
        {
            buffer[s] = '\0'; // 标记数据的末尾
            std::cout << "IP[" << client_ip << "], PORT[" << client_port << "]: " << buffer;
            // std::cout << std::endl; // 后续会使用换行
        }
        else if (s == 0) // 无数据
        {
            logMessage(NORMAL, "IP[%s], PORT[%u] shut down...me too", client_ip.c_str(), client_port);
            break;
        }
        else // 读取失败
        {
            logMessage(ERROR, "read socket error...%d:%s", errno, strerror(errno));
            break;
        }
        // 写入数据
        write(service_sockfd, buffer, strlen(buffer));
    }
}
```

注意：

- `buffer[s] = '\0'`的操作是将读取到的数据当做字符串，以便稍后能直接打印读取的内容，避免由于平台的差异而出现问题。
- 如果 read() 函数的返回值`s`大于 0，说明读取成功，打印获取到的数据和发送数据的客户端 IP 和 PORT。
- 如果 read() 函数的返回值`s`等于 0，说明读取到了文件末尾，即对端主机关闭了写端的文件描述符（1），这和管道通信是一样的，如果对端关闭了写端，说明客户端没有数据可读，直接退出（一直等也是浪费资源）。这里的退出不是退出服务端进程，而是重新从缓冲区中读取内容。
- 如果 read() 函数的返回值`s`小于 0，说明读取失败，直接退出本次读取。
- 最后的`write()`函数是向客户端原封不动地发送回数据，这是实现回声服务器的步骤。实际上服务端发送数据与否取决于客户端的需求。

> 同时对文件描述符对应的文件（服务套接字）进行写和读操作不会出现问题吗？

TCP 和 UDP 都是全双工通信。这意味着它们都能够在同一时间内在两个方向上发送和接收数据。

TCP 提供全双工服务，这意味着可以在同一时间内在两个实体之间交换数据。

而 UDP，在适当的情况下，可以被认为是全双工的，但本身并不是，而 TCP 则始终是全双工的。UDP 是一个即发即弃的尽力而为协议（fire-and-forget, best-effort protocol），但上层可以以全双工方式使用它。

> 为什么可以使用`read()`和`write()`文件 I/O 函数对网络通信的数据操作？

在 UNIX 和类 UNIX 系统中，套接字被视为一种特殊类型的文件。这就是可以使用像 read() 和 write() 这样的文件 I/O 函数来读写套接字的原因。但是，套接字不是普通文件，它们不能存储在磁盘上，也不能通过文件系统进行访问。它们是一种用于在网络上进行通信的特殊类型的文件。

### telent 工具

虽然现在还未实现客户端的逻辑，但是可以使用 telent 工具充当客户端的角色进行测试。

Linux 中的 telnet 是一种远程登录的协议，它可以让用户通过网络连接到另一台计算机，并在那台计算机上执行命令。telnet 的优点是简单易用，但缺点是不安全，因为它传输的数据都是明文，容易被窃听或篡改。

> 在 centos 中使用 telnet，首先需要在远程计算机上安装并启动 telnet 服务。这可以通过以下命令实现：
>
> ```shell
> sudo yum install telnet
> sudo yum install telnet-server
> sudo systemctl enable telnet.socket
> sudo systemctl start telnet.socket
> ```

使用方法：输入`telnet`命令，后面跟上远程计算机的 IP 地址或主机名，以及要连接的端口号（如果不指定端口号，则默认为 23）。例如，要连接到 IP 地址为`192.168.1.1`的远程计算机，可以使用以下命令：`telnet 192.168.1.1`。在成功连接到远程计算机后，输入用户名和密码进行登录。

当不需要远程登录时，首先键入转义字符`Ctrl - ]`，然后输入 exit 或 logout 命令退出 telnet 会话。

### 测试

<img src="./.网络编程：TCP socket.IMG/telnet1.gif" alt="telnet1" style="zoom:40%;" />

也可以用本地环回地址进行测试。

细节：
当`telnet`连接到服务器时，打印的日志信息说明文件描述符是 4 号。

下面再增加一个客户端测试：

<img src="./.网络编程：TCP socket.IMG/telnet2.gif" alt="telnet2" style="zoom:40%;" />

这里的现象不是我们预想的那样，中间的客户端 1 连接成功以后，服务端打印了对应的日志信息，客户端 1 发送信息服务端也能正常回显。但是上面的客户端 2 执行`telnet`命令以后，服务端既没有打印日志信息也没有进行正常的回显操作，但是一旦客户端 1 退出，服务端就会一次性将刚刚没有输出的信息打印出来。

原因是这个服务端中的`start()`处理数据的函数中的逻辑是在`while(1)`死循环中进行的，而且是单进程执行这个操作。如果某次死循环中的任务没有执行完毕，那么整个服务端进程将会陷入死循环中，一直等待任务被执行完。这个单进程服务端一次只能处理一个客户端的任务，处理完了才能处理下一个。虽然单进程版本没什么用，但是它作为学习还是很有价值的，是一切改进的基础。

## 多进程服务端（version2）

### 创建子进程

在学习完进程相关知识后，我们知道子进程创建后会继承父进程的文件描述符表。因此子进程能够直接使用父进程曾经打开的文件描述符。

如果每次获取到连接以后都创建一个子进程，那么直接调用`exit()`函数退出以后会出现僵尸问题，为了避免这个问题，考虑在父进程中使用`wait()`函数或`waitpid()`回收子进程的资源。但是前者是阻塞式等待，会出现效率上的问题；后者需要不断轮询子进程是否退出，这需要父进程（服务端）保存子进程所有 PID，然后不断查询它们是否退出，同样有效率上的问题。

为了避免父进程回收子进程出现的效率问题，可以采用以下方法：
1. 使用信号机制。对于`SIGCHLD`信号，只要子进程的状态发生改变，它就会发送此信号给父进程。我们可以通过注册函数来捕捉这个信号，处理函数调用`waitpid`以非阻塞方式来处理该信号。
1. 还可以使用孙子进程来回收子进程。父进程一次 fork() 后产生一个子进程随后立即执行`waitpid（子进程 pid, NULL, 0)`来等待子进程结束，然后子进程 fork() 后产生孙子进程随后立即`exit(0)`。这样，父进程就可以回收子进程，而不会阻塞。

> 孙子进程的原理是：父进程创建一个子进程，然后立即使用 waitpid() 来等待子进程结束。子进程创建一个孙子进程，然后立即退出。这样，父进程就可以回收子进程，而不会阻塞。孙子进程成为孤儿进程，由 init 进程（1 号进程）领养。当孙子进程退出时，init 进程会回收它的资源。
>

### 关于文件描述符

子进程继承父进程打开的文件描述符，而子进程的存在是解决单进程版本的服务器函数一次只能处理一个客户端的问题，因此服务端的“服务”逻辑应该由子进程执行，它不需要`listen_sockfd`（监听套接字）只需要`service_sockfd`（服务套接字）来处理数据，也就是`accept()`函数的返回值。

对于父进程，也就是`main()`进程，它的作用只是利用监听套接字作为参数传入`accept()`函数获取服务套接字（返回值），所以父进程在把服务套接字传递给子进程后，就要关闭服务套接字，子进程只关心服务套接字。

原先的单进程作为父进程创建子进程，让子进程做自己原本的工作，这也是一种解耦的方式。值得注意的是，父子进程不需要的文件描述符的种类是不一样的。

>父进程在把服务套接字传递给子进程后，就要关闭服务套接字，这样不会造成读写问题吗？

父进程在把服务套接字传递给子进程后，关闭服务套接字不会造成读写问题。这是因为在 UNIX 系统中，当一个进程关闭一个套接字时，它只是减少了该套接字的**引用计数**（写时拷贝）。只有当引用计数为 0 时，才会真正关闭套接字。因此，如果子进程仍然拥有该套接字的副本，则该套接字仍然是打开的，并且子进程可以继续使用它进行读写操作。

> 为什么要关闭文件描述符？

关闭文件描述符是很重要的，因为每个进程都有一个文件描述符的限制。如果进程打开了太多的文件描述符而没有关闭它们，那么它将无法再打开新的文件描述符。此外，关闭文件描述符还可以释放系统资源，例如内存和文件锁。

在某些情况下，如果不关闭文件描述符，可能会导致数据丢失或损坏。例如，如果进程使用 write() 函数将数据写入文件，但在退出之前没有关闭文件描述符，则可能会丢失未写入磁盘的数据。

文件描述符是表征资源空间的一个下标，它被一个表储存着，它是有限的。如果子进程继承了父进程创建的服务套接字被使用完了，父进程也不关闭它，那么这个文件描述符对应的文件描述符就被浪费了，所以父子进程都要关闭自己不需要的文件描述符。这是文件描述符泄漏，类似内存泄漏。在云服务器中，单进程打开的文件描述符上限是 50000~100000 个。

<img src="./.网络编程：TCP socket.IMG/image-20230509231635852.png" alt="image-20230509231635852" style="zoom:40%;" />

> 如果没有及时关闭文件描述符，那么在测试时会发现文件描述符的编号一直在增加，并且重启机器就会回复原样。

下面是使用子进程进行通信的逻辑（不包含解决僵尸进程的逻辑）：

```cpp
class TcpServer
{
    void start()
    {
        while (1)
        {
            // 4. 获取链接
            
            // 通信逻辑 -- 多进程
            // 创建子进程
            pid_t id = fork();
            assert(id != -1);
            if (id == 0) // 子进程 
            {
                close(_listen_sockfd); // 关闭监听套接字
                service(service_sockfd, client_ip, client_port);
                exit(0);
            }
            // 父进程关闭服务套接字
            close(service_sockfd);
        }
    }
};
```

### 测试

使用脚本每隔 1 秒查看进程的所有信息：

```shell
while :; do ps axj | grep TcpServer; sleep 1; echo "#"; done
```

依然使用两个`telnet`模拟客户端：
<img src="./.网络编程：TCP socket.IMG/telnet_fork.gif" style="zoom:50%;" />

两个客户端连接成功以后，可以看到服务端中依次多了两个子进程，它们是被父进程创建用来执行线程函数的，所以可以同时响应多个客户端发送的信息，图中也不会出现单进程服务端一次只能处理一个客户端的情况了。

值得注意的是，当两个子进程都调用`exit(0)`退出以后，它们会变成僵尸进程，这在打印的信息中是可以观察到的：

<img src="./.网络编程：TCP socket.IMG/image-20230509235421602.png" alt="image-20230509235421602" style="zoom:40%;" />

> 在进程列表中，`<defunct>`表示僵尸进程。

#### 捕捉信号

为了更明显地显示进程的信息，在进程退出时的日志打印信息增加了线程的 PID 打印，脚本也增加了头目的显示：

```cpp
static void service(int service_sockfd, std::string client_ip, uint16_t client_port)
{
    while (1)
    {
        // 读取缓冲区内容
        else if (s == 0) // 无数据
        {
            logMessage(NORMAL, "Process:[%d]: IP[%s], PORT[%u] shut down...me too", getpid(), client_ip.c_str(), client_port);
        }
}
```

```shell
while :; do ps axj | head -1 && ps axj | grep TcpServer; sleep 1; echo "#"; done
```

可以在`start()`成员函数中增加以下逻辑：

```cpp
void start()
{
    // 4.0 注册信号
    signal(SIGCHLD, SIG_IGN);
    while (1)
    {
        // ...
        // 创建子进程
        pid_t id = fork();

        if (id == 0) // 子进程 
        {
            exit(0); // 子进程退出
        }
    }
}
```

> 上面的代码只呈现了必要的部分，不需要的部分会说明。

用同样的方式测试一下：

<img src="./.网络编程：TCP socket.IMG/telnet_fork_signal.gif" alt="telnet_fork_signal" style="zoom:40%;" />

可以看到，由于父进程忽略了子进程退出的信号，所以两个客户端进程退出以后不会变成僵尸进程：

<img src="./.网络编程：TCP socket.IMG/image-20230510225741376.png" alt="image-20230510225741376" style="zoom:40%;" />

<img src="./.网络编程：TCP socket.IMG/image-20230510225849302.png" alt="image-20230510225849302" style="zoom:40%;" />

#### 孙子进程

让子进程再次创建子进程，就是孙子进程。那么原本子进程要执行的逻辑将会被孙子进程执行，子进程创建孙子进程后立即调用`exit(0)`退出，原本的父进程调用`wait()`或`waitpid()`函数等待子进程能立刻成功地回收子进程的资源，而不需要等待回收孙子进程的资源，这样原本的父进程就能避免因等待回收子进程资源而占用时间，降低效率了。

> 父进程通常创建子进程来执行任务，但是父进程需要回收子进程的资源，这个操作不论是 wait 函数还是 waitpid 函数，都会占用父进程一定的资源，降低了效率。因此让子进程 fork 创建孙子进程，让孙子进程执行原本子进程要执行的任务。原本的子进程直接 exit(0) 退出，原本的父进程使用 wait 或 waitpid 函数就能直接成功地（耗费的时间可以忽略不计）回收子进程的资源，为什么父进程不需要花费时间呢？另外，在父进程等待子进程的过程中，父进程并未关心孙子进程，为什么孙子进程不需要被等待？

（需要进程相关的前导知识）这种方法被称为“孤儿进程”。

为什么父进程不需要花费时间呢？这是因为孙子进程在退出时会被 init 进程（PID=1）接管，init 进程会负责回收孙子进程的资源。所以父进程只需要等待子进程退出即可，不用关心孙子进程的状态。这样，父进程就能够更快地回收子进程的资源，而不需要花费时间等待孙子进程。

另外，在父进程等待子进程的过程中，父进程并未关心孙子进程，为什么孙子进程不需要被等待？这是因为孙子进程在退出时会向 init 进程发送 SIGCHLD 信号，init 进程会捕捉这个信号并回收孙子进程的 PCB 信息。所以孙子进程不会变成僵尸进程，也不需要被父进程等待。

这是操作系统决定的。当一个进程退出时，它的子进程会被操作系统重新分配给 init 进程。init 进程负责管理这些孤儿进程，并在它们退出时回收它们的资源。

使用孙子进程来执行任务，需要明确 3 个进程的任务：

- 父进程（爷爷）：通过监听套接字获取连接，也就是获取服务套接字，最后关闭服务套接字。
- 子进程（爸爸）：创建孙子进程，关闭监听套接字，然后直接退出。
- 孙子进程（孙子）：执行服务端的任务（即例子中的`service()`函数），执行完毕后`exit(0)`退出。

关于文件描述符：
在 TCP 服务器的实现逻辑中，当父进程创建子进程时，子进程会继承父进程的文件描述符表。当子进程创建孙子进程时，孙子进程也会继承子进程的文件描述符表。因此，孙子进程继承的是子进程的文件描述符表。

在这种情况下，如果子进程关闭了监听套接字，那么孙子进程也不需要再次关闭监听套接字。但是，如果子进程没有关闭监听套接字，那么孙子进程也应该关闭监听套接字。

下面是使用孙子进程执行服务端任务的逻辑：
```cpp
#include <sys/wait.h>
void start()
{
    while (1)
    {
        pid_t id = fork();
        assert(id != -1);
        if (id == 0) // 子进程
        {
            close(_listen_sockfd); // 关闭监听套接字

            if (fork() > 0) // 创建孙子进程
                exit(0);    // 子进程直接退出
            // 下面由孙子进程执行
            service(service_sockfd, client_ip, client_port);
            exit(0);
        }
        // 父进程关闭服务套接字
        close(service_sockfd);
        waitpid(id, nullptr, 0); // 父进程直接等待子进程退出
    }
}
```

用同样的方式和脚本测试一下：

<img src="./.网络编程：TCP socket.IMG/telnet_fork_son.gif" style="zoom:50%;" />

由于子进程创建孙子进程以后就立即退出了，那么孙子进程就是孤儿进程，它将被 1 号进程领养，不会出现僵尸进程的问题：

<img src="./.网络编程：TCP socket.IMG/image-20230510235305723.png" alt="image-20230510235305723" style="zoom:40%;" />

# 客户端

## 框架

### 成员属性

TCP 是面向连接的，客户端不同于服务端，它需要明确数据接收者的 IP 地址和 PORT。除此之外，还要有网络数据的载体--套接字，因此还要保存文件描述符。

```cpp
// TcpClient.hpp
class TcpClient
{
public:
    TcpClient(uint16_t port, std::string ip = "")
        : _port(port)
        , _ip(ip)
        , _sockfd(-1)
    {}
    ~TcpClient()
    {
    }
    bool initClient()
    {
    }
    void start()
    {    
    }
private:
    int _sockfd;
    uint16_t _port;
    std::string _ip;
};
```

注意点同服务端。

### 客户端框架

和服务端类似，要提取命令行参数中的 IP 地址和 PORT，需要注意函数的使用，以及使用`usage()`函数提示使用方法，和使用智能指针接管客户端对象的资源管理（实际上简单情况下使用普通的指针也没有问题）。

```cpp
// TcpClient.cc
static void usage(std::string name)
{
    std::cout << "\nUsage: " << name << "[IP] [PORT]" << std::endl;
}
// ./TcpClient [IP] [PORT]
int main(int argc, char* argv[])
{
    if(argc != 3)
    {
        usage(argv[0]);
        exit(1);
    }

    std::string ip = argv[1];
    uint16_t port = atoi(argv[2]);
    std::unique_ptr<TcpClient> client_ptr(new TcpClient(port, ip));
    
    client_ptr->initClient();
    client_ptr->start();
    return 0;
}
```

头文件都是和服务端类似的。

## 初始化客户端

### 创建套接字

使用`socket()`函数创建一个连接套接字，`SOCK_STREAM`指定使用 TCP 协议。

下面是创建连接套接字和差错处理的逻辑：

```cpp
// TcpClient.hpp
class TcpClient
{
public:
    bool initClient()
    {
        _sockfd = socket(AF_INET, SOCK_STREAM, 0);
        if(_sockfd < 0)
        {
            logMessage(FATAL, "%d:%s", errno, strerror(errno));
            exit(2);
        }
        logMessage(DEBUG, "%s: %d", "create socket success, sockfd", _sockfd);
        return true;
    }
};
```

### 绑定

服务端必须明确端口号，是因为服务端面向的是众多客户端，如果不确定端口号，那么客户端主机和服务端主机就不能进行跨网络的进程间通信。因此服务端的端口号一旦被设置，就不应该再被改变。

相应地，客户端也必须要端口号，不过这个操作和实现 UDP 客户端一样，让操作系统帮忙绑定。端口号存在的意义就是标定进程的唯一性，而不需要关心端口号的值具体是多少。

既然不需要程序员手动调用`bind()`函数绑定，那么也就不需要在客户端中设置监听套接字了，监听操作应该是服务端要做的事情；也不需要使用`accept()`函数获取连接，因为没有主机会主动连接客户端，获取连接的操作也应该是服务端要做的事情。客户端主要需要做的事情是连接别的主机（服务端），这个能力就叫做`connect`。

## 运行服务器

### 连接

connect 函数的功能是客户端主动连接服务器，建立连接是通过三次握手，而这个连接的过程是由内核完成，不是这个函数完成的，这个函数的作用仅仅是通知 Linux 内核，让 Linux 内核自动完成 TCP 三次握手连接。（具体细节将在 TCP 协议专题介绍）

```c
#include <sys/types.h>
#include <sys/socket.h>

int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
```

参数：

- `sockfd`：创建的套接字描述符，指定通信协议为 TCP（SOCK_STREAM）。
- `addr`：服务器地址结构体的指针，指向的是一个`sockaddr_in`类型的结构体，设置服务器的 IP 地址和端口号。
- `addrlen`：addr 参数指向的结构体的大小。

返回值：

- 成功：返回 0。
- 失败：返回-1，并设置错误码 errno。

TCP 协议基于流式套接字，后面两个参数和`sendto()`（UDP socket 编程中发送数据的函数）是一样的。connect 函数的第二个参数是一个输出型参数，用于传递服务器的地址信息给内核。connect 函数的第三个参数是一个输入输出型参数，用于传递套接字地址结构的大小给内核，也用于接收内核返回的实际大小（即使它是一个值类型参数而不是一个指针类型参数）。

下面是连接和差错处理的逻辑：

```cpp
// TcpClient.hpp
void start()
{
    // 3. 连接
    // 3.1 填充服务端信息 本地->网络
    struct sockaddr_in server;
    memset(&server, 0, sizeof(server));
    server.sin_family = AF_INET;
    server.sin_addr.s_addr = inet_addr(_ip.c_str());
    server.sin_port = htons(_port);
    // 3.2 连接
    if (connect(_sockfd, (sockaddr *)&server, sizeof(server)) < 0) // 连接失败
    {
        logMessage(FATAL, "connect()errno:%d:%s", errno, strerror(errno));
        exit(3);
    }
    logMessage(DEBUG, "start tdp client...%s", strerror(errno));   // 连接成功 
}
```

值得注意的是，这里填入结构体的 IP 地址和 PORT 都是客户端在命令行输入的 IP 和 PORT，是服务端的信息，这很好理解，客户端要发送信息，必须要填写“收件人”的信息。

需要注意的是，一个已经连接的套接字是不能再次被连接到另一个地址的。所以目前连接的逻辑不能在死循环中。

> `errno:106:Transport endpoint is already connected`表示连接套接字被重复连接。

### 读取用户数据

例子中是一个很简单的客户端，它从标准输入获取用户输入的数据，对此我们可以用一个字符串保存用户要发送的数据，然后使用`send()`函数将字符串中的数据转移到套接字描述符对应的文件中，以此向已经连接的套接字中发送数据；使用`recv()`函数将服务端返回的数据从套接字中提取出来。

```c
ssize_t send(int socket, const void *buf, size_t len, int flags);
ssize_t recv(int socket, void *buf, size_t len, int flags);                
```

- send 和 recv 的第一个参数都是指定发送或接收端的 socket 描述符，第二个参数都是指定一个缓冲区，用于存放要发送或接收的数据，第三个参数都是指定缓冲区的长度，第四个参数都是指定一些标志位，一般置为 0。
- send 和 recv 的返回值都是表示实际发送或接收的字节数，如果出错则返回-1，并设置 errno。
- send 和 recv 都会涉及到 socket 的内核缓冲区，即发送缓冲区和接收缓冲区，这两个缓冲区用于存放网络上发送或接收到的数据，直到应用层读取或写入为止。
- send 和 recv 都可能会阻塞或非阻塞，取决于 socket 的模式和缓冲区的状态。如果缓冲区满了或空了，send 或 recv 就会等待，直到有足够的空间或数据可用。这和管道通信是一样的。

读取用户要发送数据的逻辑将与下一小节一起给出。

### 发送用户数据

由于实现的是一个回声服务器，就像`echo`指令一样，所以服务端在接收到数据以后直接原封不动地将数据返回给客户端。

```cpp
#define SIZE 1024
void start()
{
    // 4.0 发送并接收数据
    while (1)
    {
        // 4.1 从标准输入流获取数据
        std::string message;
        std::cout << "请输入>>> ";
        std::getline(std::cin, message);
        if (message == "quit")
            break;
        else if(message.empty()) // 只按下回车不输入数据
            continue;
        // 4.2 发送数据
        ssize_t s = send(_sockfd, message.c_str(), message.size(), 0);
        if (s > 0) // 发送成功
        {
            char buffer[SIZE];
            // 4.3 接收服务器返回的数据
            ssize_t s = recv(_sockfd, buffer, sizeof(buffer), 0);
            if (s > 0) // 接收成功
            {
                buffer[s] = '\0'; // 标记数据的末尾
                std::cout << "TcpServer 回显# " << buffer << std::endl;
            }
            else if (s == 0) // 读取到 0 个字节的数据
            {
                logMessage(NORMAL, "TcpServer: IP[%s], PORT[%u] shut down...me too", _ip.c_str(), _port);
                close(_sockfd);
                break;
            }
            else // 读取失败
            {
                logMessage(ERROR, "recv()errno:%d:%s", errno, strerror(errno));
                close(_sockfd);
                break;
            }
        }
        else // 发送 0 个字节的数据或失败
        {
            logMessage(ERROR, "send()errno:%d:%s", errno, strerror(errno));
            close(_sockfd);
            break;
        }
    }
}
```

注意：

- 连接和发送与接收数据的逻辑需要在一个死循环中进行，以不断地接收和发送数据。连接失败会直接退出。
- 只有调用`send()`函数成功发送数据，并且服务端成功接收并处理数据（在本例是回显）以后，客户端才有可能接收到服务端返回的数据，因此客户端接收服务端返回数据的前提是客户端成功发送了数据。
- 因此调用`recv()`函数接收服务端返回的数据的逻辑应该在`send()`函数返回值`s > 0`的分支上。在接收到服务端返回的数据以后，打印返回的数据，这是以回显的方式验证是否实现了 echo 服务端的办法。
- 它们的返回值都是实际读取或发送的字节数，如果发送或接收 0 个字节的数据或发送失败，直接退出并关闭连接套接字。对于`send()`函数，发送 0 个字节的数据和失败，对于服务端并没有什么区别，因为都收不到数据；对于`recv()`函数，它是在接收服务端返回的数据，因此接收到 0 个数据就表明服务端已经没有什么要发送了，即所有数据都已经被返回了。

值得注意的是，`recv()`函数的返回值并不包括`\n`，因此如果出现只按下回车而不输入数据的情况，应该重新输入，否则发送的就是一个空字符串，服务端读取时就会认为客户端没有发送数据，直接关闭。

> 这和管道是一样的。

### 测试

用两个实现的客户端替代之前的`telnet`，进行同样的测试：
<img src="./.网络编程：TCP socket.IMG/tcp_client_1.gif" style="zoom:50%;" />

<img src="./.网络编程：TCP socket.IMG/image-20230513151907837.png" alt="image-20230513151907837" style="zoom:40%;" />

通过多次发送信息的测试，效果还是符合预想的。

可能遇到的问题：

1. 客户端输入数据时只按下了回车而不是输入数据，因此用于从标准输入获取数据的字符串就是空串，这是因为`getline()`只会读取`\n`之前的字符，那么它被套接字传输到服务端时，被`read()`函数读取到的字节数就是`0`，这样就会进入返回值为 0 的分支，直接退出。因此要增加判断字符串为空的分支，如果为空则跳到下一次循环，否则会陷入死循环中。
2. 在之前的服务端实现 echo 功能时，也就是打印并没有换行（`std::cout << std::endl`），这是因为 telnet 命令行工具会自动在字符串末尾添加一个换行符`\n`作为命令的结束符。这是因为在 telnet 协议中，命令和响应之间需要通过换行符来区分，以便远程服务器可以正确解析的命令。（telnet 函数不会在字符串末尾添加换行符）

这样就实现了一个简单的 TCP 客户端，由于封装了各个模块，因此可以较方便地增加新功能。

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/TcpSocket/Processes)

# 多线程版服务端（version3）

## 引入

在实现客户端的框架时，使用了多个进程处理多个客户端的任务，但是多进程执行任务的成本通常比单进程要高，原因如下：

1. 上下文切换开销：在多进程执行任务时，操作系统需要花费一定的时间和资源来进行进程切换，以保证各个进程能够公平地使用 CPU 时间。这个过程涉及到保存和恢复多个进程的上下文信息，因此，上下文切换的开销对于多进程执行任务来说是一个不可忽略的成本。
2. 内存开销：每个进程都需要独立的地址空间和系统资源，这意味着在多进程执行任务时，需要为每个进程分配一定的内存空间和系统资源。如果需要同时运行大量进程，那么这些额外的内存开销将会非常大。
3. 进程间通信开销：在多进程执行任务时，进程之间需要进行通信和同步，以便协调各自的工作。这个过程涉及到进程间通信机制的开销，例如共享内存、管道、消息队列等，这些机制的开销也会增加多进程执行任务的成本。

虽然多进程执行任务的成本比单进程要高，但是多进程也有其优点，例如可以充分利用多核 CPU 的计算能力，提高任务处理的效率。多线程和多进程执行任务的选择通常取决于具体的应用场景和需求，以下是几种常见场景：

1. CPU 密集型任务：如果任务需要大量的 CPU 资源，例如图像处理、视频编码等，那么多进程通常比多线程更适合，因为多进程可以充分利用多核 CPU 的计算能力，提高任务处理的效率。

2. I/O 密集型任务：如果任务需要大量的 I/O 操作，例如网络通信、磁盘读写等，那么多线程通常比多进程更适合，因为多线程可以避免进程切换的开销，提高任务处理的效率。

3. 系统资源限制：如果系统资源（例如内存、文件句柄等）受到限制，那么多进程通常比多线程更适合，因为多进程可以通过操作系统的机制来隔离各个进程的资源使用，避免资源竞争和冲突。

4. 数据共享和同步：如果任务需要共享数据和同步操作，例如多个线程或进程需要访问同一个数据结构，那么多线程通常比多进程更适合，因为多线程可以通过共享内存等机制来方便地共享数据，避免数据拷贝和传输的开销。

5. 稳定性和可靠性：如果任务需要保证稳定性和可靠性，例如需要避免线程死锁、进程僵死等问题，那么多进程通常比多线程更可靠，因为多进程可以通过操作系统的机制来避免进程之间的干扰和冲突。

因此，可以使用多线程实现网络通信。关于线程的概念和实践，可以参看：

- [线程概念与控制](https://blog.csdn.net/m0_63312733/article/details/130001145?spm=1001.2014.3001.5502)
- [线程池](https://blog.csdn.net/m0_63312733/article/details/130396163?spm=1001.2014.3001.5502)（本小节只需了解`ThreadData`类的封装）

## 前导知识

### 资源管理

线程的创建和销毁被封装在一个类中，逻辑比较简单：在执行任务之前创建线程，线程执行完毕任务以后就销毁线程。

当服务进程调用`accept()`函数成功获取到新连接后就能创建线程，让线程执行之前进程要执行的任务。

资源回收问题：主线程（服务进程）创建出新线程后，也需要等待回收线程资源（只是线程要回收的资源规模比进程小），否则也会造成类似于僵尸进程这样的问题。但对于线程来说，如果不想让主线程等待新线程退出，可以让线程自己调用`pthread_detach()`函数进行线程分离，当线程退出时系统会自动回收该线程的资源。此时主线程就可以继续调用`accept`函数获取新连接，创建线程执行任务，如此往复。如果不回收资源的话，服务端线程就没有足够的资源重复地为不同客户端服务了。

### 文件描述符

主线程就是`main()`函数对应的进程，在这个例子中就是服务端进程，服务端进程创建的线程是依赖于进程自己的，因而（主）线程创建的所有线程能共享进程大部分资源，包括进程的文件描述符表。文件描述符表维护的是进程与文件之间的对应关系，当线程被进程创建时，操作系统并不会单独为线程们创建新的文件描述符表，而是让所有归属于同一个进程的线程共享进程的文件描述符表。

> 这是“线程是轻量级进程”的体现。

因此，当主线程（服务端进程）调用`accept()`函数成功获取到文件描述符后，后续它创建的所有线程都能够直接使用主线程的文件描述符。

值得注意的是，即使线程们能直接访问服务端进程通过`accept()`函数获取的文件描述符，但是线程们作为“工具人”只是主线程在执行任务过程中凭空创建出来的，因此它们并不知道它们要服务的客户端对应的文件描述符是哪一个。因此主线程在创建线程时，应该将客户端的信息作为参数传给线程函数中。

## 实现

操作系统已经为我们完成了线程操作的各种逻辑，我们只需要调用简单的接口进行创建线程或销毁线程等操作。线程是被用来执行任务的，因此线程函数才是我们自己要动手写的，也是多线程编程的主要内容。

### 线程信息

对于`pthread`库中的线程函数，线程函数的第三个参数类型是`void*`类型，这就能让任何类型的参数先被强转为`void*`类型，然后在线程函数内部再强转回去，这样就能获取到外部传给线程的信息。

在这里的线程信息用一个类`ThreadData`封装（也可以用结构体），它包含了客户端套接字的文件描述符、IP 地址和 PORT 端口号。

```cpp
// 线程信息 Thread.hpp
class ThreadData
{
public:
	int _sockfd;
	std::string _ip;
	uint16_t _port;
};
```

### 创建多线程

下面是填充线程信息和创建 5 个线程执行任务的逻辑：

```cpp
void start()
{
    while (1)
    {
        // 多线程版本
        // 填充客户端信息打包给线程
        ThreadData *_tdata = new ThreadData();
        _tdata->_sockfd = service_sockfd;
        _tdata->_ip = client_ip;
        _tdata->_port = client_port;
        pthread_t tid;
        pthread_create(&tid, nullptr, routine, _tdata);
        close(service_sockfd); // 关闭服务套接字
    }
}
```

值得注意的是，线程信息`ThreadData`应该存储在堆区，因此使用`new`操作符创建。原因是上面的逻辑是在一趟循环中进行的，循环中的局部变量存储在栈区，这样会造成线程安全问题，因为每一趟循环创建的对象的值很可能是不一样的。

使用了`new`操作符，也要成对地使用`delete`操作符进行资源释放。

最后线程退出以后要关闭服务套接字对应的文件描述符。

### 线程函数

线程函数要做的事情就是执行之前主线程要调用的服务函数`service()`，而线程函数要做的就是提取参数：
```cpp
// 线程函数
static void *routine(void *args)
{
    ThreadData *tdata = static_cast<ThreadData *>(args);
    // ThreadData* tdata = (ThreadData *)args; // 直接强转也可以
    service(tdata->_sockfd, tdata->_ip, tdata->_port);

    pthread_detach(pthread_self()); // 线程分离
    delete tdata;
    return nullptr;
}
```

值得注意的是（在本小节的“前导知识--资源管理”部分介绍），主线程创建了线程以后还要负责线程的资源回收任务，但是这个操作可以让线程自己执行，也就是调用`pthread_detach()`函数。这个函数比较特别，它只有当被调用的函数被执行成功（也就是执行到最后的语句或返回语句之后），然后才会释放线程的所有资源。

> `pthread_cancel` 则用于终止一个正在运行的线程。
>
> ```c
> int pthread_cancel(pthread_t thread);
> ```
>
> `thread` 参数是待终止的线程的标识符。如果该函数调用成功，被终止的线程将立即停止运行，并释放所有占用的资源。需要注意的是，该函数并不保证能够成功终止线程，因为被终止的线程有可能阻塞在某个系统调用中，无法被立即终止。此外，被终止的线程也不能够自动释放资源，因此需要其他线程来调用 `pthread_join` 函数来等待该线程的结束，并释放资源。

### 关于文件描述符

线程共享了主线程的文件描述符表，因此某个线程不应该对文件描述符表作修改，否则会影响其他线程。

因此主线程不能关闭通过`accept()`函数成功获取的文件描述符，只能由服务客户端的线程来关闭，因此只有当线程执行完毕任务以后才关闭服务套接字文件描述符。

线程的作用是为客户端服务，因此它不关心监听套接字，所以执行任务的线程不能关闭监听套接字，因为客户端进程（主线程）是需要不断（死循环中）地监听连接任务的。

## 测试

由于使用了多线程，所以打印的脚本应该改为查看线程的信息而不是进程：
```shell
while :; do ps -aL | head -1 && ps -aL | grep TcpServer; sleep 1; echo "#"; done
```

同样地，用两个客户端测试：

<img src="./.网络编程：TCP socket.IMG/tcp_server_threads1.gif" alt="tcp_server_threads1" style="zoom:40%;" />

可以看到，当客户端输入“quit”以后，服务端对应的线程也会退出：
<img src="./.网络编程：TCP socket.IMG/image-20230514191019974.png" alt="image-20230514191019974" style="zoom:40%;" />

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/TcpSocket/Threads)

# 线程池版服务端

- [线程池](https://blog.csdn.net/m0_63312733/article/details/130396163?spm=1001.2014.3001.5502)（本小节还需了解`Thread`类和`ThreadPool`类的封装）

## 引入

在上面的例子中，只是很简单地通过`pthread_create()`和资源回收等底层提供的系统调用创建线程，实现起来并没有什么难度，唯一需要注意的也就是给线程传递参数的类型转换的过程，多用几次也不难。上面这个例子只是一个热身，相当于熟悉接口的使用，实际上服务端不应该只有当客户端连接时才创建线程执行任务，不断创建和销毁线程也会带来开销，因此服务端应该实现创建一定数量的线程，然后将不同客户端的任务分派给线程执行任务，线程执行任务完毕以后也不退出，接着等待下次任务指派。

现在的问题就是创建多个线程后，如何对这些线程进行管理，和如何将任务合理地派发给线程执行。

在多线程执行任务时，没有使用互斥锁和条件变量可能会导致以下问题：

1. 竞态条件：多个线程同时访问共享数据时，可能会出现竞态条件，即多个线程同时修改同一数据，导致数据不一致或意外行为。例如，多个线程同时处理客户端请求时，可能会出现多个线程同时向同一个客户端发送数据的情况，从而导致数据的混乱。
2. 死锁：如果多个线程之间没有互斥锁和条件变量等同步机制，就可能会出现死锁。例如，当一个线程在等待另一个线程释放某个资源时，而另一个线程又在等待该线程释放另一个资源时，就会形成死锁，导致程序无法继续执行。
3. 内存泄漏：在多线程程序中，如果没有正确地管理内存，就可能会导致内存泄漏。例如，如果一个线程分配了一块内存，在处理完数据后没有释放，而另一个线程又分配了相同大小的内存，就会导致内存泄漏。
4. 性能问题：多线程程序的性能通常取决于线程的数量和调度算法。如果没有正确地管理线程，就可能会导致线程数量过多，从而降低程序的性能。

为了避免这些问题，可以使用互斥锁和条件变量等同步机制来保证多个线程之间的数据同步和互斥访问。此外，还应该注意正确地管理内存和线程，避免过多的线程和内存泄漏等问题。

> 这些问题在 [线程同步与互斥](https://blog.csdn.net/m0_63312733/article/details/130164414?spm=1001.2014.3001.5502) 一文中作出了解答并给出了解决方案。

## 线程池成员

在`TcpServer`类中，新增线程池成员，由于线程池是一个模板类，而且是单例模式的类，所以在定义它时要指定模板参数为`Task`类（这在“线程池”一文中介绍，简单地说它就是一个仿函数）；使用一个智能指针管理线程池，使用起来就像普通指针一样（在这个简单的例子中使用简单指针也可以）。由于是单例模式的类，所以这个类中没有对编译器开放构造函数，因此只能通过`::`操作符和内部的 get 接口获取线程池对象的地址：

```cpp
class TcpServer
{
public:
    TcpServer(/* ... */)
        /* ... */
        , _threadpool_ptr(ThreadPool<Task>::getThreadPool())
    {}
private:
    std::unique_ptr<ThreadPool<Task>> _threadpool_ptr; // 指向线程池对象的地址
};
```

## Task 类

```cpp
#pragma once
#include "Log.hpp"
#include <string>
#include <functional>

// typedef std::function<void (int, const std::string &, uint16_t &)> func_t;
// 等价于
using func_t = std::function<void(int, const std::string &, uint16_t &)>;

class Task
{
public:
	Task() {}
	Task(int sockfd, const std::string ip, uint16_t port, func_t func)
		: _sockfd(sockfd), _ip(ip), _port(port), _func(func)
	{}
	~Task() {}
	void operator()(const std::string &name)
	{
		_func(_sockfd, _ip, _port);
	}

public:
	int _sockfd;
	std::string _ip;
	uint16_t _port;
	func_t _func;
};
```

注意：

- 两种函数对象的定义方式是一样的，除此之外，还可以使用 C 风格的函数指针定义。
- `Task`是线程池的模板参数，简单地说，它会包含服务端的服务函数`service()`的地址，然后线程池会在内部的线程函数`routine()`执行它。
- `operator()`的参数是一个字符串`name`，是因为可能在测试时会打印线程的信息，例如线程 IP 或编号。在这里暂不做处理。
- `Task`类相当于一个数据包，它包含了服务端接收到的客户端 IP、PORT 以及服务套接字文件描述符，以及服务端给客户端提供服务的函数`service()`。只要客户端构造一个`Task`类型的对象，传给线程池，线程池就能在内部取出成员，然后执行`service()`。

## 服务端多线程执行任务

通过线程池指针`_threadpool_ptr`调用成员函数`run()`，实际上就是调用`pthread_create()`创建数个线程，去执行线程函数：
```cpp
class TcpServer
{
public:
    void start()
    {
        _threadpool_ptr->run(); // 线程池执行任务
        while (1) { /* ... */ }
    }
}
```

只要线程池中创建了线程，那么在任务执行前就已经有一定数量的线程在等待被分派任务了，主线程（服务端）就只要生产任务，将任务放在队列中让队列头部的线程执行。在“线程池”一文中，主线程产生的任务是进行简单的加减法，在这里，任务就是跨网络的了，不过依然很简单，用一个来自客户端的打印请求作为客户端线程的执行任务。

这也是`Task`类要有 IP 和 PORT 等网络相关的成员的原因。

## 生产任务

```cpp
void start()
{
    _threadpool_ptr->run(); // 线程池执行任务
    while (1)
    {
        // ... 
        // 线程池版本
        Task task(service_sockfd, client_ip, client_port, service); // 生产任务
        _threadpool_ptr->pushTask(task); // push 任务
    }
}
```

注意，在之前创建线程函数执行任务以后，主线程会关闭服务套接字，这个操作可以放在很多地方，在这里将它放在`service()`函数的最后：

```cpp
static void service(int service_sockfd, std::string client_ip, uint16_t client_port)
{
    while (1)
    {
        // ...
    }
    close(service_sockfd); // 关闭服务套接字
}
```

## 测试

用同样的方式测试：
<img src="./.网络编程：TCP socket.IMG/tcp_server_threadpool1.gif" alt="tcp_server_threadpool1" style="zoom:40%;" />

可以看到，只要客户端一运行起来，就会立即创建出 5 个线程（这是程序员自定义的），然后等待主线程派发任务。注意到服务端为客户端服务的线程的 PORT 是不一样的，也就说明是不同的线程（也可以在日志中增加线程信息）。

例如：

<img src="./.网络编程：TCP socket.IMG/tcp_server_threadpool2.gif" alt="tcp_server_threadpool2" style="zoom:40%;" />

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/TcpSocket/ThreadPool)

## 问题

### 长连接业务

长连接业务是指服务器与客户端建立的 TCP 连接在一定时间内保持打开状态，直到某个条件（例如超时或客户端发送指定的关闭连接请求）触发连接的关闭。

在长连接业务中，客户端可以通过一个 TCP 连接与服务器保持交互状态，发送多个请求和接收多个响应，而无需每次请求都建立和关闭连接，从而减少了建立和关闭连接的开销。这种方式可以提高客户端和服务器之间的通信效率，特别是在需要频繁进行交互的场景下，如在线游戏、即时通讯等。

长连接业务也带来了一些挑战，例如：

1. 连接的维护和管理：长时间保持连接需要服务器维护大量的连接状态信息，包括连接的建立、关闭、超时等。服务器需要对这些信息进行有效的管理和维护，避免连接状态信息过多导致服务器负载过高。

2. 数据的可靠性和有序性：长连接业务中，多个请求和响应可能会在同一个连接上进行，因此需要保证数据的可靠性和有序性。服务器需要采取相应的措施，如序列号、确认应答等机制来保证数据的可靠性和有序性。

3. 连接的安全性：长连接业务中，连接可能会存在较长时间，因此需要采取相应的安全措施，如 SSL/TLS 加密、身份验证等机制来保障连接的安全性。

因此，长连接业务需要服务器具备一定的连接管理和维护能力，以及对数据的可靠性、有序性和安全性进行有效的保障，才能更好地满足客户端的需求。

例如上面实现的例子就是长连接业务，“长”在代码上的体现就是在一个死循环中执行任务。所以要想办法在任务结束时关闭这个连接。这个例子中，只能承载 10 个客户端左右。

多进程和多线程服务器应该要限制进程和线程的数量，否则客户端如果在一个死循环中不断地申请创建进程或线程，服务器就会因为承载不了这么大的需求而瞬间挂掉。线程池的作用就是将业务逻辑和操作系统分隔，相当于它们之间的一个软件层（就像 OS 和硬件一样），它从程序层面就直接限制了申请进程和线程的数量，保证操作系统的安全。

实际上在实现服务器的时候不会简单粗暴地将业务逻辑放在一个死循环中，基本上是客户端请求服务端协助以后，服务端再去为客户端服务，不用一直执行死循环。

## 更换短业务

短业务是指客户端与服务器之间仅进行**一次**请求和响应的业务。在短业务中，客户端向服务器发送一个请求，服务器处理该请求并返回一个响应，然后连接就会被关闭，整个交互过程只持续很短的时间。

短业务通常是一些简单的请求和响应，例如查询天气、查询股票信息、搜索等，这些业务不需要客户端和服务器之间长时间的交互。在短业务中，客户端和服务器之间的连接建立和关闭的开销比较小，因此可以更快地响应客户端请求，提高业务处理效率。

> 相比之下，长连接业务则需要在客户端和服务器之间建立和维持一个较长时间的连接，这样就可以进行多次请求和响应，从而可以实现一些需要长时间交互的业务。但是长连接业务需要服务器维护大量的连接状态信息，连接的管理和维护成本也比较高。

> 短业务和长连接业务各有优缺点，具体应该根据业务需求来选择适当的交互方式。

这里用一个大写转小写的服务端函数`change()`代替原来的`service()`：

```cpp
// 短服务
static void change(int service_sockfd, std::string client_ip, uint16_t client_port, const std::string &name)
{
    char buffer[NUM]; // 以字符串作为缓冲区
    // 读取缓冲区内容
    ssize_t s = read(service_sockfd, buffer, sizeof(buffer) - 1);
    if (s > 0) // 读取成功
    {
        buffer[s] = '\0'; // 标记数据的末尾
        std::cout << name << ": "; // 显示线程编号
        std::cout << "IP[" << client_ip << "], PORT[" << client_port << "]: " << buffer << std::endl;
        
        std::string message;
        char *start = buffer;
        while (start)
        {
            char ch;
            if (islower(*start)) ch = toupper(*start);
            else ch = *start;
            message.push_back(ch);
            start++;
        }
        write(service_sockfd, message.c_str(), message.size());
    }
    else if (s == 0) // 无数据
    {
        logMessage(NORMAL, "%s: IP[%s], PORT[%u] shut down...me too", name.c_str(), client_ip.c_str(), client_port);
    }
    else // 读取失败
    {
        logMessage(ERROR, "read socket error...%d:%s", errno, strerror(errno));
    }
    close(service_sockfd);
}
```

注意到这个大写转小写的逻辑是不在死循环内部的，而是只有当服务端读取成功以后才会让线程执行任务。

在客户端中，将`initClient()`合并到`start()`中，并用一个变量标记此时客户端是否连接成功：
```cpp
bool alive = false;
void start()
{
    while (1)
    {
        if (!alive)
        {
            // 1. 创建套接字
            _sockfd = socket(AF_INET, SOCK_STREAM, 0);
            if (_sockfd < 0)
            {
                logMessage(FATAL, "%d:%s", errno, strerror(errno));
                exit(2);
            }
            logMessage(DEBUG, "%s: %d", "create socket success, sockfd", _sockfd);
            // 2. bind(OS 完成）
            // 3. 连接
            // 3.1 填充服务端信息 本地->网络
            struct sockaddr_in server;
            memset(&server, 0, sizeof(server));
            server.sin_family = AF_INET;
            server.sin_addr.s_addr = inet_addr(_ip.c_str());
            server.sin_port = htons(_port);
            // 3.2 连接
            if (connect(_sockfd, (sockaddr *)&server, sizeof(server)) < 0) // 连接失败
            {
                logMessage(FATAL, "connect()errno:%d:%s", errno, strerror(errno));
                exit(3);
            }
            logMessage(DEBUG, "start TcpClient...%s", strerror(errno)); // 连接成功
            alive = true;
        }
        // 4.0 发送并接收数据
        // 4.1 从标准输入流获取数据
        std::string message;
        std::cout << "请输入>>> ";
        std::getline(std::cin, message);
        if (message == "quit")
            break;
        else if (message.empty())
            continue;
        // 4.2 发送数据
        ssize_t s = send(_sockfd, message.c_str(), message.size(), 0);
        if (s > 0) // 发送成功
        {
            char buffer[SIZE];
            // 4.3 接收服务器返回的数据
            ssize_t s = recv(_sockfd, buffer, sizeof(buffer) - 1, 0);
            if (s > 0) // 接收成功
            {
                buffer[s] = '\0';
                std::cout << "TcpServer 回显# " << buffer << std::endl;
            }
            else if (s == 0) // 读取到 0 个字节的数据
            {
                logMessage(NORMAL, "TcpServer: IP[%s], PORT[%u] shut down...me too", _ip.c_str(), _port);
                alive = false;
                close(_sockfd);
            }
            else // 读取失败
            {
                logMessage(ERROR, "recv()errno:%d:%s", errno, strerror(errno));
                alive = false;
                close(_sockfd);
            }
        }
        else // 发送 0 个字节的数据或失败
        {
            logMessage(ERROR, "send()errno:%d:%s", errno, strerror(errno));
            alive = false;
            close(_sockfd);
        }
    }
}
```

注意：

- `alive`的作用是进行重连操作，能保证执行到“请输入>>>”时一定连接成功。
- 为了安全起见，在`send()`之前也判断一下返回值。

# 简易英译汉服务端

接入线程池后的服务端，已经可以应付小几百个的客户端需求（还可以增加线程池内的线程数量），如果想让服务端更改或增加服务，那么只要修改或增加线程函数即可。

在这里可以简单地实现一个英译汉的服务端：客户端输入英文单词，服务端返回对应的中文释义。

这是一个查询的任务，因此我们可以使用哈希表来实现，即 STL 中的`unordered_map`。将英文单词作为 key，将对应的中文释义作为 value。

## 实现

在这里只是简单地实现一个查询操作，因此并不会将整个字典映射到哈希表中，只是简单地加入几个键值对进行测试，也不考虑一词多义的情况。如果要实现较完整的功能，可以从文件中读取键值对。

```cpp
// 简易汉译英
static void enToZh(int service_sockfd, std::string client_ip, uint16_t client_port, const std::string &name)
{
    char buffer[NUM];
    static std::unordered_map<std::string, std::string> dict = {
        {"hello", "你好"},
        {"world", "世界"},
        {"mango", "芒果"},
        {"attack", "进击"}};
    while (1)
    {
        // 读取缓冲区内容
        ssize_t s = read(service_sockfd, buffer, sizeof(buffer) - 1);
        if (s > 0) // 读取成功
        {
            buffer[s] = '\0';
            std::cout << name << ": ";
            std::cout << "IP[" << client_ip << "], PORT[" << client_port << "]: " << buffer << std::endl;

            std::string message;
            auto iter = dict.find(buffer);
            if (iter == dict.end())
                message = "I don't konw...";
            else
                message = iter->second;

            write(service_sockfd, message.c_str(), message.size());
        }
        else if (s == 0) // 无数据
        {
            logMessage(NORMAL, "%s: IP[%s], PORT[%u] shut down...me too", name.c_str(), client_ip.c_str(), client_port);
            break;
        }
        else // 读取失败
        {
            logMessage(ERROR, "read socket error...%d:%s", errno, strerror(errno));
            break;
        }
    }
    close(service_sockfd);
}
```

## 测试

<img src="./.网络编程：TCP socket.IMG/image-20230515143556472.png" alt="image-20230515143556472" style="zoom:40%;" />

通过简单的测试可以实现多线程执行来自客户端的请求。

需要注意的是，`enToZh()`函数需要不断读取来自客户端的内容，否则只会在第一次执行任务，然后直接退出。

[源代码](https://gitee.com/shawyxy/2023-linux/tree/main/TcpSocket/ThreadPoolChange)

# 地址转换函数

## 介绍

在 Linux 中，有一些地址转换函数可以用来在字符串 IP 地址和整数 IP 地址之间进行转换。这些函数通常包含在以下头文件中，下面介绍几个常用的函数：

```c
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
```

1. `inet_addr()`：将字符串 IP 地址转换为 32 位整数 IP 地址。该函数的原型如下：

```c
in_addr_t inet_addr(const char *cp);
```

参数：

- `cp`：指向包含字符串 IP 地址的字符数组的指针。

返回值：

- 成功：返回一个 32 位整数 IP 地址。
- 失败：返回`INADDR_NONE`（通常是一个值为`-1`的宏）。

2. `inet_ntoa()`：将 32 位整数 IP 地址转换为字符串 IP 地址。该函数的原型如下：

```c
char *inet_ntoa(struct in_addr in);
```

参数：

- `in`：是一个`struct in_addr`类型的结构体，该结构体包含一个 32 位整数 IP 地址。

返回值：

- 成功：函数返回一个指向包含字符串 IP 地址的字符数组的指针。

需要注意的是，该函数返回的指针指向的字符数组是静态分配的，因此如果需要多次使用该函数的返回值，需要先将返回值复制到另一个缓冲区中。

3. `inet_pton()`：将字符串 IP 地址转换为网络字节序的二进制 IP 地址。该函数的原型如下：

```c
int inet_pton(int af, const char *src, void *dst);
```

参数：

- `af`：指定了地址族，可以是`AF_INET`或`AF_INET6`。`src`参数是指向包含字符串 IP 地址的字符数组的指针。
- `dst`：指向用于存储二进制 IP 地址的缓冲区的指针。

返回值：

- 成功：转换的地址族的值（`AF_INET`或`AF_INET6`）。
- 失败：
  - 如果输入的字符串 IP 无效，则返回 0。
  - 如果输入的协议家族 af 无效，则返回-1，并将 errno 设置为`EAFNOSUPPORT`。

4. `inet_ntop()`：将网络字节序的二进制 IP 地址转换为字符串 IP 地址。该函数的原型如下：

```c
const char *inet_ntop(int af, const void *src, char *dst, socklen_t size);
```

参数：

- `af`：指定了地址族，可以是`AF_INET`（IPv4）或`AF_INET6`（IPv6），表示网络通信。
- `src`：指向包含二进制 IP 地址的缓冲区的指针。
- `dst`：指向用于存储字符串 IP 地址的缓冲区的指针。
- `size`：指定了缓冲区的大小。

返回值：

- 成功：返回一个指向包含字符串 IP 地址的字符数组的指针。
- 失败：返回`NULL`。

注意：

- 在使用这些函数进行地址转换时，应该始终检查返回值以确保转换成功。如果返回值为特殊值`INADDR_NONE`或`-1`，则表示转换失败，应该相应地处理错误。
- 指针类型的`dst`参数都是一个输出型参数。

## 并发安全问题

在网络通信中，实际上只需要字符串格式 IP 转二进制数格式 IP 的函数即可，而从二进制格式 IP 转字符串格式 IP 存在的意义就是打印出来，让用户更方便地进行查看。

在上面的实践过程中，使用的是 inet_addr() 和 inet_ntoa()，因为这两个函数最简单，参数只有一个，只要接收返回值即可。但是，这两个函数在多线程并发条件下可能会出现安全问题。

### inet_ntoa()

inet_ntoa() 函数在将 32 位整数 IP 地址转换为字符串 IP 地址时存在安全问题。具体来说，该函数返回的指针指向的字符数组是静态分配的，因此如果需要多次使用该函数的返回值，请先将返回值复制到另一个缓冲区中。

这个问题的根本原因是 inet_ntoa() 函数使用了一个静态的字符数组来存储转换后的字符串 IP 地址，并且返回了一个指向该数组的指针。当多次调用 inet_ntoa() 函数时，每次调用都会覆盖该静态数组，因此之前返回的指针指向的内容也会被修改。这可能会导致潜在的安全问题，例如在多线程环境下，不同线程可能会同时调用 inet_ntoa() 函数，导致返回值被覆盖，从而导致不可预测的行为。

为了避免这个问题，可以使用 inet_nota_r() 函数代替 inet_ntoa() 函数。

与 inet_ntoa() 函数不同的是，inet_ntoa_r() 函数使用了一个用户提供的缓冲区来存储转换后的字符串 IP 地址，并且返回一个指向该缓冲区的指针。这样，多次调用该函数时，每次调用都会使用不同的缓冲区，避免了返回值被覆盖的问题。

需要注意的是，使用 inet_ntoa_r() 函数时，应该确保提供的缓冲区足够大，以容纳转换后的字符串 IP 地址。通常，可以使用 INET_ADDRSTRLEN 宏来定义缓冲区的大小，该宏定义为 16，可以容纳 IPv4 地址的字符串表示形式（例如 "192.168.0.1"）。

#### 测试

下面创建两个套接字，然后将它的二进制 IP 成员的值分别设置为`0`和`0xffffffff`，再分别调用`inet_ntoa()`函数转化，打印两次函数调用的返回值：

```cpp
#include <iostream>
#include <netinet/in.h>
#include <arpa/inet.h>
using namespace std;

int main()
{
	sockaddr_in sock1;
	sockaddr_in sock2;

	sock1.sin_addr.s_addr = 0;
	sock2.sin_addr.s_addr = 0xffffffff;

	char* ptr1 = inet_ntoa(sock1.sin_addr);
	char* ptr2 = inet_ntoa(sock2.sin_addr);

	cout << ptr1 << endl;
	cout << ptr2 << endl;

	return 0;
}
```

输出：
```text
255.255.255.255                        
255.255.255.255
```

如果要多次使用 inet_ntoa() 函数的返回值，每次调用后都要及时保存它的返回值。

在多线程条件下，这个静态的字符串内存区域相当于被所有线程共享的临界资源，如果不用互斥锁或条件变量限制线程的行为，那么很可能会发生并发问题，也就是说，inet_ntoa 函数不是线程安全的。
```cpp
#include <iostream>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <unistd.h>
using namespace std;

void*func1(void *args)
{
	sockaddr_in *sock1 = (sockaddr_in *)args;
	while (1) {
		char* ptr1 = inet_ntoa(sock1->sin_addr);
		cout << "ptr1: " << ptr1 << endl;
		sleep(1);
	}
}
void *func2(void *args)
{
	sockaddr_in *sock2 = (sockaddr_in *)args;
	while (1) {
		char* ptr2 = inet_ntoa(sock2->sin_addr);
		cout << "ptr2: " << ptr2 << endl;
		sleep(1);
	}
}

int main()
{
	sockaddr_in sock1;
	sockaddr_in sock2;
	sock1.sin_addr.s_addr = 0;
	sock2.sin_addr.s_addr = 0xffffffff;

	pthread_t pid1, pid2;
	pthread_create(&pid1, nullptr, func1, &sock1);
	pthread_create(&pid2, nullptr, func2, &sock2);

	pthread_join(pid1, nullptr);
	pthread_join(pid2, nullptr);

	return 0;
}
```

输出：
```text
ptr1: 0.0.0.0ptr2: 255.255.255.255

ptr1: 0.0.0.0ptr2: 255.255.255.255

ptr1: 0.0.0.0
ptr2: 255.255.255.255
```

不过在 centos7 中测试时，并未发现问题，这可能是这个版本的 Linux 实现函数时使用了线程安全限制。

### inet_addr()

inet_addr() 函数在将字符串 IP 地址转换为 32 位整数 IP 地址时也存在安全问题。具体来说，该函数的返回值是一个 32 位整数，如果转换失败，则返回一个特殊值 INADDR_NONE，此时可能会出现一些安全问题。

例如，在某些情况下，可能会使用 inet_addr() 函数将用户输入的字符串 IP 地址转换为 32 位整数 IP 地址，如果用户输入的字符串无法被正确转换，则 inet_addr() 函数将返回 INADDR_NONE。攻击者可以通过构造恶意的字符串 IP 地址来触发 inet_addr() 函数的这种行为，并从而导致潜在的安全问题，例如拒绝服务攻击等。

为了避免这个问题，可以使用 inet_pton() 函数代替 inet_addr() 函数。

与 inet_addr() 函数不同的是，inet_pton() 函数在转换字符串 IP 地址时使用了一个缓冲区来存储转换后的二进制 IP 地址，并且返回一个整数值来指示转换的结果。如果转换成功，则返回转换后的地址族的值（AF_INET 或 AF_INET6），如果转换失败，则返回 -1。这样，我们可以根据返回值来检查转换是否成功，并进一步处理错误。

需要注意的是，在使用 inet_pton() 函数进行地址转换时，应该始终检查返回值以确保转换成功。如果返回值为 -1，则表示转换失败，应该相应地处理错误。

# 其他问题

## 资源释放问题

在上面的测试中，端口号可能一会是 8080，一会是 8081，这是因为当客户端连接服务端时，如果服务端直接被关闭，那么服务端再次绑定上次的端口号时可能会绑定失败，直接退出可能会导致服务端的资源未完全释放完全。

具体细节涉及 TCP 协议，在这里仅解释原因。

## 无法绑定

绑定失败的另一大原因是其他进程已经绑定了端口号。

一般云服务器只能绑定 1024 及以上的端口号，因为被保护的端口号已经被内置的服务使用了。在测试时，一般绑定 8000 及以上的端口号。

> 云服务器上即使代码没有问题也不一定能访问成功，这是因为云服务器可能没有开放端口解决办法是在云服务器上开放安全组。
