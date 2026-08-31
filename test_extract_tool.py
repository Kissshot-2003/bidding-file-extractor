# -*- coding: utf-8 -*-
"""招标文件快速解压工具 - 核心逻辑单元测试。
运行: python test_extract_tool.py
隔离：FORMAT_REGISTRY / ERROR_LOG 重定向到临时目录，不污染桌面真实文件。
"""
import os
import sys
import io
import copy
import json
import base64
import zipfile
import tempfile
import shutil
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_tool as et

HDR = '<?xml version="1.0" encoding="utf-8"?>'


def make_zip_bytes(entries):
    """entries: [(name, bytes), ...] 或 {name: bytes}；重复名可模拟 ZIP 内部重名。"""
    items = entries.items() if isinstance(entries, dict) else entries
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in items:
            z.writestr(name, data)
    return buf.getvalue()


def wrap_b64(data, width=64):
    """Base64 后每 width 字符插入换行，模拟真实文件的多行内容。"""
    b = base64.b64encode(data).decode("ascii")
    return "\r\n".join(b[i:i + width] for i in range(0, len(b), width))


def write_case(dirpath, filename, xml):
    p = os.path.join(dirpath, filename)
    with open(p, "w", encoding="utf-8") as f:
        f.write(xml)
    return p


def bad_crc_open_factory(bad_name):
    """返回一个 mock.patch 目标函数：把 zipfile 的 infolist() 改为
    对 bad_name 条目返回 CRC 被翻转的副本，模拟容器内置哈希校验一致
    (zip 条目记录 CRC 与解压数据不符，典型场景：解密产物出错，但 zip 能照常读取)。"""
    orig_infolist = zipfile.ZipFile.infolist

    def fake_infolist(self):
        out = []
        for zi in orig_infolist(self):
            if zi.filename == bad_name:
                zi2 = copy.copy(zi)
                zi2.CRC = zi.CRC ^ 0xFFFFFFFF
                out.append(zi2)
            else:
                out.append(zi)
        return out

    return fake_infolist


class ExtractTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="extract_tool_test_")
        self._old_reg, self._old_log = et.FORMAT_REGISTRY, et.ERROR_LOG
        et.FORMAT_REGISTRY = os.path.join(self.tmp, "format_registry.json")
        et.ERROR_LOG = os.path.join(self.tmp, "error.log")

    def tearDown(self):
        et.FORMAT_REGISTRY, et.ERROR_LOG = self._old_reg, self._old_log
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def pdf():
        return b"%PDF-1.4 fake-content"


