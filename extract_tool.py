"""
招标文件解压工具 (*.zf / *.cf → ZIP，解压前文件)
支持任意前缀的 *zf / *cf 格式：.zf, .cf, .aqzf, .tlzf, .hnzf, .czzf, .sczf, .xizf,
.szcf, .tlcf，以及任何字母/数字前缀（如 .xdzf、.2026cf）——只要扩展名以 zf 或 cf 结尾
支持格式学习更新：成功解压未知格式后自动记忆，下次选择文件时自动包含

v2.7 变更：
  - 修复：部分平台附件链接（如 epoint/新点 TuZhiDocShow 图纸查看页）是
    HTML 页面而非文件——此前直接提交 Motrix 会"成功"下载到 4KB 网页
    （表现为文件损坏）。现于提交前自动解析：探测响应为 HTML → 请求
    epoint 同名 Action.action 接口 → 取 JSON 中 custom.serverFilePath
    真实文件直链（该链路无需登录态），Referer 设为原页面
  - 增强：下载完成后嗅探文件头，若仍为网页（链接过期/平台拦截）行内
    明确报错并引导「浏览器」打开，不再产生看似成功的坏文件
  - 新增 _resolve_attachment_url 解析层与 _looks_like_html /
    _epoint_action_url / _parse_epoint_server_file_path 可测组件

v2.6 变更：
  - 新功能：Motrix 无头下载——通过 Motrix 持久化的本地 aria2 RPC 配置
    （%APPDATA%/Motrix/settings.json 的 rpcPort/rpcSecret）直接 addUri：
    不弹 Motrix 窗口、任务自动开始，dir=附件归属项目输出目录、out=附件
    文件名，allow-overwrite 保证「重新下载」可覆盖旧文件
  - 新功能：附件栏逐行渲染——每行文件名 + 实时进度条 + 速度/进度文本
  - 新功能：行内按钮「暂停/继续/停止/重新下载/浏览器」，头部「全部下载」
    一键提交全部附件；Motrix 未运行时自动拉起并轮询引擎就绪（约 30 秒）
  - 调整：行状态机 idle→starting→active→paused→complete/error/stopped，
    后台线程 1 秒轮询 tellStatus 经队列回传 UI，界面不卡顿；
    RPC 不可用时行内显示明确错误，浏览器按钮始终兜底

v2.5 变更：
  - 调整：附件下载由「浏览器下载」改为「Motrix 下载」——把选中附件的
    链接批量组装为 motrix:// 深度链接调起 Motrix「新建任务」窗口
    （每行一条自动预填，确认后开始下载；Motrix 未运行会被系统自动拉起），
    下载任务统一进 Motrix 队列，多线程/限速/保存目录由 Motrix 管理
  - 增强：未检测到 motrix:// 协议（未安装 Motrix）时自动回退
    系统浏览器逐条打开链接，行为与旧版一致

v2.4 变更：
  - 修复：exe 打包版「格式学习记忆丢失」——onefile 运行时 __file__ 指向
    临时解包目录 _MEIPASS，导致 format_registry.json 等配置每次写到临时目录、
    下次启动即丢失（表现为每次解压都在「★ 已学习新格式」）。
    现改为 exe 所在目录持久化；目录不可写时回退 %APPDATA%\招标文件快速解压工具
  - decrypt_config.json 打包运行时优先从 exe 目录读取（随包模板），
    其次配置目录；源码运行时行为不变
  - 附带：ui_config.json（勾选状态）与错误日志同样落盘配置目录，同源修复

v2.3 变更：
  - 多项目归属：批量解压多个招标文件时，附件按「项目分组」在右栏展示
    （分隔行=项目名，附件行带分类名），每个附件记录其归属项目与输出目录，
    浏览器下载只打开所选项目自己的链接，杜绝下错位置
  - 右栏标题显示「N 个附件 · M 项目」；解压与下载日志均带 [项目 | 分类]

v2.2 变更：
  - 布局：可下载附件栏移到「待解压文件」右侧独立一栏（左右分栏），
    不再横插在进度/日志之间遮挡信息流；附件列表与按钮随栏常驻
  - 增强：解压完成弹窗明确提示「成功 N 个文件 + 附件数 + 输出目录」
    （此前仅状态栏/日志提示，容易漏看）；完成后打开输出目录仍可勾选
  - GUI 窗口扩为 920x640（左右分栏需要更宽）

v2.1 变更：
  - 调整：附件下载改为「浏览器下载」——直接调用系统浏览器打开链接。
    附件多为招投标平台登录后下载（需会话/鉴权），浏览器可靠可用，
    比程序直连成功率高；解压完成自动弹出附件面板并附提示
  - 保留库级 _download_attachment 直连能力（默认不启用 GUI 直连）

v2.0 变更：
  - 新功能：附件链接识别与选择下载。解压时自动解析容器内元数据
    （PBZB.xml 等，含被内部规则跳过写盘的文件）与已交付文本条目，
    识别 <ZBFileCAD><CADMuLu><CADFile> 风格的可下载文件链接
    （图纸/清单控制价等：分类 MuLuName、文件名 CADTenderName、URL CADFileName），
    也兜底扫描任意 *CADFile* 变体与 <fileUrl/href/src> URL；&amp; 已解码
  - 新功能：GUI 解压完成后出现「可下载附件」面板——按分类列名、多选、
    全选；「浏览器下载」逐项调用系统浏览器打开链接
  - 新功能：--auto 模式下识别到附件在日志给出摘要（GUI 手动选择下载）

v1.9 变更：
  - 增强：解压增量校验——每个条目录出时累计 CRC32 并与 zip 原始记录比对，
    不一致（数据损坏/加密密钥或算法错误）即拦截该条目并清理残留，
    防止错误的解密产物混入结果目录（与 v1.8 单条目容错联动）
  - 增强：解压后生成 _SHA256SUMS.txt 校验清单（SHA-256 + 文件名，
    sha256sum 兼容格式），日志同时输出摘要；GUI 可勾选开关并记忆，
    --auto 默认开启，可用 --no-checksum 关闭
  - 性能：SHA-256 与 CRC32 随流式拷贝增量计算，无多余磁盘 IO 与内存开销

v1.8 变更：
  - 修复：保存格式注册表时读取仍在用纯 utf-8，若用户曾用记事本/PowerShell
    写入 BOM，会导致 JSONDecodeError 使学习结果静默丢失（现已统一 utf-8-sig）
  - 增强：--auto 新增 --quiet（静默：不弹结果框、不自动打开输出目录，适合脚本；
    退出码语义不变：0 成功 / 1 有失败或取消 / 2 无有效输入）与 --recursive（目录递归）
  - 增强：GUI 解压中可随时「取消解压」（当前条目停手、剩余文件跳过，取消不计入失败）
  - 增强：单个 ZIP 条目读取/写入失败只跳过该条目并告警，不再中断整个文件；
    失败碎片自动清理，已解出的其他文件不受影响

v1.7 变更：
  - 界面美化：浅色现代风格（卡片分区 + 蓝色主色调），「开始解压」改为
    醒目主按钮，日志按成功/失败/告警着色，列表空时显示拖放提示，
    进度条旁显示百分比，状态栏移至窗口底部
  - 高分屏适配：启用 Per-Monitor DPI 感知，高分屏文字不再发虚
  - 图标：窗口/任务栏使用应用图标；打包 exe 内嵌多尺寸 .ico
  - 自动解压小窗同步套用新样式

v1.6 变更：
  - 性能：大文件内存占用从约 4~5 倍文件体积降至接近流式水平——
    改用 mmap 字节级定位内容标签，Base64 分块流式解码到临时文件，
    全程不再整文件转字符串、不再整段 Base64 驻留内存
  - 修复：「覆盖已存在文件」此前实际会改名为 (1) 而非覆盖；
    现在语义正确：勾选覆盖→替换同名旧文件，不勾选→跳过并记录日志
  - 增强：解压改为后台线程执行，界面不再卡死「无响应」，
    日志经队列回传主线程刷新，可随时查看进度
  - 增强：命令行 --auto 自动模式——拖文件到 exe 上即自动解压并退出，
    支持 --out 指定输出目录，退出码可用于脚本判断（0 成功 / 1 有失败 / 2 无输入）
  - 增强：支持把文件/文件夹直接拖到已打开的窗口里添加（tkinterdnd2，
    缺失该库时自动退化为原行为）；命令行与拖放现在也接受文件夹
  - 增强：记住「覆盖」「完成后打开目录」两个勾选状态（ui_config.json）
  - 增强：错误日志超过 1MB 自动轮转为 .old，防止无限增长
  - 修复：JSON 配置（格式注册表/解密配置/界面配置）改用 utf-8-sig 读取，
    容忍记事本、PowerShell 等工具编辑后留下的 BOM，避免学习结果静默丢失
  - 新增：unittest 单元测试（test_extract_tool.py），覆盖核心解压逻辑
  - 清理：移除残留死代码，重写输出路径冲突处理逻辑

v1.5 变更：
  - 修复：解除扩展名与内容标签的强绑定。此前 .xczf 等未知扩展名会按后缀
    映射到 ZBFileContent 单一标签，命中不了 DYFileContent 即报错；
    现在依次尝试「注册表映射 → ZBFileContent → DYFileContent」，
    全部未命中再泛化匹配任意 <XXXFileContent> 标签
  - 扩大支持类型：泛化 *FileContent 匹配使未来任何新变体（如答疑、澄清、
    补遗等衍生格式）无需改代码即可解压；学习机制记录实际命中的标签

v1.4 变更：
  - 扩大文件支持范围：不再局限于内置扩展名清单，凡以 zf / cf 结尾的扩展名
    一律接受（前缀可为任意字母或数字），文件选择对话框与文件夹扫描同步放宽

v1.3 优化：
  - 修复：XML 头检测容忍 UTF-8 BOM 与前导空白，避免带 BOM 的文件被误判失败
  - 修复：ZIP 条目名按 UTF-8 标志位(bit 11)正确解码，GBK 中文名不再可能被误解码
  - 修复：错误日志显式记录传入的异常堆栈，不再依赖调用点是否处于 except 块
  - 重构：核心解压逻辑抽为模块级 extract_file()，与 GUI 解耦，便于测试与命令行复用
  - 性能：AES CBC 异或改用整型批量运算；大文件改用流式拷贝，降低内存占用
  - 增强：ZIP 内部同名文件自动加序号(1)(2)…，防止互相覆盖造成丢文件
  - 增强：解压总大小防护（默认 2GB，可配置），防止异常巨型文件拖垮磁盘
  - 增强：UI 增加「移除选中」按钮、双击列表项打开所在文件夹、日志带时间戳
  - 增强：支持命令行传入文件路径（可直接把文件拖到 exe 上 / 发送到本工具）
  - 保留：可插拔 AES 解密钩子（decrypt_config.json），排除内部文件（PBZB.xml 等）

v1.2 变更：
  - 排除内部文件（如 PBZB.xml 工程清单控制文件），只导出交付文件，与官方工具一致。
  - 对加密容器（如 .ahaqslzb 造价文件）增加「可插拔 AES 解密钩子」：
      解密配置见同目录 decrypt_config.json（默认关闭）。
      未配置密钥时，该文件会按原样导出密文，并在日志中告警。
"""

