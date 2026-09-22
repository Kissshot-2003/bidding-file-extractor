# 第三方组件与开源许可声明（Third-Party Notices）

本仓库**主程序**（`extract_tool.py` 及其构建产物）以 **MIT** 许可发布，详见 [LICENSE](LICENSE)。

为提供「内置附件下载」能力，本仓库同时分发下列第三方可执行程序。该程序以**独立可执行文件**形式随附（聚合分发 / mere aggregation），运行时仅通过本机进程间 JSON-RPC 与之通信，**未与本项目源代码静态链接、亦未合并编译为同一衍生作品**，因此不影响本项目自身的 MIT 授权。

---

## 1. aria2（`aria2c.exe`）

| 项目 | 说明 |
|---|---|
| 组件 | aria2c（aria2） |
| 版本 | 1.37.0（Windows 64-bit build 1） |
| 许可 | **GNU General Public License v2.0**（GPL-2.0） |
| 许可证全文 | [aria2_COPYING.txt](aria2_COPYING.txt) |
| 源代码获取 | https://github.com/aria2/aria2 （release tag `release-1.37.0`：https://github.com/aria2/aria2/releases/tag/release-1.37.0 ） |
| 官网 | https://aria2.github.io/ |

依据 GPL-2.0 第 1 条，本仓库随附其许可证全文（`aria2_COPYING.txt`），未修改其版权声明；
依据 GPL-2.0 第 3 条，上文给出对应源代码（`release-1.37.0`）的公开获取途径。

> 说明：本项目不修改 aria2 源码，仅原样分发其官方预编译的 `aria2c.exe`。

## 2. OpenSSL（aria2 的依赖）

| 项目 | 说明 |
|---|---|
| 说明 | aria2 的 Windows 构建包含 OpenSSL 库 |
| 许可 | 见 [aria2_LICENSE.OpenSSL.txt](aria2_LICENSE.OpenSSL.txt)（OpenSSL License + SSLeay License） |
| 项目主页 | https://www.openssl.org/ |

## 3. 其他第三方库

aria2 的 Windows 官方发行包还包含 zlib、expat、libsqlite3、c-ares、libssh2 等以宽松许可（MIT/BSD/zlib 等）发布的库。
其版权与许可证信息随 aria2 官方发行包一并提供：
https://github.com/aria2/aria2/releases/tag/release-1.37.0

---

## 许可兼容性说明

- 本项目主程序为 **MIT**。
- 内嵌的 **aria2c.exe 为 GPL-2.0**，属**独立分发的聚合组件**，不是本项目的衍生作品；
  本项目的 MIT 许可 **不延伸覆盖** aria2c.exe，其仍单独受 GPL-2.0 约束。
- 若你**二次分发**本项目（含其构建的 exe），请一并保留本声明、`aria2_COPYING.txt`
  与 `aria2_LICENSE.OpenSSL.txt`，并保留 aria2 源码的获取途径，以符合 GPL-2.0 要求。
- 若你**仅分发主程序源码（不含 aria2c.exe）**：源码运行需要自行获取 aria2c.exe，
  此时 GPL-2.0 的再分发义务由获取者/分发者自行承担。