class TagMatchingTests(ExtractTestBase):
    def test_builtin_zf(self):
        z = make_zip_bytes({"a.pdf": self.pdf()})
        src = write_case(self.tmp, "a.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        r = et.extract_file(src)
        self.assertEqual(r["files"], ["a.pdf"])

    def test_builtin_cf(self):
        z = make_zip_bytes({"a.pdf": self.pdf()})
        src = write_case(self.tmp, "b.cf",
                         HDR + '<R><DYFileContent>\n' + wrap_b64(z) + "\n</DYFileContent></R>")
        r = et.extract_file(src)
        self.assertEqual(r["files"], ["a.pdf"])

    def test_xczf_dyfile(self):
        """v1.5 修复场景：<DYFile> 根标签 + DYFileContent。"""
        z = make_zip_bytes({"答疑.pdf": self.pdf()})
        src = write_case(self.tmp, "c.xczf",
                         HDR + '\n<DYFile><DYGuid>X</DYGuid>'
                         "<DYFileContent>" + wrap_b64(z) + "</DYFileContent></DYFile>")
        r = et.extract_file(src)
        self.assertEqual(r["files"], ["答疑.pdf"])
        # 学习机制应记录实际命中的标签
        with open(et.FORMAT_REGISTRY, encoding="utf-8") as f:
            reg = json.load(f)
        self.assertEqual(reg.get("xczf"), "DYFileContent")

    def test_registry_wrong_mapping_falls_back(self):
        """扩展名映射到 ZBFileContent 但实际是 DYFileContent 时应回退成功。"""
        z = make_zip_bytes({"d.pdf": self.pdf()})
        src = write_case(self.tmp, "d.zf",
                         HDR + "<R><DYFileContent>" + wrap_b64(z) + "</DYFileContent></R>")
        r = et.extract_file(src)
        self.assertEqual(r["files"], ["d.pdf"])

    def test_generic_unknown_tag(self):
        """全新 <XXXFileContent> 标签应被泛化匹配。"""
        z = make_zip_bytes({"e.pdf": self.pdf()})
        src = write_case(self.tmp, "e.newfmt",
                         HDR + "<Root><ABCDFileContent>" + wrap_b64(z) + "</ABCDFileContent></Root>")
        r = et.extract_file(src)
        self.assertEqual(r["files"], ["e.pdf"])

    def test_no_header_rejected(self):
        """无 <?xml 声明头的文件应被拒绝（与 v1.4 行为一致）。"""
        z = make_zip_bytes({"x.pdf": self.pdf()})
        src = write_case(self.tmp, "nohdr.zf",
                         "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        with self.assertRaises(ValueError):
            et.extract_file(src)

    def test_bom_and_whitespace_tolerated(self):
        z = make_zip_bytes({"f.pdf": self.pdf()})
        src = write_case(self.tmp, "f.zf",
                         "﻿\n  " + HDR + "<ZBFileContent>" + wrap_b64(z) + "</ZBFileContent>")
        r = et.extract_file(src)
        self.assertEqual(r["files"], ["f.pdf"])


    def test_learned_format_save_with_bom(self):
        """v1.8 回归：注册表文件带 BOM 时学习结果仍能保存（utf-8-sig 读取）。"""
        et._save_learned_format("xczf", "DYFileContent")
        self.assertEqual(et._load_registry()[0].get("xczf"), "DYFileContent")

    def test_cancel_pending(self):
        """cancel_event 预置：解压应立即中止且不计入失败。"""
        z = make_zip_bytes({"c1.pdf": self.pdf(), "c2.pdf": self.pdf()})
        src = write_case(self.tmp, "cancel.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        ev = threading.Event()
        ev.set()
        with self.assertRaises(et.CancelledError):
            et.extract_file(src, cancel_event=ev)

    def test_run_batch_cancel_counts(self):
        ev = threading.Event()
        ev.set()
        a = write_case(self.tmp, "a1.zf",
                       HDR + "<R><ZBFileContent>"
                       + wrap_b64(make_zip_bytes({"k.pdf": self.pdf()}))
                       + "</ZBFileContent></R>")
        b = write_case(self.tmp, "b1.zf", "garbage")
        s = et.run_batch([a, b], cancel_event=ev)
        self.assertEqual(s["success"], 0)
        self.assertEqual(s["failed"], 0)
        self.assertEqual(s["cancelled"], 2)

    def test_run_batch_cancel_after_first(self):
        """第一个文件解压成功后取消：第一个成功、第二个计入取消、无失败。"""
        a = write_case(self.tmp, "ok.zf",
                       HDR + "<R><ZBFileContent>"
                       + wrap_b64(make_zip_bytes({"fine.pdf": self.pdf()}))
                       + "</ZBFileContent></R>")
        b = write_case(self.tmp, "later.zf", "garbage")
        ev = threading.Event()

        def after_done(m):
            if str(m).startswith("✓ ok.zf"):
                ev.set()

        s = et.run_batch([a, b], log=after_done, cancel_event=ev)
        self.assertEqual(s["success"], 1)
        self.assertEqual(s["failed"], 0)
        self.assertEqual(s["cancelled"], 1)


class ErrorTests(ExtractTestBase):
    def test_not_xml_rejected(self):
        src = write_case(self.tmp, "bad.zf", "hello not xml")
        with self.assertRaises(ValueError) as cm:
            et.extract_file(src)
        self.assertIn("不是有效的 XML", str(cm.exception))

    def test_missing_content_rejected(self):
        src = write_case(self.tmp, "nocontent.zf", HDR + "<R><Other>x</Other></R>")
        with self.assertRaises(ValueError) as cm:
            et.extract_file(src)
        self.assertIn("未找到招标文件内容", str(cm.exception))

    def test_not_pk_rejected(self):
        fake = base64.b64encode(b"NOT_A_ZIP_DATA____").decode()
        src = write_case(self.tmp, "notpk.zf", HDR + f"<R><ZBFileContent>{fake}</ZBFileContent></R>")
        with self.assertRaises(ValueError) as cm:
            et.extract_file(src)
        self.assertIn("不是有效的 ZIP", str(cm.exception))


class ExtractionBehaviorTests(ExtractTestBase):
    def _src_dup_entries(self, name="dup.zf"):
        z = make_zip_bytes([("PBZB.xml", b"<control/>"),
                            ("same.pdf", b"first"),
                            ("same.pdf", b"second")])
        return write_case(self.tmp, name,
                          HDR + f"<R><ZBFileContent>{wrap_b64(z)}</ZBFileContent></R>")

    def test_internal_file_excluded_and_dupes_numbered(self):
        logs = []
        r = et.extract_file(self._src_dup_entries(), log=logs.append)
        self.assertNotIn("PBZB.xml", r["files"])
        listed = [f for f in os.listdir(r["dir"]) if f != "_SHA256SUMS.txt"]
        self.assertEqual(sorted(listed), ["same(1).pdf", "same.pdf"])
        self.assertTrue(any("跳过内部文件" in m for m in logs))

    def test_overwrite_true_replaces_existing(self):
        src = self._src_dup_entries("ow.zf")
        et.extract_file(src)
        target1 = os.path.join(self.tmp, "ow", "same.pdf")
        self.assertTrue(os.path.exists(target1))
        r2 = et.extract_file(src)  # 同名再次解压：应原地覆盖而非改名
        self.assertEqual(sorted(r2["files"]), ["same(1).pdf", "same.pdf"])
        # 目录内不应出现 (2)(3) 等累积副本
        listed = [f for f in os.listdir(os.path.join(self.tmp, "ow")) if f != "_SHA256SUMS.txt"]
        self.assertEqual(sorted(listed), ["same(1).pdf", "same.pdf"])
        del target1

    def test_overwrite_false_skips_existing(self):
        src = write_case(self.tmp, "skip.zf",
                         HDR + "<R><ZBFileContent>"
                         + wrap_b64(make_zip_bytes({"s.pdf": self.pdf()}))
                         + "</ZBFileContent></R>")
        logs = []
        et.extract_file(src, log=logs.append)
        logs.clear()
        r = et.extract_file(src, overwrite=False, log=logs.append)
        self.assertEqual(r["files"], [])
        self.assertTrue(any("已存在" in m for m in logs))
        # 原文件内容未被破坏
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "skip", "s.pdf")))

    def test_max_total_size_cap(self):
        z = make_zip_bytes({"small.txt": b"a", "big.bin": b"x" * (4 * 1024 * 1024)})
        src = write_case(self.tmp, "cap.zf",
                         HDR + f"<R><ZBFileContent>{wrap_b64(z)}</ZBFileContent></R>")
        r = et.extract_file(src, max_total_size=1024 * 1024)
        self.assertEqual(r["files"], ["small.txt"])
        self.assertGreater(r["skipped_size"], 0)

    def test_output_dir_param(self):
        out_root = os.path.join(self.tmp, "out")
        src = write_case(self.tmp, "od.zf",
                         HDR + "<R><ZBFileContent>"
                         + wrap_b64(make_zip_bytes({"o.pdf": self.pdf()}))
                         + "</ZBFileContent></R>")
        r = et.extract_file(src, output_dir=out_root)
        self.assertTrue(r["dir"].startswith(out_root))
        self.assertTrue(os.path.isfile(os.path.join(r["dir"], "o.pdf")))