import os
import sys
import re
import base64
import json
import zlib
import hashlib
import zipfile
import shutil
import traceback
import io
import mmap
import binascii
import tempfile
import queue
import threading
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_config_dir():
    """持久化配置目录（格式注册表/界面状态/错误日志等）：
    - 源码运行时：源码所在目录（开发机习惯不变）
    - PyInstaller 打包运行时：exe 所在目录；该目录不可写（如 Program Files）
      时回退 %APPDATA%\\招标文件快速解压工具——解决 onefile 下 __file__ 指向
      临时解包目录 _MEIPASS 导致「每次启动都重新学习格式、记忆丢失」的问题。
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        probe = os.path.join(exe_dir, f".writetest_{os.getpid()}")
        try:
            with open(probe, "w") as f:
                f.write("x")
            os.remove(probe)
            return exe_dir
        except Exception:
            pass
        ap = os.path.join(os.environ.get("APPDATA", ""), "招标文件快速解压工具")
        try:
            os.makedirs(ap, exist_ok=True)
            return ap
        except Exception:
            return exe_dir
    return APP_DIR


CONFIG_DIR = _resolve_config_dir()
ERROR_LOG = os.path.join(CONFIG_DIR, "extract_error.log")
FORMAT_REGISTRY = os.path.join(CONFIG_DIR, "format_registry.json")
DECRYPT_CONFIG = os.path.join(CONFIG_DIR, "decrypt_config.json")
UI_CONFIG = os.path.join(CONFIG_DIR, "ui_config.json")
LOG_MAX_BYTES = 1 << 20
APP_VERSION = "v2.7"
BUILTIN_FORMATS = {"zf": "ZBFileContent", "cf": "DYFileContent"}
# 已知常见格式（用于文件对话框精确列出）；实际接受范围更广，见 _is_supported_ext()
BUILTIN_EXTENSIONS = ["zf", "cf", "aqzf", "tlzf", "hnzf", "czzf", "sczf", "xizf", "szcf", "tlcf"]


def _is_supported_ext(ext):
    """扩展名是否受支持：ext 为不带点的后缀（如 'aqzf'、'2026cf'）。
    规则：以 zf 或 cf 结尾即接受，前缀可为任意字母/数字/点等。"""
    ext = (ext or "").lower()
    return ext.endswith("zf") or ext.endswith("cf")

# 内部/控制文件：官方工具不当作交付文件导出，这里默认排除（可经 decrypt_config.json 追加）。
INTERNAL_FILES = {"PBZB.xml"}
# 已知需要解密的导出容器扩展名（用于在未配置密钥时给出告警提示）。
KNOWN_ENCRYPTED_EXTS = {".ahaqslzb"}
# 单次解压总量上限（字节），防 zip 炸弹；可通过环境变量 EXTRACT_MAX_SIZE 覆盖。
MAX_TOTAL_SIZE = int(os.environ.get("EXTRACT_MAX_SIZE", 2 * 1024 ** 3))  # 默认 2GB


def _log(msg, exc=None):
    """写错误日志（与 GUI 无关）。exc 为异常对象时显式格式化其堆栈。
    超过 1MB 自动轮转为 .old，防止无限增长。"""
    try:
        if os.path.exists(ERROR_LOG) and os.path.getsize(ERROR_LOG) > LOG_MAX_BYTES:
            try:
                os.replace(ERROR_LOG, ERROR_LOG + ".old")
            except Exception:
                pass
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
            if exc is not None:
                lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
                f.write("".join(lines) + "\n")
    except Exception:
        pass


def _load_registry():
    learned = {}
    try:
        if os.path.exists(FORMAT_REGISTRY):
            # utf-8-sig：容忍记事本/PowerShell 等工具写入的 BOM
            with open(FORMAT_REGISTRY, "r", encoding="utf-8-sig") as f:
                learned = json.load(f)
    except Exception:
        pass
    registry = dict(BUILTIN_FORMATS)
    registry.update(learned)
    return registry, learned


def _save_learned_format(ext, tag):
    try:
        learned = {}
        if os.path.exists(FORMAT_REGISTRY):
            # utf-8-sig：容忍记事本/PowerShell 等工具写入的 BOM，避免学习结果静默丢失
            with open(FORMAT_REGISTRY, "r", encoding="utf-8-sig") as f:
                learned = json.load(f)
        learned[ext] = tag
        with open(FORMAT_REGISTRY, "w", encoding="utf-8") as f:
            json.dump(learned, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _log(f"保存格式注册表失败: {e}")


def _get_format_extensions(learned):
    all_exts = list(set(BUILTIN_EXTENSIONS) | set(learned.keys()))
    all_exts.sort()
    return all_exts


# ============================================================================
# 纯 Python AES（ECB / CBC，支持 128/192/256）—— 零依赖，便于打包进 exe。
# 正确性已用 cryptography 库对照验证。
# ============================================================================
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i

_RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36,
         0x6c,0xd8,0xab,0x4d,0x9a,0x2f,0x5e,0xbc,0x63,0xc6,0x97,0x35,0x6a,0xd4,0xb3,0x7d,0xfa,0xef,0xc5,0x91]
_NB = 4


def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11b
    return a & 0xff


def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p & 0xff


def _key_expansion(key):
    Nk = len(key) // 4
    Nr = Nk + 6
    w = []
    for i in range(Nk):
        w.append(list(key[4*i:4*i+4]))
    for i in range(Nk, _NB * (Nr + 1)):
        temp = list(w[i - 1])
        if i % Nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[b] for b in temp]
            temp[0] ^= _RCON[i // Nk - 1]
        elif Nk > 6 and i % Nk == 4:
            temp = [_SBOX[b] for b in temp]
        prev = w[i - Nk]
        w.append([temp[j] ^ prev[j] for j in range(4)])
    return w, Nr


def _add_round_key(state, w, r):
    for c in range(_NB):
        for row in range(4):
            state[row][c] ^= w[r * _NB + c][row]


def _sub_bytes(state, inv=False):
    sbox = _INV_SBOX if inv else _SBOX
    for r in range(4):
        for c in range(_NB):
            state[r][c] = sbox[state[r][c]]


def _shift_rows(state, inv=False):
    for r in range(1, 4):
        if inv:
            state[r] = state[r][-r:] + state[r][:-r]
        else:
            state[r] = state[r][r:] + state[r][:r]


def _mix_columns(state, inv=False):
    for c in range(_NB):
        col = [state[r][c] for r in range(4)]
        if inv:
            t0 = _gmul(col[0],14) ^ _gmul(col[1],11) ^ _gmul(col[2],13) ^ _gmul(col[3],9)
            t1 = _gmul(col[0],9)  ^ _gmul(col[1],14) ^ _gmul(col[2],11) ^ _gmul(col[3],13)
            t2 = _gmul(col[0],13) ^ _gmul(col[1],9)  ^ _gmul(col[2],14) ^ _gmul(col[3],11)
            t3 = _gmul(col[0],11) ^ _gmul(col[1],13) ^ _gmul(col[2],9)  ^ _gmul(col[3],14)
        else:
            t0 = _gmul(col[0],2) ^ _gmul(col[1],3) ^ col[2] ^ col[3]
            t1 = col[0] ^ _gmul(col[1],2) ^ _gmul(col[2],3) ^ col[3]
            t2 = col[0] ^ col[1] ^ _gmul(col[2],2) ^ _gmul(col[3],3)
            t3 = _gmul(col[0],3) ^ col[1] ^ col[2] ^ _gmul(col[3],2)
        state[0][c], state[1][c], state[2][c], state[3][c] = t0, t1, t2, t3


def _bytes_to_state(b):
    return [[b[r + 4*c] for c in range(_NB)] for r in range(4)]


def _state_to_bytes(s):
    return bytes(s[r][c] for c in range(_NB) for r in range(4))


def _aes_decrypt_block(block, w, Nr):
    state = _bytes_to_state(block)
    _add_round_key(state, w, Nr)
    _shift_rows(state, inv=True)
    _sub_bytes(state, inv=True)
    for rnd in range(Nr - 1, 0, -1):
        _add_round_key(state, w, rnd)
        _mix_columns(state, inv=True)
        _shift_rows(state, inv=True)
        _sub_bytes(state, inv=True)
    _add_round_key(state, w, 0)
    return _state_to_bytes(state)


def _aes_encrypt_block(block, w, Nr):
    state = _bytes_to_state(block)
    _add_round_key(state, w, 0)
    for rnd in range(1, Nr):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, w, rnd)
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, w, Nr)
    return _state_to_bytes(state)


def _xor16(a, b):
    """按 16 字节整型异或（比逐字节生成器快数倍）。"""
    return (int.from_bytes(a, "little") ^ int.from_bytes(b, "little")).to_bytes(16, "little")


def aes_cbc_decrypt(ciphertext, key, iv):
    if len(key) not in (16, 24, 32):
        raise ValueError("AES key must be 16/24/32 bytes")
    if len(ciphertext) % 16 != 0 or len(iv) != 16:
        raise ValueError("ciphertext must be multiple of 16 and iv 16 bytes")
    w, Nr = _key_expansion(key)
    out = bytearray()
    prev_int = int.from_bytes(iv, "little")
    for i in range(0, len(ciphertext), 16):
        blk = ciphertext[i:i+16]
        dec = _aes_decrypt_block(blk, w, Nr)
        out += (int.from_bytes(dec, "little") ^ prev_int).to_bytes(16, "little")
        prev_int = int.from_bytes(blk, "little")
    return bytes(out)


def aes_cbc_encrypt(plaintext, key, iv):
    if len(key) not in (16, 24, 32):
        raise ValueError("AES key must be 16/24/32 bytes")
    if len(plaintext) % 16 != 0 or len(iv) != 16:
        raise ValueError("plaintext must be multiple of 16 and iv 16 bytes")
    w, Nr = _key_expansion(key)
    out = bytearray()
    prev_int = int.from_bytes(iv, "little")
    for i in range(0, len(plaintext), 16):
        blk = plaintext[i:i+16]
        xored = (int.from_bytes(blk, "little") ^ prev_int).to_bytes(16, "little")
        enc = _aes_encrypt_block(xored, w, Nr)
        out += enc
        prev_int = int.from_bytes(enc, "little")
    return bytes(out)


def aes_ecb_decrypt(ciphertext, key):
    if len(key) not in (16, 24, 32):
        raise ValueError("AES key must be 16/24/32 bytes")
    if len(ciphertext) % 16 != 0:
        raise ValueError("ciphertext must be multiple of 16")
    w, Nr = _key_expansion(key)
    out = bytearray()
    for i in range(0, len(ciphertext), 16):
        out += _aes_decrypt_block(ciphertext[i:i+16], w, Nr)
    return bytes(out)


def pkcs7_unpad(data):
    if not data:
        return data
    pad = data[-1]
    if pad < 1 or pad > 16:
        return data
    if data[-pad:] != bytes([pad]) * pad:
        return data
    return data[:-pad]


# ============================================================================
# 解密配置与钩子
# ============================================================================
def _load_decrypt_config():
    """读取 decrypt_config.json。返回 (rules_dict, exclude_set)。
    打包运行时先找 exe 目录（随包模板），再找配置目录（回退 APPDATA）。"""
    exclude = set(INTERNAL_FILES)
    rules = {}
    path = None
    for cand in (os.path.join(APP_DIR, "decrypt_config.json"),
                 os.path.join(CONFIG_DIR, "decrypt_config.json")):
        if os.path.exists(cand):
            path = cand
            break
    try:
        if path:
            with open(path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            for x in cfg.get("exclude_files", []):
                exclude.add(x)
            rules = cfg.get("rules", {})
    except Exception as e:
        _log(f"读取解密配置失败: {e}")
    return rules, exclude


def _decode_secret(s, fmt):
    if not s:
        return b""
    fmt = (fmt or "hex").lower()
    if fmt == "hex":
        return bytes.fromhex(s)
    if fmt == "base64":
        return base64.b64decode(s)
    if fmt in ("text", "utf8", "utf-8"):
        return s.encode("utf-8")
    return s.encode("latin1")


def _try_aes_decrypt(data, rule):
    key = _decode_secret(rule.get("key", ""), rule.get("key_format", "hex"))
    if len(key) not in (16, 24, 32):
        raise ValueError("密钥长度必须为 16/24/32 字节")
    mode = (rule.get("mode", "CBC") or "CBC").upper()
    iv = _decode_secret(rule.get("iv", ""), rule.get("iv_format", "hex"))
    body = data
    if rule.get("iv_from_ciphertext"):
        iv = data[:16]
        body = data[16:]
    if mode == "ECB":
        out = aes_ecb_decrypt(body, key)
    elif mode == "CBC":
        if len(iv) != 16:
            raise ValueError("CBC 模式需要 16 字节 IV（或通过 iv_from_ciphertext 从密文取）")
        out = aes_cbc_decrypt(body, key, iv)
    else:
        raise ValueError("仅支持 AES ECB / CBC")
    if rule.get("strip_pkcs7", True):
        out = pkcs7_unpad(out)
    return out


def _decrypt_if_needed(basename, data, rules):
    """
    若 basename 命中某个解密规则且已启用并配置了密钥，则尝试 AES 解密。
    返回 (out_data, decrypted_bool, warn_msg)。
    """
    ext = os.path.splitext(basename)[1].lower()
    rule = rules.get(ext)
    if not rule or not rule.get("enabled") or not rule.get("key"):
        if ext in KNOWN_ENCRYPTED_EXTS:
            return data, False, f"该文件为加密容器（*{ext}），未配置解密密钥，已按原样导出密文"
        return data, False, None
    try:
        out = _try_aes_decrypt(data, rule)
    except Exception as e:
        return data, False, f"解密失败：{e}（已按原样导出密文）"
    if rule.get("verify_xml", True):
        head = out[:60]
        if not (head[:3] == b"\xef\xbb\xbf" or head[:5] == b"<?xml" or b"<?xml" in head):
            return data, False, "解密校验失败：输出不是 XML，密钥/算法可能不正确（已按原样导出密文）"
    return out, True, None


def _decode_zip_name(zi):
    """按 ZIP 规范解码条目名：flag bit 11 表示 UTF-8，否则按 cp437→GBK 回退。"""
    if zi.flag_bits & 0x800:
        return zi.filename
    try:
        return zi.filename.encode("cp437").decode("gbk")
    except Exception:
        return zi.filename


def _resolve_target(directory, base, used_names, overwrite, log=None):
    """决定输出路径，语义：
    - 不允许覆盖且磁盘已有同名 → 返回 None（由调用方跳过）
    - 允许覆盖且磁盘已有同名 → 直接用原名替换旧文件
    - 本次 ZIP 内部重名 → 自动加 (1)(2)… 序号，防止互相覆盖
    """
    target = os.path.join(directory, base)
    fresh = base not in used_names
    if fresh and not os.path.exists(target):
        used_names.add(base)
        return target
    if fresh and overwrite:
        used_names.add(base)
        if log:
            log(f"  ↻ 覆盖已有文件: {base}")
        return target
    if fresh:
        return None
    stem, ext = os.path.splitext(base)
    i = 1
    while True:
        cand_base = f"{stem}({i}){ext}"
        cand = os.path.join(directory, cand_base)
        if cand_base not in used_names and (overwrite or not os.path.exists(cand)):
            used_names.add(cand_base)
            return cand
        i += 1


# ============================================================================
# 附件链接识别：容器内部 XML/JSON 中的可下载文件链接（图纸/清单控制价等）
# ============================================================================
# 参与附件解析的文本型条目后缀（内部元数据可能被排除写盘，仍需读取解析）
ATTACH_TEXT_EXTS = {".xml", ".json", ".txt", ".htm", ".html"}
DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _extract_attachments(text):
    """从容器内文本条目（XML/JSON/TXT）中解析可下载附件列表。
    优先解析六安/安徽平台风格的 <ZBFileCAD><CADMuLu MuLuName="分类"><CADFile
    CADTenderName="文件名" CADFileName="http…"/>；其余 *CADFile/CADFile* 变体
    与任意结构化 URL 属性兜底。返回 [{category, name, url}]（去重保序，URL 解 &amp;）。"""
    out = []
    seen = set()

    def add(cat, name, url):
        if not url or not url.lower().startswith(("http://", "https://")):
            return
        url = url.replace("&amp;", "&")
        if url in seen:
            return
        seen.add(url)
        name = (name or "").strip()
        if not name:
            tail = url.split("?")[0].rstrip("/").split("/")[-1]
            name = tail[:40] or url[:40]
        out.append({"category": (cat or "").strip() or "附件", "name": name, "url": url})

    try:  # 结构化解析：CADFile 变体尽量覆盖
        from xml.etree import ElementTree as ET
        root = ET.fromstring(text)
        for mu in root.iter("CADMuLu"):
            cat = (mu.get("MuLuName") or "").strip()
            for cf in mu.iter("CADFile"):
                add(cat, cf.get("CADTenderName"), cf.get("CADFileName"))
        for el in root.iter():
            cl = (el.tag or "").lower()
            if "cadfile" in cl:
                add(el.get("MuLuName"), el.get("CADTenderName") or el.get("name"),
                    el.get("CADFileName") or el.get("fileUrl") or el.get("href"))
            for attr in ("fileUrl", "DownLoadUrl", "downloadUrl", "href", "src", "Url", "url"):
                add(None, None, el.get(attr))
    except Exception:
        pass

    # 兜底：任意位置裸 URL（含 CDATA / 非属性文本）
    for m in re.finditer(r"https?://[^\s\"'<>]+", text):
        add(None, None, m.group(0))
    return out


def _dedup_attachments(raw):
    """按 (name, url) 去重，保持首次顺序。"""
    seen, out = set(), []
    for a in raw:
        key = (a["name"], a["url"])
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def _download_attachment(url, target_dir, name, log=None):
    """尽力直连下载附件到 target_dir。成功返回文件路径。
    若服务器返回 HTML 页面（需要浏览器会话/鉴权而非文件），抛 ValueError
    （GUI 捕获后提示用浏览器打开）。"""
    log = log or (lambda _m: None)
    from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor
    from urllib.error import URLError, HTTPError
    import http.cookiejar

    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = Request(url.replace("&amp;", "&"),
                  headers={"User-Agent": DEFAULT_UA, "Accept": "*/*",
                           "Accept-Language": "zh-CN,zh;q=0.9"})
    resp = opener.open(req, timeout=45)
    ctype = (resp.headers.get("Content-Type") or "").lower()
    body_head = resp.read(8 if "text/html" in ctype else 32)
    if "text/html" in ctype:
        raise ValueError("服务器返回网页（可能需要浏览器会话/身份验证），请改用 Motrix 或浏览器打开")

    fname = _safe_filename(name) or "download"
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, fname)
    if os.path.exists(target):
        stem, ext = os.path.splitext(fname)
        i = 1
        while os.path.exists(os.path.join(target_dir, f"{stem}({i}){ext}")):
            i += 1
        target = os.path.join(target_dir, f"{stem}({i}){ext}")

    total = 0
    with open(target, "wb") as f:
        f.write(body_head)
        total += len(body_head)
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    return target


def _safe_filename(name):
    """清洗文件名非法字符。"""
    name = (name or "").strip()
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    return name[:240]


# ---------------------------------------------------------------------------
# Motrix 下载器集成（motrix:// 深度链接，Motrix 2.x 官方协议格式）
# ---------------------------------------------------------------------------
def _motrix_protocol_available():
    """检测系统是否已注册 motrix:// 协议（安装 Motrix 后自动注册）。"""
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "motrix"):
            return True
    except OSError:
        return False


