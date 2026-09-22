# 项目工作约定

## 版本号更新
- 每次发版前必须先询问用户：更新大版本（v3.x → v4.0）还是小版本（v3.0 → v3.1），不得自行决定。
- 版本号集中管理在 extract_tool.py 的 `APP_VERSION`；打包 spec / dist exe / 桌面 exe 命名需与之一致。
- 打包后 exe 需同步复制到桌面（`%USERPROFILE%\Desktop\招标文件快速解压工具_vX.Y.exe`）。

## 打包
- 打包命令：`python -m PyInstaller 招标文件快速解压工具_vX.Y.spec`（在项目根目录）。
- spec 由上一版本复制改名（改 EXE 的 name），binaries 含项目根的 aria2c.exe，
  datas 含 fonts/ 与 aria2 许可文本，hiddenimports 含 tkinterdnd2，单文件 windowed。

## 测试
- 发版前必须全量跑通：`python -X utf8 -m unittest test_extract_tool -v`。

## 项目要点
- 附件下载用随包内嵌的 aria2c.exe（binaries 内嵌；运行期经 sys._MEIPASS/程序目录定位）。
  程序自行拉起 aria2 引擎（随机空闲端口 + 随机 rpc-secret）并经本地 JSON-RPC 控制，
  不再依赖 Motrix；源码运行需项目根存在 aria2c.exe；退出时 atexit 关闭引擎。
- 安庆 .AQZF 内层加密清单解密：PBZB.xml 的 ZBInfoMx 收集全部 EncryKey（多标段逐个尝试），
  MD5(EncryKey) 前8/后8字节轮换 → AES-128-ECB/PKCS7；EncryQingDan 除 "0"/"false" 外均尝试解密。
- AES 优先 pycryptodome（C 实现），未安装回退内置纯 Python；两者结果已对拍一致。