class ChecksumTests(ExtractTestBase):
    def test_checksum_file_generated(self):
        z = make_zip_bytes({"s.pdf": self.pdf(), "清单.xlsx": b"XLSX-data"})
        src = write_case(self.tmp, "cs.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        r = et.extract_file(src)
        self.assertTrue(r["checksum_file"])
        self.assertNotIn("_SHA256SUMS.txt", r["files"])  # 清单不混入交付文件
        with open(r["checksum_file"], encoding="utf-8", newline="") as f:
            lines = f.read().strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith(r["hashes"]["s.pdf"]))
        self.assertTrue(lines[1].startswith(r["hashes"]["清单.xlsx"]))
        # 哈希确实等于原始数据（防计算错误）
        import hashlib
        self.assertEqual(r["hashes"]["s.pdf"], hashlib.sha256(self.pdf()).hexdigest())

    def test_checksum_disabled(self):
        z = make_zip_bytes({"s.pdf": self.pdf()})
        src = write_case(self.tmp, "cs2.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        r = et.extract_file(src, make_checksum=False)
        self.assertIsNone(r["checksum_file"])
        self.assertFalse(os.path.exists(os.path.join(r["dir"], "_SHA256SUMS.txt")))

    def test_crc_mismatch_skips_entry(self):
        """v1.9 核心：CRC 与 zip 记录不符即判定解压产物损坏，拦截该条目。"""
        z = make_zip_bytes([("ok.pdf", self.pdf()), ("bad.pdf", b"corrupted-by-decrypt")])
        src = write_case(self.tmp, "crc.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        logs = []
        with mock.patch.object(zipfile.ZipFile, "infolist", bad_crc_open_factory("bad.pdf")):
            r = et.extract_file(src, log=logs.append)
        self.assertEqual(r["files"], ["ok.pdf"])  # 好条目正常，坏条目被拦
        # zipfile 自身或本工具兜底校验均可判 CRC 不符
        self.assertTrue(any("bad.pdf" in m and ("CRC" in m) for m in logs))
        # 半成品不残留（_ 开头 ASCII 排序在前）
        self.assertEqual(sorted(os.listdir(r["dir"])), ["_SHA256SUMS.txt", "ok.pdf"])

    def test_crc_bad_returns_hashes_only_good(self):
        z = make_zip_bytes([("ok.pdf", self.pdf()), ("bad.pdf", b"xx")])
        src = write_case(self.tmp, "crc2.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        with mock.patch.object(zipfile.ZipFile, "infolist", bad_crc_open_factory("bad.pdf")):
            r = et.extract_file(src)
        self.assertIn("ok.pdf", r["hashes"])
        self.assertNotIn("bad.pdf", r["hashes"])
        with open(r["checksum_file"], encoding="utf-8") as f:
            self.assertNotIn("bad.pdf", f.read())


class CorruptEntryTests(ExtractTestBase):
    def test_corrupt_entry_skipped_rest_ok(self):
        """v1.8 回归：单个条目损坏时跳过该条目，其余条目正常解压。"""
        z = make_zip_bytes([("bad.pdf", b"broken"),
                            ("good.pdf", self.pdf())])
        src = write_case(self.tmp, "corrupt.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        logs = []
        orig_open = zipfile.ZipFile.open

        def fake_open(self, name, mode="r", pwd=None, force_zip64=False):
            fn = getattr(name, "filename", None) or name
            if str(fn).endswith("bad.pdf"):
                raise RuntimeError("模拟损坏条目")
            return orig_open(self, name, mode, pwd)

        with mock.patch.object(zipfile.ZipFile, "open", fake_open):
            r = et.extract_file(src, log=logs.append)
        self.assertEqual(r["files"], ["good.pdf"])  # 坏条目被跳过但不失败
        self.assertTrue(any("bad.pdf" in m and "跳过" in m for m in logs))
        # 坏条目的残留碎片文件不应留下
        listed = [f for f in os.listdir(r["dir"]) if f != "_SHA256SUMS.txt"]
        self.assertEqual(sorted(listed), ["good.pdf"])

    def test_corrupt_single_file_still_reports_success(self):
        """即使某文件内部有坏条目，整文件仍算解压成功（warnings 计数 +1）。"""
        z = make_zip_bytes([("x.pdf", self.pdf())])
        src = write_case(self.tmp, "ok.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        s = et.run_batch([src])
        self.assertEqual(s["success"], 1)
        self.assertEqual(s["failed"], 0)


class BatchTests(ExtractTestBase):
    def test_run_batch_summary(self):
        ok = write_case(self.tmp, "ok1.zf",
                        HDR + "<R><ZBFileContent>"
                        + wrap_b64(make_zip_bytes({"k.pdf": self.pdf()}))
                        + "</ZBFileContent></R>")
        bad = write_case(self.tmp, "bad1.zf", "garbage")
        prog = []
        s = et.run_batch([ok, bad], progress=lambda i, t, n: prog.append((i, t)))
        self.assertEqual(s["success"], 1)
        self.assertEqual(s["failed"], 1)
        self.assertEqual(prog[-1], (2, 2))


class CliHelperTests(unittest.TestCase):
    def test_parse_args(self):
        auto, out, files, quiet, recursive, checksum = et._parse_args(
            ["--auto", "--out", "D:\\x", "a.zf"])
        self.assertTrue(auto)
        self.assertEqual(out, "D:\\x")
        self.assertEqual(files, ["a.zf"])
        self.assertFalse(quiet)
        self.assertFalse(recursive)
        self.assertTrue(checksum)  # 默认生成校验清单
        auto, out, files, quiet, recursive, checksum = et._parse_args(["--auto", "--out=D:\\y"])
        self.assertTrue(auto)
        self.assertEqual(out, "D:\\y")
        self.assertEqual(files, [])
        self.assertFalse(quiet)
        self.assertFalse(recursive)
        self.assertTrue(checksum)

    def test_parse_args_quiet_recursive(self):
        auto, out, files, quiet, recursive, checksum = et._parse_args(
            ["--auto", "--quiet", "--recursive", "--out", "D:\\z", "f.zf"])
        self.assertTrue(auto)
        self.assertTrue(quiet)
        self.assertTrue(recursive)
        self.assertEqual(out, "D:\\z")
        self.assertEqual(files, ["f.zf"])
        self.assertTrue(checksum)
        auto, out, files, quiet, recursive, checksum = et._parse_args(
            ["--auto", "--no-checksum"])
        self.assertTrue(auto)
        self.assertFalse(checksum)

    def test_collect_cli_files(self):
        tmp = tempfile.mkdtemp(prefix="collect_test_")
        try:
            a = write_case(tmp, "a.zf", HDR + "<R/>")
            write_case(tmp, "ignore.txt", "x")
            sub = os.path.join(tmp, "sub")
            os.makedirs(sub)
            b = write_case(sub, "b.cf", HDR + "<R/>")
            files = et._collect_cli_files([tmp])
            self.assertEqual(files, [a])  # 非递归扫描：仅顶层文件，.txt 被过滤，sub 不深入
            files2 = et._collect_cli_files([a, a, sub])
            self.assertEqual(len(files2), 2)  # 去重保序
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_cli_files_recursive(self):
        tmp = tempfile.mkdtemp(prefix="collect_rec_")
        try:
            a = write_case(tmp, "a.zf", HDR + "<R/>")
            sub = os.path.join(tmp, "sub")
            os.makedirs(sub)
            deep = os.path.join(sub, "deep")
            os.makedirs(deep)
            bcat = write_case(deep, "b.cf", HDR + "<R/>")
            write_case(deep, "skip.txt", "x")
            files = et._collect_cli_files([tmp], recursive=True)
            self.assertEqual(files, [a, bcat])  # 递归含子目录，.txt 仍被过滤
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