def _build_motrix_deeplink(urls):
    """把一条或多条下载链接组装为 motrix:// 深度链接。

    Motrix 2.x 协议格式：motrix://new-task?uri=<URL编码后的链接>
    （uri 须以 http/https/ftp/magnet 开头）；多条链接以换行合并可
    在 Motrix「新建任务」窗口一次性批量预填（每行一条）。
    返回深度链接字符串；urls 全为空时返回 None。
    """
    from urllib.parse import quote
    lines = [u.strip() for u in urls if u and u.strip()]
    if not lines:
        return None
    return "motrix://new-task?uri=" + quote("\n".join(lines), safe="")


def _fmt_size(n):
    """字节数 → 人类可读大小（B/KB/MB/GB）。"""
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
    return "0 B"


def _fmt_speed(speed):
    """字节数/秒 → 人类可读速度。"""
    speed = float(speed or 0)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if speed < 1024 or unit == "GB/s":
            return ("%d %s" % (speed, unit)) if unit == "B/s" else ("%.1f %s" % (speed, unit))
        speed /= 1024.0
    return "0 B/s"


def _motrix_rpc_endpoint():
    """读取 Motrix 本地设置，返回 (rpc端口, rpc令牌)；读取失败返回 None。

    Motrix 2.x 把引擎 RPC 端口与令牌持久化在 %APPDATA%/Motrix/settings.json，
    与其 aria2 引擎实际启动参数一致，可用于本地 JSON-RPC 无头直控。"""
    path = os.path.join(os.environ.get("APPDATA", ""), "Motrix", "settings.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
        engine = cfg.get("engine") or {}
        port = int(engine.get("rpcPort") or 16800)
        secret = str(engine.get("rpcSecret") or "")
        return port, secret
    except Exception:
        return None


def _motrix_exe_path():
    """从系统注册的 motrix:// 协议命令行解析 Motrix.exe 安装路径。"""
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"motrix\shell\open\command") as k:
            cmd = (winreg.QueryValueEx(k, "")[0] or "").strip()
        if cmd.startswith('"'):
            return cmd.split('"', 2)[1]
        return cmd.split(" ", 1)[0]
    except Exception:
        return None


def _aria2_rpc(port, secret, method, params=None, timeout=6):
    """调用 Motrix 内置 aria2 的 JSON-RPC。成功返回 result，失败抛异常。

    端点 http://127.0.0.1:<port>/jsonrpc；令牌以 "token:<secret>" 作为
    第一个参数（secret 为空时不带令牌）。注意 Motrix 定制版 aria2 对
    JSON-RPC 业务错误（如 GID 不存在）返回 HTTP 400，错误详情在响应体。"""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": "zb-extract-tool",
        "method": method,
        "params": (["token:" + secret] if secret else []) + list(params or []),
    }).encode("utf-8")
    req = Request("http://127.0.0.1:%d/jsonrpc" % port, data=payload,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = None
        message = (data or {}).get("error", {}).get("message") if data else None
        raise RuntimeError(message or f"Motrix RPC HTTP {e.code}")
    data = json.loads(body)
    if data.get("error"):
        raise RuntimeError(str((data["error"] or {}).get("message") or "RPC 错误"))
    return data.get("result")


def _motrix_ensure_engine(port, secret, wait_seconds=30, log=None):
    """确保 Motrix aria2 引擎可用：已在运行直接返回 True；否则拉起
    Motrix 并轮询 RPC 就绪（默认最长等待 30 秒）。"""
    import time

    def probe():
        try:
            _aria2_rpc(port, secret, "aria2.getVersion", timeout=2)
            return True
        except Exception:
            return False

    if probe():
        return True
    exe = _motrix_exe_path()
    if not exe or not os.path.exists(exe):
        if log:
            log("✗ 未找到 Motrix 安装路径（motrix:// 协议未注册），无法自动启动")
        return False
    try:
        import subprocess
        subprocess.Popen([exe], cwd=os.path.dirname(exe),
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        if log:
            log("🚀 Motrix 未运行，已自动启动，等待下载引擎就绪…")
    except Exception as e:
        if log:
            log(f"✗ 自动启动 Motrix 失败: {e}")
        return False
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(0.8)
        if probe():
            return True
    if log:
        log("✗ 等待 Motrix 下载引擎超时（可在 Motrix 设置中检查 RPC 端口）")
    return False


def _motrix_add_download(url, save_dir, filename, log=None, resume=True, referer=None):
    """无头添加下载任务到 Motrix（不弹窗、自动开始）。成功返回 aria2 gid。

    本地 RPC addUri：dir=附件归属项目输出目录，out=清洗后的文件名；
    allow-overwrite 保证可覆盖旧文件；resume=True（首次提交）尝试续传
    旧的部分文件，resume=False（「重新下载」）强制全新下载——对不支持
    Range 续传的服务器也能成功；referer 用于平台防盗链校验。"""
    endpoint = _motrix_rpc_endpoint()
    if not endpoint:
        raise RuntimeError("未找到 Motrix 配置（请先启动一次 Motrix）")
    port, secret = endpoint
    if not _motrix_ensure_engine(port, secret, log=log):
        raise RuntimeError("Motrix 下载引擎未就绪（已尝试自动启动 Motrix）")
    opts = {"dir": save_dir, "out": filename,
            "user-agent": DEFAULT_UA,
            "allow-overwrite": "true",
            "continue": "true" if resume else "false"}
    if referer:
        opts["referer"] = referer
    return str(_aria2_rpc(port, secret, "aria2.addUri", [[url], opts]))


def _motrix_task_status(port, secret, gid):
    """查询 aria2 任务状态，返回简化 dict（原始状态、进度字节、速度、错误）。"""
    st = _aria2_rpc(port, secret, "aria2.tellStatus",
                    [gid, ["status", "completedLength", "totalLength",
                           "downloadSpeed", "errorMessage"]])
    return {
        "raw": st.get("status") or "",
        "done": int(st.get("completedLength") or 0),
        "total": int(st.get("totalLength") or 0),
        "speed": int(st.get("downloadSpeed") or 0),
        "error": (st.get("errorMessage") or "").strip(),
    }


# ---------------------------------------------------------------------------
# 附件链接解析层：把"查看器页面"还原为真实文件直链
# ---------------------------------------------------------------------------
def _looks_like_html(head_bytes, content_type):
    """按 Content-Type 与响应体头部判断是否为 HTML 页面（容忍 UTF-8 BOM）。"""
    ct = (content_type or "").lower()
    if "text/html" in ct or "application/xhtml" in ct:
        return True
    head = (head_bytes or b"")[:256].lstrip()
    if head.startswith(b"\xef\xbb\xbf"):
        head = head[3:]
    lower = head[:15].lower()
    return lower.startswith(b"<!doctype html") or lower.startswith(b"<html")


def _epoint_action_url(url):
    """epoint/新点 框架查看页 URL → 同名 Action.action 接口（保留查询串）。

    例：.../pages/signature/TuZhiDocShow?AttachGuid=..&ClientGuid=..
      → .../pages/signature/TuZhiDocShowAction.action?AttachGuid=..&ClientGuid=..
    非 epoint 页面风格（无路径/已是 .action）返回 None。"""
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    path = parts.path or ""
    if not path or path.endswith(".action") or "." in path.rstrip("/").rsplit("/", 1)[-1]:
        return None
    return urlunsplit((parts.scheme, parts.netloc, path + "Action.action", parts.query, ""))


def _parse_epoint_server_file_path(json_text):
    """从 epoint Action 响应 JSON 提取 (custom.serverFilePath, custom.msg)。"""
    try:
        data = json.loads(json_text)
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None
    custom = data.get("custom") or {}
    if not isinstance(custom, dict):
        return None, None
    return custom.get("serverFilePath"), custom.get("msg")


def _sniff_html_file(path):
    """嗅探本地文件：内容是 HTML 页面（而非二进制附件）时返回 True。"""
    try:
        with open(path, "rb") as f:
            head = f.read(512).lstrip()
        if head.startswith(b"\xef\xbb\xbf"):
            head = head[3:]
        lower = head[:15].lower()
        return lower.startswith(b"<!doctype html") or lower.startswith(b"<html")
    except Exception:
        return False


def _resolve_attachment_url(url, log=None):
    """把附件 URL 解析为可直连下载的文件地址。

    流程：GET 探测响应类型；若为 HTML（epoint/新点 TuZhiDocShow 等查看页），
    请求同名 Action.action 接口，从 JSON 的 custom.serverFilePath 取真实
    文件直链（实测该链路无需登录态）；Action 返回 msg（如链接过期）时抛
    ValueError 带原因；已是文件直链则原样返回。"""
    if not url or not url.lower().startswith(("http://", "https://")):
        return url
    from urllib.request import Request, urlopen
    try:
        req = Request(url.replace("&amp;", "&"),
                      headers={"User-Agent": DEFAULT_UA, "Accept": "*/*"})
        with urlopen(req, timeout=15) as resp:
            head = resp.read(2048)
            ctype = resp.headers.get("Content-Type")
    except Exception as e:
        if log:
            log(f"⚠ 链接预检失败（仍按原链接提交 Motrix）: {e}")
        return url
    if not _looks_like_html(head, ctype):
        return url

    action = _epoint_action_url(url)
    if not action:
        raise ValueError("链接返回的是网页而非文件（暂不支持自动解析），请用「浏览器」打开")
    try:
        req = Request(action.replace("&amp;", "&"),
                      headers={"User-Agent": DEFAULT_UA,
                               "X-Requested-With": "XMLHttpRequest",
                               "Accept": "application/json, text/javascript, */*",
                               "Referer": url})
        with urlopen(req, timeout=15) as resp:
            body = resp.read(65536).decode("utf-8", "replace")
    except Exception as e:
        raise ValueError(f"查看页接口请求失败: {e}")
    server_file, msg = _parse_epoint_server_file_path(body)
    if server_file and str(server_file).lower().startswith(("http://", "https://")):
        if log:
            log("🔧 已从查看页解析出真实文件直链")
        return server_file
    if msg:
        raise ValueError("平台返回: " + str(msg))
    raise ValueError("查看页解析失败（未获取到文件地址），请用「浏览器」打开")


# ============================================================================
# 核心解压逻辑（与 GUI 解耦，可独立测试 / 命令行调用）
# ============================================================================
class CancelledError(Exception):
    """用户取消解压时抛出（由 run_batch 捕获，不计入失败）。"""


def _stream_b64_to_file(buf, start, end, out, chunk=1 << 20):
    """把 buf[start:end] 的 Base64 文本分块流式解码写入 out。
    自动跳过空白字符；按 4 字符组对齐分块，末尾残缺组容错处理。"""
    ws = b" \t\r\n\v\f"
    carry = b""
    pos = start
    while pos < end:
        block = bytes(buf[pos:min(pos + chunk, end)])
        pos += len(block)
        block = block.translate(None, ws)
        if not block:
            continue
        data = carry + block
        n4 = len(data) // 4 * 4
        if n4 == 0:
            carry = data
            continue
        out.write(binascii.a2b_base64(data[:n4]))
        carry = data[n4:]
    if carry:
        try:
            out.write(binascii.a2b_base64(carry))
        except Exception as e:
            raise ValueError(f"Base64 数据尾部损坏: {e}")


def extract_file(filepath, overwrite=True, log=None, registry=None, learned=None,
                 max_total_size=None, output_dir=None, cancel_event=None,
                 make_checksum=True):
    """
    解压单个招标文件，返回结果字典：
      {dir, files, learned_ext, warnings, skipped_size, hashes, checksum_file}
    - filepath    : *zf / *cf 文件路径
    - overwrite   : 目标文件已存在时是否覆盖（ZIP 内部同名冲突始终自动改名）
    - log         : 可选回调 log(str)，用于输出进度/告警
    - registry    : 格式注册表（可变 dict，用于学习新格式）；None 则自动加载
    - learned     : 已学习格式集合（可变 dict）；None 则自动加载
    - max_total_size: 解压总量上限（字节）
    - output_dir  : 输出根目录；None 则输出到源文件所在目录（子目录名为文件主名）
    - cancel_event: threading.Event，置位后中止解压（抛 CancelledError）
    - make_checksum: 解压后生成 _SHA256SUMS.txt 校验清单（SHA-256 + 原始 CRC32）
    返回 dict 附加 "attachments"：容器内 XML/JSON 中识别的可下载附件链接列表
    [{category, name, url}]（跳过写盘的内部元数据文件也会参与识别）。
    大文件内存友好：mmap 定位标签，Base64 分块流式解码到临时文件，
    峰值内存仅数 MB，与输入文件大小基本无关。
    单个 ZIP 条目损坏（读取/写入异常、CRC 校验不符）只跳过该条目并告警，
    不中断整包——CRC 对不上即数据已损坏（典型场景：加密密钥/算法错误），
    此时该条目被拦截并清理，防止错误的密文/解密产物混入结果目录。
    """
    log = log or (lambda _m: None)
    if registry is None or learned is None:
        registry, learned = _load_registry()
    if max_total_size is None:
        max_total_size = MAX_TOTAL_SIZE

    name = os.path.basename(filepath)
    folder = os.path.dirname(filepath)

    ext = os.path.splitext(filepath)[1].lower().lstrip(".")
    ext_suffix = ext[-2:] if len(ext) >= 2 else ext

    # ---- 定位内容标签（字节级，避免整文件转 str 的双倍内存）----
    # 候选顺序：注册表映射 → ZBFileContent → DYFileContent → 泛化任意 <XXXFileContent>
    candidates = []
    pref = registry.get(ext) or registry.get(ext_suffix)
    for t in (pref, "ZBFileContent", "DYFileContent"):
        if t and t not in candidates:
            candidates.append(t)

    f = open(filepath, "rb")
    try:
        try:
            buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        except (ValueError, OSError):
            buf = f.read()  # 空文件等无法 mmap 的场景回退为整体读入
        try:
            head = bytes(buf[:64]).lstrip(b"\xef\xbb\xbf \t\r\n")
            if head[:5] != b"<?xml":
                raise ValueError("不是有效的 XML 格式招标文件")

            tag = None
            span = None
            for t in candidates:
                tb = re.escape(t.encode("ascii"))
                m = re.search(rb"<" + tb + rb"[^>]*>(.*?)</" + tb + rb"\s*>", buf, re.DOTALL)
                if m:
                    tag, span = t, m.span(1)
                    break
            if span is None:
                gm = re.search(rb"<([A-Za-z0-9_]{1,64}FileContent)[^>]*>(.*?)</\1\s*>",
                               buf, re.DOTALL)
                if gm:
                    tag, span = gm.group(1).decode("ascii"), gm.span(2)
            if span is None:
                raise ValueError("未找到招标文件内容"
                                 "（已尝试 ZBFileContent / DYFileContent 及泛化 *FileContent 匹配）")

            # Base64 分块流式解码到临时文件（自动删除），不再整段驻留内存
            spool = tempfile.TemporaryFile()
            try:
                try:
                    _stream_b64_to_file(buf, span[0], span[1], spool)
                except ValueError:
                    raise
                except Exception as e:
                    raise ValueError(f"Base64 解码失败: {e}")
                spool.seek(0)
                if spool.read(2) != b"PK":
                    raise ValueError("解码内容不是有效的 ZIP 格式")
                spool.seek(0)

                stem = os.path.splitext(name)[0]
                root_dir = output_dir or folder
                extract_dir = os.path.join(root_dir, stem)
                if not os.path.exists(extract_dir):
                    os.makedirs(extract_dir)

                rules, exclude = _load_decrypt_config()

                extracted = []
                warnings = 0
                skipped_size = 0
                total_size = 0
                used_names = set()
                entry_meta = []  # [{name, sha256, crc}] 校验记录
                attachment_raw = []  # 容器内文本条目中的可下载链接

                with zipfile.ZipFile(spool) as zf:
                    for zi in zf.infolist():
                        if zi.is_dir():
                            continue
                        if cancel_event is not None and cancel_event.is_set():
                            raise CancelledError("用户取消")
                        decoded_name = _decode_zip_name(zi)
                        base = os.path.basename(decoded_name)
                        if not base:
                            continue
                        # 内部文件（如 PBZB.xml）：不写盘，但仍读取文本解析附件链接
                        if base in exclude:
                            log(f"  ⊘ 跳过内部文件: {base}")
                            ext_name = os.path.splitext(base)[1].lower()
                            if ext_name in ATTACH_TEXT_EXTS:
                                try:
                                    attachment_raw.extend(
                                        _extract_attachments(zf.read(zi).decode("utf-8", "replace")))
                                except CancelledError:
                                    raise
                                except Exception:
                                    pass
                            continue

                        total_size += zi.file_size
                        if total_size > max_total_size:
                            skipped_size += zi.file_size
                            log(f"  ✗ {base}: 解压总量将超过 {max_total_size // (1024**2)}MB 上限，已跳过")
                            warnings += 1
                            continue

                        target = _resolve_target(extract_dir, base, used_names, overwrite, log)
                        if target is None:
                            log(f"  ⊘ {base}: 已存在，跳过（未勾选覆盖）")
                            warnings += 1
                            continue

                        try:
                            # 仅命中解密规则的文件需要整体读入内存；其余流式拷贝。
                            # 全程累计 SHA-256 与 CRC32：CRC 与 zip 条目记录不符即判数据损坏
                            # （加密容器若密钥/算法不对，修改后的明文 CRC 必然对不上）。
                            src_ext = os.path.splitext(base)[1].lower()
                            rule = rules.get(src_ext)
                            need_decrypt = bool(rule and rule.get("enabled") and rule.get("key"))

                            if need_decrypt:
                                data = zf.read(zi)
                                out_data, decrypted, warn = _decrypt_if_needed(base, data, rules)
                                if warn:
                                    log(f"  ⚠ {base}: {warn}")
                                    warnings += 1
                                if decrypted:
                                    log(f"  🔓 {base}: AES 解密成功")
                                crc = zlib.crc32(out_data)
                                if crc != (zi.CRC & 0xFFFFFFFF):
                                    raise ValueError(
                                        f"CRC 校验失败（zip 记录 {zi.CRC:08X}，实际 {crc:08X}）："
                                        "解密产物与源文件不符，可能密钥/算法不正确")
                                sha_hex = hashlib.sha256(out_data).hexdigest()
                                with open(target, "wb") as out:
                                    out.write(out_data)
                            else:
                                hasher = hashlib.sha256()
                                crc = 0
                                with zf.open(zi) as src, open(target, "wb") as out:
                                    while True:
                                        if cancel_event is not None and cancel_event.is_set():
                                            raise CancelledError("用户取消")
                                        chunk = src.read(1 << 20)
                                        if not chunk:
                                            break
                                        out.write(chunk)
                                        crc = zlib.crc32(chunk, crc)
                                        hasher.update(chunk)
                                if crc != (zi.CRC & 0xFFFFFFFF):
                                    raise ValueError(
                                        f"CRC 校验失败（zip 记录 {zi.CRC:08X}，实际 {crc:08X}）："
                                        "解压数据已损坏")
                                sha_hex = hasher.hexdigest()
                        except CancelledError:
                            raise
                        except Exception as e:
                            log(f"  ✗ {base}: {e}（已跳过该条目）")
                            warnings += 1
                            try:
                                if os.path.exists(target):
                                    os.remove(target)
                            except Exception:
                                pass
                            continue

                        entry_meta.append({"name": base, "sha256": sha_hex,
                                           "crc": f"{crc & 0xFFFFFFFF:08X}"})
                        extracted.append(os.path.basename(target))
                        # 交付文件本身若含下载链接（如 xxx 附件指引），也参与识别
                        if os.path.splitext(base)[1].lower() in ATTACH_TEXT_EXTS:
                            try:
                                with open(target, "r", encoding="utf-8", errors="replace") as tf:
                                    attachment_raw.extend(_extract_attachments(tf.read()))
                            except Exception:
                                pass
            finally:
                spool.close()
        finally:
            if isinstance(buf, mmap.mmap):
                buf.close()
    finally:
        f.close()

    # ---- 生成 SHA-256 校验清单（hash  + 空格两格  + 文件名，sha256sum 兼容格式）----
    checksum_file = None
    if make_checksum and entry_meta:
        try:
            checksum_file = os.path.join(extract_dir, "_SHA256SUMS.txt")
            with open(checksum_file, "w", encoding="utf-8", newline="\n") as sf:
                for m in entry_meta:
                    sf.write(f"{m['sha256']}  {m['name']}\n")
            log(f"  🧮 已生成校验清单: _SHA256SUMS.txt（{len(entry_meta)} 个文件，SHA-256 + CRC32）")
        except Exception as e:
            log(f"  ⊘ 校验清单写入失败: {e}")
            checksum_file = None

    learned_ext = None
    if ext not in BUILTIN_EXTENSIONS and ext not in learned:
        _save_learned_format(ext, tag)
        learned[ext] = tag
        registry[ext] = tag
        learned_ext = ext
        log(f"★ 已学习新格式 .{ext}，下次将自动识别")

    attachments = _dedup_attachments(attachment_raw)
    if attachments:
        log(f"  📎 识别到 {len(attachments)} 个可下载附件"
            + (f"：{', '.join(a['name'] for a in attachments[:5])}" + ("…" if len(attachments) > 5 else "")))

    return {
        "dir": extract_dir,
        "files": extracted,
        "learned_ext": learned_ext,
        "warnings": warnings,
        "skipped_size": skipped_size,
        "hashes": {m["name"]: m["sha256"] for m in entry_meta},
        "checksum_file": checksum_file,
        "attachments": attachments,
    }


def run_batch(files, overwrite=True, log=None, progress=None,
              registry=None, learned=None, output_dir=None, cancel_event=None,
              make_checksum=True):
    """批量解压入口：GUI 后台线程与 --auto 模式共用。
    - progress(idx, total, name) 可选回调
    - cancel_event 置位后：当前文件停手、后续文件不再处理（不计入失败）
    - make_checksum 解压后生成 SHA-256 校验清单
    - 返回 {success, failed, cancelled, learned, last_dir}
    """
    log = log or (lambda _m: None)
    progress = progress or (lambda i, t, n: None)
    success = 0
    failed = 0
    cancelled = 0
    learned_list = []
    attachments = []
    last_dir = None
    total = len(files)
    for idx, fp in enumerate(files):
        if cancel_event is not None and cancel_event.is_set():
            cancelled += len(files) - idx  # 剩余文件全部计入取消
            log(f"⏹ 已取消：剩余 {len(files) - idx} 个文件不再处理")
            break
        name = os.path.basename(fp)
        progress(idx, total, name)
        try:
            r = extract_file(fp, overwrite=overwrite, log=log,
                             registry=registry, learned=learned,
                             output_dir=output_dir, cancel_event=cancel_event,
                             make_checksum=make_checksum)
            log(f"✓ {name} → {r['dir']} ({len(r['files'])} 个文件)"
                + ("，已附带 SHA-256 校验清单" if r.get("checksum_file") else ""))
            if r["warnings"]:
                log(f"  ⚠ 本次 {r['warnings']} 条告警（详见上方日志）")
            if r["learned_ext"]:
                learned_list.append(r["learned_ext"])
            if r.get("attachments"):
                stem = os.path.splitext(name)[0]
                for a in r["attachments"]:
                    aa = dict(a)
                    aa["project"] = a.get("project") or stem  # 归属项目=源文件名主体
                    aa["out_dir"] = a.get("out_dir") or r["dir"]
                    attachments.append(aa)
            last_dir = r["dir"]
            success += 1
        except CancelledError:
            log(f"⏹ {name} 已取消")
            cancelled += 1
            break
        except Exception as e:
            log(f"✗ {name} 解压失败: {e}")
            _log(f"解压失败: {fp}", exc=e)
            failed += 1
    progress(total, total, "")
    return {"success": success, "failed": failed, "cancelled": cancelled,
            "learned": learned_list, "last_dir": last_dir,
            "attachments": attachments}


# ============================================================================
# GUI
# ============================================================================
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    _log("tkinter not available")
    raise

# 可选依赖：窗口拖放支持（缺失时自动退化为普通 Tk，不影响其他功能）
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except Exception:
    TkinterDnD = None
    DND_FILES = None

# ---- 视觉规范（浅色现代风）----
FONT = "微软雅黑"
BG = "#F3F4F6"        # 页面背景（浅灰）
CARD = "#FFFFFF"      # 卡片背景
BORDER = "#E5E7EB"    # 边框/分隔线
FG = "#111827"        # 主文字
MUTED = "#6B7280"     # 次要文字
ACCENT = "#2563EB"    # 主色（蓝）
ACCENT_DARK = "#1E40AF"
SELECT_BG = "#DBEAFE" # 列表选中底色
SUCCESS = "#15803D"
DANGER = "#DC2626"
WARN = "#B45309"


def _enable_high_dpi():
    """启用 Per-Monitor DPI 感知，高分屏文字不再发虚。"""
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _apply_dpi_scaling(root):
    try:
        import ctypes
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi:
            root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass


def _setup_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")  # clam 允许完全自定义配色，观感扁平现代
    except Exception:
        pass
    style.configure(".", background=BG, foreground=FG, borderwidth=0, font=(FONT, 9))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Card.TLabel", background=CARD, foreground=FG)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
    style.configure("H1.TLabel", background=CARD, foreground=FG, font=(FONT, 13, "bold"))
    style.configure("Sub.TLabel", background=CARD, foreground=MUTED, font=(FONT, 8))
    style.configure("Section.TLabel", background=BG, foreground=FG, font=(FONT, 10, "bold"))
    style.configure("Pct.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
    style.configure("Status.TLabel", background="#ECEDF1", foreground=MUTED)
    # 普通按钮（扁平灰）
    style.configure("TButton", background=CARD, foreground="#374151",
                    padding=(12, 6), borderwidth=0, font=(FONT, 9))
    style.map("TButton",
              background=[("pressed", "#E5E7EB"), ("active", "#EFF1F4")],
              foreground=[("disabled", "#9CA3AF")])
    # 主按钮（蓝色大按钮）
    style.configure("Primary.TButton", background=ACCENT, foreground="white",
                    padding=(22, 9), borderwidth=0, font=(FONT, 11, "bold"))
    style.map("Primary.TButton",
              background=[("disabled", "#93B4F5"), ("pressed", ACCENT_DARK), ("active", ACCENT_DARK)],
              foreground=[("disabled", "#F3F6FE")])
    # 复选框（页面背景上）
    style.configure("TCheckbutton", background=BG, foreground=FG,
                    focuscolor=BG, font=(FONT, 9))
    style.map("TCheckbutton", background=[("active", BG)])
    # 复选框（卡片内）
    style.configure("Card.TCheckbutton", background=CARD, foreground=FG,
                    focuscolor=CARD, font=(FONT, 9))
    style.map("Card.TCheckbutton", background=[("active", CARD)])
    # 进度条
    style.configure("Accent.Horizontal.TProgressbar", troughcolor=BORDER,
                    background=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT,
                    borderwidth=0, thickness=10)
    # 分隔线
    style.configure("TSeparator", background=BORDER)


def _set_app_icon(root):
    """窗口/任务栏图标。iconphoto(True) 同时作用于后续顶层窗口。
    PhotoImage 对 PNG 支持最稳，优先用 PNG；.ico 仅作后备。"""
    try:
        for name in ("icon_preview.png", "招标文件快速解压工具.ico"):
            icon = os.path.join(APP_DIR, name)
            if os.path.exists(icon):
                root._appicon = tk.PhotoImage(file=icon)  # 持有引用防回收
                root.iconphoto(True, root._appicon)
                break
    except Exception:
        pass


def make_root():
    _enable_high_dpi()
    root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
    _apply_dpi_scaling(root)
    _setup_style(root)
    _set_app_icon(root)
    return root


# ---- 共享日志写入（带时间戳与级别着色）----
def _log_tag(msg):
    if "✗" in msg:
        return "error"
    if msg.lstrip().startswith(("✓", "★")):
        return "ok"
    if any(s in msg for s in ("⚠", "⊘", "↻")):
        return "warn"
    return None


def config_log_tags(widget):
    widget.tag_configure("time", foreground=MUTED)
    widget.tag_configure("ok", foreground=SUCCESS)
    widget.tag_configure("error", foreground=DANGER)
    widget.tag_configure("warn", foreground=WARN)


def write_log(widget, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    widget.insert(tk.END, f"[{ts}] ", "time")
    tag = _log_tag(msg)
    widget.insert(tk.END, msg + "\n", tag) if tag else widget.insert(tk.END, msg + "\n")
    widget.see(tk.END)


def _load_ui_config():
    cfg = {}
    try:
        if os.path.exists(UI_CONFIG):
            with open(UI_CONFIG, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
    except Exception:
        pass
    return cfg


def _save_ui_config(cfg):
    try:
        with open(UI_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class ExtractTool:
    def __init__(self):
        self.root = make_root()
        self.root.title(f"招标文件快速解压工具 {APP_VERSION}")
        self.root.geometry("920x640")
        self.root.minsize(760, 520)
        self.root.configure(background=BG)
        self.files = []
        self.is_running = False
        self.last_output_dir = None
        self.q = None
        self.cancel_event = threading.Event()
        self.attachments = []
        self.attach_rows = {}         # 附件索引 → 行控件与下载状态
        self.attach_q = queue.Queue() # 后台线程 → UI 的附件状态/日志消息
        self.registry, self.learned = _load_registry()

        cfg = _load_ui_config()
        self.overwrite_var = tk.BooleanVar(value=bool(cfg.get("overwrite", True)))
        self.open_dir_var = tk.BooleanVar(value=bool(cfg.get("open_dir", False)))
        self.checksum_var = tk.BooleanVar(value=bool(cfg.get("checksum", True)))
        for var in (self.overwrite_var, self.open_dir_var, self.checksum_var):
            var.trace_add("write", lambda *_: self._persist_cfg())
        self.status_text = tk.StringVar(value="就绪")

        self._build_ui()
        self._register_dnd()
        self._handle_argv()
        self._refresh_list_ui()
        self.root.after(150, self._poll_attach_queue)
        threading.Thread(target=self._attach_poller_loop, daemon=True).start()
        self.root.bind_all("<MouseWheel>", self._attach_mousewheel)

    def _build_ui(self):
        # ---- 状态栏（沉底）----
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(side=tk.BOTTOM, fill=tk.X)
        statusbar = tk.Frame(self.root, background="#ECEDF1", height=30)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        statusbar.pack_propagate(False)
        ttk.Label(statusbar, textvariable=self.status_text,
                  style="Status.TLabel").pack(side=tk.LEFT, padx=12)
        ttk.Label(statusbar, text=APP_VERSION,
                  style="Status.TLabel").pack(side=tk.RIGHT, padx=12)

        # ---- 顶栏（卡片色 + 下边线）----
        header = tk.Frame(self.root, background=CARD,
                          highlightthickness=1, highlightbackground=BORDER)
        header.pack(fill=tk.X)
        ttk.Label(header, text="招标文件快速解压工具",
                  style="H1.TLabel").pack(side=tk.LEFT, padx=(16, 10), pady=12)
        ttk.Label(header, text=f"{APP_VERSION} | 支持任意 *zf / *cf | 标签自动识别 | 后台解压不卡界面",
                  style="Sub.TLabel").pack(side=tk.LEFT, pady=(4, 0))

        # ---- 主内容区 ----
        main = ttk.Frame(self.root, padding=(14, 12))
        main.pack(fill=tk.BOTH, expand=True)

        # 左右分栏：左列（待解压文件+操作+日志），右栏（可下载附件）
        body = ttk.Frame(main)
        body.pack(fill=tk.BOTH, expand=True)
        left_col = ttk.Frame(body)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.body = body

        # 文件区标题 + 计数徽标
        head_row = ttk.Frame(left_col)
        head_row.pack(fill=tk.X)
        dnd_hint = "，可直接把文件拖进窗口" if TkinterDnD is not None else ""
        self.count_label = ttk.Label(head_row, text="待解压文件（0）", style="Section.TLabel")
        self.count_label.pack(side=tk.LEFT)
        ttk.Label(head_row, text=f"双击条目打开所在文件夹{dnd_hint}",
                  style="Muted.TLabel").pack(side=tk.LEFT, padx=10)

        # 文件列表卡片
        list_card = tk.Frame(left_col, background=CARD, highlightthickness=1,
                             highlightbackground=BORDER, highlightcolor=ACCENT)
        list_card.pack(fill=tk.BOTH, expand=True, pady=(6, 10))
        list_content = tk.Frame(list_card, background=CARD)
        list_content.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.file_listbox = tk.Listbox(list_content, font=(FONT, 9),
                                       selectmode=tk.EXTENDED, activestyle="none",
                                       bg=CARD, fg=FG, relief="flat",
                                       highlightthickness=0,
                                       selectbackground=SELECT_BG, selectforeground=FG)
        vscroll = ttk.Scrollbar(list_content, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=vscroll.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.bind("<Double-Button-1>", self._open_selected_folder)

        # 空列表提示（覆盖在列表中央）
        self.hint_label = tk.Label(
            list_content, text="把 *zf / *cf 文件拖到这里\n或点击下方「选择文件」",
            bg=CARD, fg=MUTED, font=(FONT, 10), justify="center")
        self.hint_label.place(relx=0.5, rely=0.42, anchor="center")

        # ---- 操作按钮行 1：文件管理 ----
        ops = ttk.Frame(left_col)
        ops.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(ops, text="选择文件", command=self._add_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ops, text="选择文件夹", command=self._add_folder).pack(side=tk.LEFT, padx=6)
        ttk.Button(ops, text="移除选中", command=self._remove_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(ops, text="清空列表", command=self._clear_list).pack(side=tk.LEFT, padx=6)

        # ---- 操作按钮行 2：主按钮 + 选项 ----
        act = ttk.Frame(left_col)
        act.pack(fill=tk.X, pady=(0, 12))
        self.btn_extract = ttk.Button(act, text="开始解压",
                                      style="Primary.TButton", command=self._start_extract)
        self.btn_extract.pack(side=tk.LEFT)
        self.btn_cancel = ttk.Button(act, text="取消解压",
                                     command=self._cancel_extract, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(act, text="SHA-256 校验清单",
                        variable=self.checksum_var).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Checkbutton(act, text="覆盖已存在文件",
                        variable=self.overwrite_var).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Checkbutton(act, text="完成后打开输出目录",
                        variable=self.open_dir_var).pack(side=tk.RIGHT, padx=6)

        # ---- 右栏：可下载附件（逐行卡片：文件名+进度条+操作按钮）----
        self.attach_card = tk.Frame(body, background=CARD, width=400,
                                    highlightthickness=1, highlightbackground=BORDER,
                                    highlightcolor=ACCENT)
        self.attach_card.pack_propagate(False)
        attach_row = ttk.Frame(self.attach_card)
        attach_row.pack(fill=tk.X, padx=8, pady=(8, 2))
        ttk.Label(attach_row, text="可下载附件", style="Section.TLabel").pack(side=tk.LEFT)
        self.attach_count = ttk.Label(attach_row, text="（0）", style="Muted.TLabel")
        self.attach_count.pack(side=tk.LEFT, padx=4)
        ttk.Button(attach_row, text="全部下载",
                   command=self._download_all_in_motrix).pack(side=tk.RIGHT, padx=2)
        attach_container = tk.Frame(self.attach_card, background=CARD)
        attach_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))
        self.attach_canvas = tk.Canvas(attach_container, bg=CARD, highlightthickness=0)
        attach_scroll = ttk.Scrollbar(attach_container, orient=tk.VERTICAL,
                                      command=self.attach_canvas.yview)
        self.attach_inner = tk.Frame(self.attach_canvas, background=CARD)
        self.attach_canvas.create_window((0, 0), window=self.attach_inner,
                                         anchor="nw", tags="inner")
        self.attach_inner.bind(
            "<Configure>",
            lambda _e: self.attach_canvas.configure(
                scrollregion=self.attach_canvas.bbox("all")))
        self.attach_canvas.bind(
            "<Configure>",
            lambda e: self.attach_canvas.itemconfigure("inner", width=e.width))
        self.attach_canvas.configure(yscrollcommand=attach_scroll.set)
        self.attach_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        attach_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        attach_hint = tk.Label(self.attach_card, text="解压后识别到的图纸/清单\n控制价等下载链接将出现在此栏",
                               bg=CARD, fg=MUTED, font=(FONT, 9), justify="center")
        attach_hint.pack(padx=8, pady=(0, 8))
        self.attach_hint = attach_hint
        self.attach_card.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        self.attach_card.pack_forget()

        # ---- 进度行 ----
        prog_row = ttk.Frame(left_col)
        prog_row.pack(fill=tk.X, pady=(0, 10))
        self.prog_row = prog_row
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(prog_row, variable=self.progress_var,
                                        style="Accent.Horizontal.TProgressbar",
                                        mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pct_text = tk.StringVar(value="0%")
        ttk.Label(prog_row, textvariable=self.pct_text, style="Pct.TLabel",
                  width=6).pack(side=tk.LEFT, anchor="e", padx=(8, 2))

        # ---- 日志区 ----
        log_head = ttk.Frame(left_col)
        log_head.pack(fill=tk.X)
        ttk.Label(log_head, text="解压日志", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Button(log_head, text="清空日志",
                   command=self._clear_log).pack(side=tk.RIGHT)
        log_card = tk.Frame(left_col, background="#FAFBFC", highlightthickness=1,
                            highlightbackground=BORDER, highlightcolor=ACCENT)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.log_text = tk.Text(log_card, height=8, font=(FONT, 9), bg="#FAFBFC",
                                fg=FG, relief="flat", padx=8, pady=6, wrap="none",
                                insertbackground=FG, selectbackground=SELECT_BG,
                                selectforeground=FG)
        log_scroll = ttk.Scrollbar(log_card, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        config_log_tags(self.log_text)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _persist_cfg(self):
        try:
            _save_ui_config({"overwrite": self.overwrite_var.get(),
                             "open_dir": self.open_dir_var.get(),
                             "checksum": self.checksum_var.get()})
        except Exception:
            pass

    def _register_dnd(self):
        if TkinterDnD is None:
            return
        try:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
        except Exception as e:
            _log(f"注册拖放失败: {e}")

    def _on_drop(self, event):
        paths = list(self.root.tk.splitlist(event.data))
        added = 0
        for p in _collect_cli_files(paths):
            if p not in self.files:
                self._add_path(p)
                added += 1
        self.status_text.set(f"已拖入 {added} 个文件")
        return event.action

    def _handle_argv(self):
        """支持命令行/拖放传入文件或文件夹路径，直接加入列表。"""
        files = _collect_cli_files(sys.argv[1:])
        for p in files:
            self._add_path(p)
        if files:
            self.status_text.set(f"已通过命令行添加 {len(files)} 个文件")
        self._refresh_list_ui()

    def _add_path(self, p):
        if p not in self.files:
            self.files.append(p)
            self.file_listbox.insert(tk.END, os.path.basename(p))
        self._refresh_list_ui()

    def _refresh_list_ui(self):
        """刷新计数徽标与空列表提示。"""
        n = len(self.files)
        self.count_label.config(text=f"待解压文件（{n}）")
        if n:
            self.hint_label.place_forget()
        else:
            self.hint_label.place(relx=0.5, rely=0.42, anchor="center")

    def _ui_log(self, msg):
        write_log(self.log_text, msg)

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)

    # ---- 附件下载面板（Motrix 无头下载：逐行进度 + 暂停/停止/重下/浏览器）----
    def _populate_attachments(self):
        for w in self.attach_inner.winfo_children():
            w.destroy()
        self.attach_rows = {}
        projects = []
        for a in self.attachments:    # 保持项目出现顺序
            if a.get("project") not in projects:
                projects.append(a["project"])
        for pj in projects:
            tk.Label(self.attach_inner, text="─ " + pj + " ─", bg=CARD, fg=MUTED,
                     font=(FONT, 8), anchor="w").pack(fill=tk.X, padx=2, pady=(8, 2))
            for idx, a in enumerate(self.attachments):
                if a.get("project") == pj:
                    self._build_attach_row(idx)
        n_proj = len(projects)
        suffix = f" · {n_proj} 项目" if n_proj > 1 else ""
        self.attach_count.config(text=f"（{len(self.attachments)} 个{suffix}）")
        self.attach_hint.pack_forget()
        self.attach_card.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        self._ui_log(f"📎 解压识别出 {len(self.attachments)} 个可下载附件——"
                     "点行内「下载」或「全部下载」即无头提交 Motrix（不弹窗、"
                     "自动开始，文件存入各项目输出目录）；Motrix 未运行会自动启动")

    def _build_attach_row(self, idx):
        a = self.attachments[idx]
        card = tk.Frame(self.attach_inner, background=CARD)
        card.pack(fill=tk.X, padx=4, pady=(0, 4))
        top = tk.Frame(card, background=CARD)
        top.pack(fill=tk.X)
        name = f"[{a['category']}] {a['name']}"
        if len(name) > 34:
            name = name[:33] + "…"
        tk.Label(top, text=name, bg=CARD, fg=FG, font=(FONT, 9),
                 anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
        pct_lbl = tk.Label(top, text="", bg=CARD, fg=MUTED, font=(FONT, 8),
                           anchor="e", width=5)
        pct_lbl.pack(side=tk.RIGHT)
        bar = ttk.Progressbar(card, orient=tk.HORIZONTAL, maximum=100, value=0,
                              style="Accent.Horizontal.TProgressbar")
        bar.pack(fill=tk.X, pady=(2, 1))
        stat_lbl = tk.Label(card, text="未下载", bg=CARD, fg=MUTED,
                            font=(FONT, 8), anchor="w")
        stat_lbl.pack(fill=tk.X)
        btns = tk.Frame(card, background=CARD)
        btns.pack(fill=tk.X, pady=(2, 0))
        self.attach_rows[idx] = {"card": card, "bar": bar, "pct_lbl": pct_lbl,
                                 "status_lbl": stat_lbl, "btns": btns,
                                 "state": "idle", "gid": None, "error": None,
                                 "status_text": "", "pct": 0.0, "speed": 0}
        self._render_attach_row(idx)

    def _render_attach_row(self, idx):
        row = self.attach_rows[idx]
        pct = row.get("pct", 0.0)
        row["bar"].configure(value=pct)
        row["pct_lbl"].configure(text=f"{pct:.0f}%" if pct > 0 else "")
        st = row["state"]
        defaults = {"idle": "未下载", "starting": "连接 Motrix 引擎…",
                    "stopping": "处理中…", "active": "下载中…", "paused": "已暂停",
                    "waiting": "排队中…", "complete": "✔ 已完成",
                    "stopped": "已停止", "error": row.get("error") or "下载失败"}
        text = row.get("status_text") or defaults.get(st, "")
        color = MUTED
        if st == "active":
            color = ACCENT
        elif st == "complete":
            color = SUCCESS
        elif st == "paused":
            color = WARN
        elif st == "error":
            color = DANGER
        if st == "error" and row.get("error"):
            err = row["error"]
            text = "下载失败: " + (err[:60] + "…" if len(err) > 60 else err)
        row["status_lbl"].configure(text=text, fg=color)
        self._render_attach_buttons(idx)

    def _render_attach_buttons(self, idx):
        row = self.attach_rows[idx]
        for w in row["btns"].winfo_children():
            w.destroy()
        st = row["state"]

        def add(text, cmd):
            ttk.Button(row["btns"], text=text, command=cmd).pack(side=tk.LEFT, padx=(0, 4))

        if st == "idle":
            add("下载", lambda i=idx: self._attach_start(i))
        elif st == "starting":
            ttk.Button(row["btns"], text="提交中…", state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 4))
        elif st in ("active", "waiting"):
            add("暂停", lambda i=idx: self._attach_pause(i))
            add("停止", lambda i=idx: self._attach_stop(i))
            add("重新下载", lambda i=idx: self._attach_restart(i))
        elif st == "paused":
            add("继续", lambda i=idx: self._attach_resume(i))
            add("停止", lambda i=idx: self._attach_stop(i))
            add("重新下载", lambda i=idx: self._attach_restart(i))
        elif st == "stopping":
            ttk.Button(row["btns"], text="…", state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 4))
        elif st == "complete":
            add("重新下载", lambda i=idx: self._attach_restart(i))
        elif st in ("error", "stopped"):
            add("重新下载", lambda i=idx: self._attach_start(i))
        add("浏览器", lambda i=idx: self._attach_open_browser(i))

    # ---- 行状态机：UI 线程内更新；后台线程经 attach_q 提交 ----
    def _set_attach_state(self, idx, state, detail=None, text=None):
        row = self.attach_rows.get(idx)
        if not row:
            return
        row["state"] = state
        if state in ("active", "paused", "waiting") and detail:
            row["gid"] = detail
        elif state in ("error", "stopped", "idle"):
            row["gid"] = None
            row["error"] = detail
        if text is not None:
            row["status_text"] = text
        self._render_attach_row(idx)

    def _attach_finalize_complete(self, idx):
        """任务完成收尾：嗅探产物文件头，若为网页（链接过期/平台拦截）判为
        失败并引导「浏览器」打开，避免产生看似成功的坏文件。"""
        row = self.attach_rows.get(idx)
        if not row:
            return
        a = self.attachments[idx]
        ext = os.path.splitext(a["name"])[1].lower()
        target = os.path.join(a.get("out_dir") or ".",
                              _safe_filename(a["name"]) or "attachment.bin")
        if ext not in (".html", ".htm", ".xhtml", ".xml", ".svg") and _sniff_html_file(target):
            row["state"] = "error"
            row["gid"] = None
            row["error"] = "下载内容是网页而非文件（链接可能已过期），请点「浏览器」打开"
            row["status_text"] = ""
        else:
            row["state"] = "complete"
            row["pct"] = 100.0
            row["status_text"] = "✔ 已完成"
        self._render_attach_row(idx)

    def _apply_attach_status(self, idx, st):
        row = self.attach_rows.get(idx)
        if not row:
            return
        raw = st["raw"]
        total, done, speed = st["total"], st["done"], st["speed"]
        row["total"] = total
        row["done"] = done
        row["pct"] = (done / total * 100.0) if total > 0 else 0.0
        row["speed"] = speed
        if raw == "complete":
            self._attach_finalize_complete(idx)
        elif raw == "active":
            row["state"] = "active"
            if total > 0:
                row["status_text"] = f"{_fmt_size(done)} / {_fmt_size(total)} · {_fmt_speed(speed)}"
            else:
                row["status_text"] = f"已下载 {_fmt_size(done)} · {_fmt_speed(speed)}"
        elif raw == "paused":
            row["state"] = "paused"
            row["status_text"] = "已暂停"
        elif raw == "waiting":
            row["state"] = "waiting"
            row["status_text"] = "排队中（已达最大并发）"
        elif raw == "error":
            row["state"] = "error"
            row["gid"] = None
            row["error"] = st["error"] or "服务器拒绝（可能需浏览器登录后下载）"
            row["status_text"] = ""
        elif raw == "removed":
            row["state"] = "stopped"
            row["gid"] = None
            row["status_text"] = ""
        self._render_attach_row(idx)

    # ---- 行操作（UI 线程发起，RPC 在后台线程执行）----
    def _attach_start(self, idx, resume=True):
        row = self.attach_rows.get(idx)
        if not row or row["state"] in ("starting", "active", "paused", "waiting", "stopping"):
            return
        a = self.attachments[idx]
        row["pct"] = 0.0
        row["speed"] = 0
        row["total"] = 0
        row["done"] = 0
        self._set_attach_state(idx, "starting", text="连接 Motrix 引擎…")
        self._ui_log(f"📤 提交 Motrix 下载: [{a.get('project')} | {a['category']}] {a['name']}")

        def work():
            try:
                real_url = _resolve_attachment_url(
                    a["url"], log=lambda m: self.attach_q.put(("log", idx, {"text": m})))
            except Exception as e:
                self.attach_q.put(("state", idx,
                                   {"state": "error", "detail": str(e),
                                    "text": f"解析失败: {e}"}))
                return
            try:
                gid = _motrix_add_download(
                    real_url, a.get("out_dir") or ".",
                    _safe_filename(a["name"]) or "attachment.bin",
                    log=lambda m: self.attach_q.put(("log", idx, {"text": m})),
                    resume=resume, referer=a["url"])
            except Exception as e:
                self.attach_q.put(("state", idx,
                                   {"state": "error", "detail": str(e),
                                    "text": f"提交失败: {e}"}))
                return
            self.attach_q.put(("state", idx,
                               {"state": "active", "detail": gid, "text": ""}))
        threading.Thread(target=work, daemon=True).start()

    def _attach_rpc(self, idx, method, ok_state, ok_text=None):
        row = self.attach_rows.get(idx)
        if not row or not row.get("gid"):
            return
        endpoint = _motrix_rpc_endpoint()
        gid = row["gid"]
        if not endpoint:
            self.attach_q.put(("state", idx,
                               {"state": "error", "detail": "未找到 Motrix 配置",
                                "text": "操作失败: 未找到 Motrix 配置"}))
            return
        port, secret = endpoint

        def work():
            try:
                _aria2_rpc(port, secret, "aria2." + method, [gid], timeout=6)
            except Exception as e:
                # 失败不硬切状态：轮询会按引擎真实状态纠正（任务可能刚完成）
                self.attach_q.put(("log", idx, {"text": f"⚠ Motrix 操作({method})失败: {e}"}))
                return
            self.attach_q.put(("state", idx,
                               {"state": ok_state, "text": ok_text or ""}))
        threading.Thread(target=work, daemon=True).start()

    def _attach_pause(self, idx):
        row = self.attach_rows.get(idx)
        if not row or row["state"] != "active":
            return
        self._set_attach_state(idx, "stopping", text="暂停中…")
        self._attach_rpc(idx, "pause", "paused", "已暂停")

    def _attach_resume(self, idx):
        row = self.attach_rows.get(idx)
        if not row or row["state"] != "paused":
            return
        self._set_attach_state(idx, "stopping", text="继续中…")
        self._attach_rpc(idx, "unpause", "active")

    def _attach_stop(self, idx):
        row = self.attach_rows.get(idx)
        if not row or row["state"] not in ("active", "paused", "waiting"):
            return
        self._set_attach_state(idx, "stopping", text="停止中…")
        self._attach_rpc(idx, "remove", "stopped", "已停止")

    def _attach_restart(self, idx):
        """重新下载：移除旧任务后强制全新下载（continue=false，不依赖
        服务器 Range 续传支持，任何服务器都能成功）。"""
        row = self.attach_rows.get(idx)
        if not row:
            return
        old_gid = row.get("gid")
        endpoint = _motrix_rpc_endpoint()
        if old_gid and endpoint:
            port, secret = endpoint

            def _rm(gid=old_gid):
                try:
                    _aria2_rpc(port, secret, "aria2.remove", [gid], timeout=6)
                except Exception:
                    pass
            threading.Thread(target=_rm, daemon=True).start()
        row["gid"] = None
        row["state"] = "idle"
        self._attach_start(idx, resume=False)

    def _attach_open_browser(self, idx):
        a = self.attachments[idx]
        self._ui_log(f"🌐 调用浏览器打开: [{a.get('project')} | {a['category']}] {a['name']}")
        try:
            os.startfile(a["url"])
        except Exception as e:
            self._ui_log(f"✗ 打开失败: {e}")

    def _download_all_in_motrix(self):
        started = 0
        for idx in list(self.attach_rows.keys()):
            if self.attach_rows[idx]["state"] in ("idle", "error", "stopped", "complete"):
                self._attach_start(idx)
                started += 1
        if not started and self.attach_rows:
            self._ui_log("没有可下载的附件（全部正在下载或处理中）")

    def _attach_mousewheel(self, event):
        w = getattr(self, "attach_canvas", None)
        if w is None or not w.winfo_ismapped():
            return
        mx, my = w.winfo_pointerx(), w.winfo_pointery()
        inside = (w.winfo_rootx() <= mx < w.winfo_rootx() + w.winfo_width()
                  and w.winfo_rooty() <= my < w.winfo_rooty() + w.winfo_height())
        if inside:
            w.yview_scroll(-1 * (event.delta // 120), "units")

    def _attach_poller_loop(self):
        """后台轮询 Motrix 任务状态（1 秒节拍），经 attach_q 交 UI 线程刷新。"""
        import time
        while True:
            try:
                tracked = [(idx, r) for idx, r in list(self.attach_rows.items())
                           if r.get("gid") and r["state"] in
                           ("active", "paused", "waiting", "stopping")]
                if tracked:
                    endpoint = _motrix_rpc_endpoint()
                    if not endpoint:
                        for idx, _r in tracked:
                            self.attach_q.put(("state", idx,
                                               {"state": "error",
                                                "detail": "未找到 Motrix 配置",
                                                "text": "未找到 Motrix 配置"}))
                    else:
                        port, secret = endpoint
                        for idx, _r in tracked:
                            try:
                                st = _motrix_task_status(port, secret, _r["gid"])
                            except Exception as e:
                                msg = str(e)
                                if "is not found" in msg:
                                    # 任务记录被 Motrix 清除（SQLite 持久化模式下
                                    # 完成任务即刻移出 RPC；或引擎已重启）——
                                    # 交 UI 按目标文件是否落盘判定完成/丢失
                                    self.attach_q.put(("gone", idx, {}))
                                else:
                                    self.attach_q.put(("log", idx,
                                                       {"text": f"⚠ 进度查询失败: {msg}"}))
                                continue
                            self.attach_q.put(("status", idx, st))
            except Exception:
                pass  # 轮询线程永不退出，异常下个节拍重来
            time.sleep(1.0)

    def _apply_attach_gone(self, idx):
        """GID 在引擎中消失（Motrix SQLite 模式下完成任务/出错任务会被
        移出 RPC，或引擎重启）：按目标文件落盘大小判定完成/中断/丢失。"""
        row = self.attach_rows.get(idx)
        if not row or row["state"] not in ("active", "waiting", "stopping"):
            return
        a = self.attachments[idx]
        target = os.path.join(a.get("out_dir") or ".",
                              _safe_filename(a["name"]) or "attachment.bin")
        total = row.get("total") or 0
        size = os.path.getsize(target) if os.path.exists(target) else -1
        if size > 0 and (total <= 0 or size >= total):
            self._attach_finalize_complete(idx)
            return
        elif size >= 0:
            row["state"] = "error"
            row["gid"] = None
            row["error"] = "下载已中断，请点击「重新下载」"
            row["status_text"] = ""
        else:
            row["state"] = "error"
            row["gid"] = None
            row["error"] = "任务记录已清除（Motrix 可能已重启），请重新下载"
            row["status_text"] = ""
        self._render_attach_row(idx)

    def _poll_attach_queue(self):
        try:
            while True:
                kind, idx, payload = self.attach_q.get_nowait()
                if kind == "state":
                    self._set_attach_state(idx, payload["state"],
                                           detail=payload.get("detail"),
                                           text=payload.get("text"))
                elif kind == "status":
                    self._apply_attach_status(idx, payload)
                elif kind == "gone":
                    self._apply_attach_gone(idx)
                elif kind == "log":
                    self._ui_log(payload.get("text", ""))
        except queue.Empty:
            pass
        self.root.after(150, self._poll_attach_queue)

    def _open_selected_folder(self, _event=None):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self.files):
            folder = os.path.dirname(self.files[idx])
            try:
                os.startfile(folder)
            except Exception as e:
                self._ui_log(f"打开文件夹失败: {e}")

    def _add_files(self):
        exts = _get_format_extensions(self.learned)
        # 精确列出已知格式；*zf/*cf 通配兜底任意字母/数字前缀（注意：Windows 的 *.zf
        # 匹配不到 .aqzf 这类带中间点的扩展名，因此必须用无点通配 *zf / *cf）
        pattern = ";".join(f"*.{e}" for e in exts) + ";*zf;*cf"
        paths = filedialog.askopenfilenames(
            title="选择招标文件",
            filetypes=[("招标文件 (*zf/*cf)", pattern), ("所有文件", "*.*")],
        )
        for p in paths:
            self._add_path(p)
        self.status_text.set(f"已添加 {len(self.files)} 个文件")

    def _add_folder(self):
        folder = filedialog.askdirectory(title="选择存放招标文件的文件夹")
        if not folder:
            return
        count = 0
        for fp in _collect_cli_files([folder]):
            self._add_path(fp)
            count += 1
        self.status_text.set(f"已添加 {count} 个文件")

    def _remove_selected(self):
        sel = list(self.file_listbox.curselection())
        if not sel:
            return
        for idx in reversed(sel):
            self.file_listbox.delete(idx)
            del self.files[idx]
        self.status_text.set(f"已移除 {len(sel)} 个文件，剩余 {len(self.files)} 个")
        self._refresh_list_ui()

    def _clear_list(self):
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.status_text.set("列表已清空")
        self._refresh_list_ui()

    # ---- 后台线程解压：worker 线程只通过队列与 UI 通信 ----
    def _start_extract(self):
        if self.is_running:
            return
        if not self.files:
            messagebox.showinfo("提示", "请先添加文件")
            return

        self.is_running = True
        self.cancel_event.clear()
        self.btn_extract.config(text="解压中…", state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.pct_text.set("0%")
        self.log_text.delete(1.0, tk.END)
        self.last_output_dir = None

        files = list(self.files)
        overwrite = self.overwrite_var.get()
        registry, learned = self.registry, self.learned
        q = queue.Queue()
        self.q = q

        def worker():
            try:
                summary = run_batch(
                    files, overwrite=overwrite,
                    log=lambda m: q.put(("log", m)),
                    progress=lambda i, t, n: q.put(("prog", (i, t, n))),
                    registry=registry, learned=learned,
                    cancel_event=self.cancel_event,
                    make_checksum=self.checksum_var.get(),
                )
            except Exception as e:  # 兜底：绝不让线程静默死亡
                summary = {"success": 0, "failed": len(files),
                           "cancelled": 0, "learned": [], "last_dir": None}
                q.put(("log", f"发生未预期异常: {e}"))
                _log("批量解压异常", exc=e)
            q.put(("done", summary))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, self._poll_queue)

    def _cancel_extract(self):
        if not self.is_running:
            return
        self.cancel_event.set()
        self.status_text.set("正在取消…")
        self._ui_log("⏹ 用户请求取消，等待当前文件处理完毕…")
        self.btn_cancel.config(state=tk.DISABLED)

    def _poll_queue(self):
        q = self.q
        try:
            while True:
                kind, payload = q.get_nowait()
                if kind == "log":
                    self._ui_log(payload)
                elif kind == "prog":
                    idx, total, name = payload
                    pct = int(idx / total * 100) if total else 100
                    self.progress_var.set(pct)
                    self.pct_text.set(f"{pct}%")
                    self.status_text.set(f"正在处理 ({idx + 1}/{total}): {name}" if idx < total
                                         else f"完成 ({total}/{total})")
                elif kind == "done":
                    self._finish(payload)
                    return
        except queue.Empty:
            pass
        self.root.after(80, self._poll_queue)

    def _finish(self, summary):
        success, failed = summary["success"], summary["failed"]
        cancelled = summary.get("cancelled", 0)
        learned_list = summary["learned"]
        self.last_output_dir = summary["last_dir"]

        self.progress_var.set(100)
        self.pct_text.set("100%")
        self.btn_cancel.config(state=tk.DISABLED)
        if cancelled:
            self.status_text.set(f"已取消: 成功 {success}, 失败 {failed}, 取消 {cancelled}")
            self._ui_log(f"\n已取消: 成功: {success}, 失败: {failed}, 取消: {cancelled}")
        else:
            self.status_text.set(f"完成: 成功 {success}, 失败 {failed}")
            self._ui_log(f"\n全部完成! 成功: {success}, 失败: {failed}")
        if learned_list:
            self._ui_log(f"★ 新学习格式: {', '.join('.' + x for x in learned_list)}")
        self.attachments = list(summary.get("attachments", []))
        if self.attachments:
            self._populate_attachments()

        if cancelled:
            messagebox.showinfo("完成", f"已取消: 成功 {success}, 失败 {failed}, 取消 {cancelled}")
        elif failed > 0:
            messagebox.showwarning("完成", f"成功: {success}, 失败: {failed}\n详情请查看日志")
        elif success > 0:
            parts = [f"成功解压 {success} 个文件"]
            if self.attachments:
                parts.append(f"识别到 {len(self.attachments)} 个可下载附件，"
                             + "已列在右侧「可下载附件」栏，点行内「下载」"
                               "或「全部下载」无头提交 Motrix")
            if self.last_output_dir:
                parts.append(f"输出目录:\n{self.last_output_dir}")
            messagebox.showinfo("解压完成", "\n".join(parts))
            if self.open_dir_var.get() and self.last_output_dir:
                try:
                    os.startfile(self.last_output_dir)
                except Exception:
                    pass

        self.is_running = False
        self.q = None
        self.btn_extract.config(text="开始解压", state=tk.NORMAL)

    def run(self):
        self.root.mainloop()


# ============================================================================
# 命令行解析与 --auto 自动模式
# ============================================================================
def _parse_args(argv):
    """极简参数解析：位置参数为文件/文件夹；--auto；--out DIR 或 --out=DIR；
    --quiet；--recursive；--no-checksum（默认生成 SHA-256 校验清单）。
    返回 (auto, out, files, quiet, recursive, checksum)。"""
    auto = False
    out = None
    quiet = False
    recursive = False
    checksum = True
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--auto":
            auto = True
        elif a == "--out":
            i += 1
            if i < len(argv):
                out = argv[i]
        elif a.startswith("--out="):
            out = a.split("=", 1)[1]
        elif a == "--quiet":
            quiet = True
        elif a == "--recursive":
            recursive = True
        elif a == "--no-checksum":
            checksum = False
        else:
            files.append(a)
        i += 1
    return auto, out, files, quiet, recursive, checksum


def _collect_cli_files(paths, recursive=False):
    """把传入的文件/文件夹路径展开为受支持的文件列表（去重保序）。
    recursive=True 时文件夹递归深入子目录（同批保持稳定排序：目录序 + 文件名序）。"""
    files = []
    for p in paths:
        if os.path.isdir(p):
            if recursive:
                names = []
                for root, dirs, fnames in os.walk(p):
                    dirs.sort()
                    for fn in sorted(fnames):
                        fp = os.path.join(root, fn)
                        ext = os.path.splitext(fn)[1].lstrip(".").lower()
                        if os.path.isfile(fp) and _is_supported_ext(ext):
                            names.append(fp)
                files.extend(names)
            else:
                for f in sorted(os.listdir(p)):
                    fp = os.path.join(p, f)
                    ext = os.path.splitext(f)[1].lstrip(".").lower()
                    if os.path.isfile(fp) and _is_supported_ext(ext):
                        files.append(fp)
        elif os.path.isfile(p) and _is_supported_ext(os.path.splitext(p)[1].lstrip(".").lower()):
            files.append(p)
    seen = set()
    return [x for x in files if not (x in seen or seen.add(x))]


class AutoRunner:
    """--auto 模式：无主操作界面，仅显示进度小窗；完成后弹结果框退出。
    退出码：0 全部成功；1 有失败/取消；2 未收到有效输入。
    quiet=True 时完全静默：不弹窗、不打开输出目录，适合脚本/自动化调用。"""

    def __init__(self, files, out_dir=None, quiet=False, checksum=True):
        self.files = files
        self.out_dir = out_dir
        self.quiet = quiet
        self.checksum = checksum
        self.exit_code = None
        self.q = queue.Queue()
        self.registry, self.learned = _load_registry()

        self.root = make_root()
        self.root.title(f"招标文件快速解压工具 {APP_VERSION} - 自动解压")
        self.root.geometry("620x340")
        self.root.configure(background=BG)
        if quiet:
            self.root.withdraw()  # 无窗口运行，完成后立即退出
        else:
            self.root.attributes("-topmost", True)

        header = tk.Frame(self.root, background=CARD,
                          highlightthickness=1, highlightbackground=BORDER)
        header.pack(fill=tk.X)
        ttk.Label(header, text="自动解压", style="H1.TLabel").pack(side=tk.LEFT, padx=(16, 10), pady=12)
        ttk.Label(header, text=f"{APP_VERSION} | 拖放或命令行触发",
                  style="Sub.TLabel").pack(side=tk.LEFT, pady=(4, 0))

        main = ttk.Frame(self.root, padding=(14, 10))
        main.pack(fill=tk.BOTH, expand=True)

        top_row = ttk.Frame(main)
        top_row.pack(fill=tk.X)
        ttk.Label(top_row, text=f"共 {len(files)} 个文件，自动解压中…",
                  style="Section.TLabel").pack(side=tk.LEFT)
        self.status = tk.StringVar(value="就绪")
        ttk.Label(top_row, textvariable=self.status,
                  style="Pct.TLabel").pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(main, maximum=max(len(files), 1),
                                        style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, pady=(6, 10))

        log_card = tk.Frame(main, background="#FAFBFC", highlightthickness=1,
                            highlightbackground=BORDER, highlightcolor=ACCENT)
        log_card.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_card, font=(FONT, 9), bg="#FAFBFC", fg=FG,
                                relief="flat", padx=8, pady=6, wrap="none",
                                insertbackground=FG, selectbackground=SELECT_BG,
                                selectforeground=FG)
        log_scroll = ttk.Scrollbar(log_card, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        config_log_tags(self.log_text)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        threading.Thread(target=self._worker, daemon=True).start()
        self.root.after(80, self._poll)

    def _worker(self):
        try:
            summary = run_batch(
                self.files, overwrite=True,
                log=lambda m: self.q.put(("log", m)),
                progress=lambda i, t, n: self.q.put(("prog", (i, t, n))),
                registry=self.registry, learned=self.learned,
                output_dir=self.out_dir,
                make_checksum=self.checksum,
            )
        except Exception as e:
            _log("auto 批量异常", exc=e)
            summary = {"success": 0, "failed": len(self.files),
                       "learned": [], "last_dir": None}
            self.q.put(("log", f"发生异常: {e}"))
        self.q.put(("done", summary))

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    write_log(self.log_text, payload)
                elif kind == "prog":
                    i, t, n = payload
                    self.progress.configure(maximum=max(t, 1), value=i)
                    self.status.set(f"({i + 1}/{t}) {n}" if i < t else f"完成 {t} 个")
                elif kind == "done":
                    self.root.after(0, lambda s=payload: self._finish(s))
                    return
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _finish(self, summary):
        s, f = summary["success"], summary["failed"]
        c = summary.get("cancelled", 0)
        self.exit_code = 1 if (f or c) else 0
        if self.quiet:
            self.root.destroy()
            return
        messagebox.showinfo("自动解压完成",
                            f"成功: {s}, 失败: {f}" + (f", 取消: {c}" if c else ""))
        if s > 0 and summary["last_dir"]:
            try:
                os.startfile(summary["last_dir"])
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.exit_code if self.exit_code is not None else (1 if self.files else 2)


if __name__ == "__main__":
    auto, out_dir, cli_paths, quiet, recursive, checksum = _parse_args(sys.argv[1:])
    if auto:
        cli_files = _collect_cli_files(cli_paths, recursive=recursive)
        if not cli_files:
            _log("--auto 未收到有效文件/文件夹")
            sys.exit(2)
        try:
            sys.exit(AutoRunner(cli_files, out_dir, quiet=quiet, checksum=checksum).run())
        except SystemExit:
            raise
        except Exception as e:
            _log("启动失败(--auto)", exc=e)
            sys.exit(1)
    else:
        app = ExtractTool()
        try:
            app.run()
        except Exception as e:
            _log(f"启动失败", exc=e)
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(e), "启动失败", 0)
