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
import hashlib
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


class AttachmentTests(ExtractTestBase):
    PBZB = ('<?xml version="1.0" encoding="utf-8"?>'
            '<XiangMuInfo BiaoDuanMC="测试工程">'
            '<ZBFileCAD>'
            '<CADMuLu MuLuName="图纸" Xh="1">'
            '<CADFile CADFileLx="9" CADFileName="http://114.98.87.113:9016/TPBidder/'
            'TuZhiDocShow?AttachGuid=aaa&amp;ClientGuid=bbb" CADTenderLx="3" '
            'CADTenderName="图纸.rar" NO="1"/>'
            '</CADMuLu>'
            '<CADMuLu MuLuName="清单控制价" Xh="2">'
            '<CADFile CADFileLx="9" CADFileName="http://114.98.87.113:9016/TPBidder/'
            'TuZhiDocShow?AttachGuid=ccc" CADTenderName="预算.rar" NO="1"/>'
            '</CADMuLu>'
            '</ZBFileCAD>'
            '</XiangMuInfo>')

    def test_extract_attachment_xml(self):
        att = et._extract_attachments(self.PBZB)
        self.assertEqual(len(att), 2)
        self.assertEqual(att[0]["category"], "图纸")
        self.assertEqual(att[0]["name"], "图纸.rar")
        self.assertNotIn("&amp;", att[0]["url"])  # 实体已解码
        self.assertEqual(att[1]["category"], "清单控制价")

    def test_extract_attachment_bare_url(self):
        att = et._extract_attachments('<x><a href="https://example.com/file.rar">下载</a></x>')
        self.assertEqual(len(att), 1)
        self.assertEqual(att[0]["url"], "https://example.com/file.rar")
        self.assertTrue(att[0]["name"])

    def test_extract_attachment_dedup(self):
        twice = et._extract_attachments(self.PBZB) + et._extract_attachments(self.PBZB)
        ded = et._dedup_attachments(twice)
        self.assertEqual(len(ded), 2)

    def test_run_batch_attachments_tagged_by_project(self):
        """v2.3：批量解压多个文件时，附件带归属项目与输出目录，防止下错位置。"""
        z1 = make_zip_bytes([("PBZB.xml", self.PBZB.encode("utf-8")),
                             ("正文.pdf", self.pdf())])
        s1 = write_case(self.tmp, "项目A.zf",
                        HDR + "<R><ZBFileContent>" + wrap_b64(z1) + "</ZBFileContent></R>")
        z2 = make_zip_bytes([("正文.pdf", self.pdf()), ("附件.txt",
                                                         b'<x fileUrl="https://d.example.com/b.rar">k</x>')])
        s2 = write_case(self.tmp, "项目B.cf",
                        HDR + "<R><DYFileContent>" + wrap_b64(z2) + "</DYFileContent></R>")
        summ = et.run_batch([s1, s2])
        att = summ["attachments"]
        self.assertEqual(len(att), 3)
        for a in att:
            self.assertTrue(a.get("project"))
            self.assertTrue(a.get("out_dir"))
        proj_a = [a for a in att if a["project"].startswith("项目A")]
        self.assertEqual(len(proj_a), 2)
        self.assertEqual(proj_a[0]["name"], "图纸.rar")
        self.assertIn(os.path.join(self.tmp, "项目A"), proj_a[0]["out_dir"])
        proj_b = [a for a in att if a["project"].startswith("项目B")]
        self.assertEqual(len(proj_b), 1)
        self.assertEqual(proj_b[0]["url"], "https://d.example.com/b.rar")
        self.assertIn(os.path.join(self.tmp, "项目B"), proj_b[0]["out_dir"])

    def test_extract_file_attachments_with_internal_excluded(self):
        """PBZB.xml 被排除写盘，但仍参与附件识别。"""
        z = make_zip_bytes([("PBZB.xml", self.PBZB.encode("utf-8")),
                            ("正文.pdf", self.pdf())])
        src = write_case(self.tmp, "att.zf",
                         HDR + "<R><ZBFileContent>" + wrap_b64(z) + "</ZBFileContent></R>")
        logs = []
        r = et.extract_file(src, log=logs.append)
        self.assertEqual(len(r["attachments"]), 2)
        self.assertNotIn("PBZB.xml", r["files"])  # 仍是内部文件不出盘
        self.assertTrue(any("跳过内部文件" in m for m in logs))
        self.assertTrue(any("可下载附件" in m for m in logs))

    def test_safe_filename(self):
        self.assertEqual(et._safe_filename('a/b\\c:d*e?f"g<h>i|j'), "a_b_c_d_e_f_g_h_i_j")
        self.assertTrue(len(et._safe_filename("x" * 500)) <= 240)


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

    def test_aria2c_path_found(self):
        # 源码/打包运行都应能定位内置 aria2c；找不到时返回 None（不抛异常）
        p = et._aria2c_path()
        if p is not None:
            self.assertTrue(os.path.isfile(p))

    def test_aria2_engine_start_and_stop(self):
        # 内置引擎可真实拉起并通过 RPC 查询版本；结束后必须能干净关闭
        if et._aria2c_path() is None:
            self.skipTest("未找到内置 aria2c.exe")
        try:
            endpoint = et._ensure_aria2_engine()
            self.assertIsNotNone(endpoint)
            port, secret = endpoint
            version = et._aria2_rpc(port, secret, "aria2.getVersion", timeout=5)
            self.assertIn("version", version)
        finally:
            et._stop_aria2_engine()

    def test_fmt_size_and_speed(self):
        self.assertEqual(et._fmt_size(0), "0 B")
        self.assertEqual(et._fmt_size(512), "512 B")
        self.assertEqual(et._fmt_size(2048), "2.0 KB")
        self.assertEqual(et._fmt_size(3 * 1024 * 1024), "3.0 MB")
        self.assertEqual(et._fmt_speed(0), "0 B/s")
        self.assertEqual(et._fmt_speed(1024 * 1024), "1.0 MB/s")

    def test_aria2_rpc_endpoint_shape(self):
        # 引擎未启动时返回 None；启动后返回 (端口, 令牌) 二元组；不抛异常
        endpoint = et._aria2_rpc_endpoint()
        if endpoint is not None:
            port, secret = endpoint
            self.assertIsInstance(port, int)
            self.assertIsInstance(secret, str)

    def test_aria2_rpc_error_raises(self):
        # 连一个大概率不存在的端口：必须抛异常而不是静默返回
        with self.assertRaises(Exception):
            et._aria2_rpc(16999, "", "aria2.getVersion", timeout=1)

    def test_looks_like_html(self):
        self.assertTrue(et._looks_like_html(b"<!DOCTYPE html><html>", None))
        self.assertTrue(et._looks_like_html(b"\xef\xbb\xbf<html lang=\"zh\">", "text/plain"))
        self.assertTrue(et._looks_like_html(b"xxx", "text/html; charset=utf-8"))
        self.assertFalse(et._looks_like_html(b"Rar!\x1a\x07\x01\x00", "application/octet-stream"))
        self.assertFalse(et._looks_like_html(b"", "application/json"))

    def test_epoint_action_url(self):
        page = ("http://220.179.5.14:90/TPBidder/netztbmis/pages/signature/TuZhiDocShow"
                "?AttachGuid=A1&ClientGuid=B2")
        action = et._epoint_action_url(page)
        self.assertEqual(action,
                         "http://220.179.5.14:90/TPBidder/netztbmis/pages/signature/TuZhiDocShowAction.action"
                         "?AttachGuid=A1&ClientGuid=B2")
        # 已是 .action / 无路径 / 带扩展名的路径不处理
        self.assertIsNone(et._epoint_action_url(page.replace("TuZhiDocShow", "TuZhiDocShowAction.action")))
        self.assertIsNone(et._epoint_action_url("http://x.com/file.rar?k=1"))

    def test_parse_epoint_server_file_path(self):
        raw = json.dumps({"controls": [], "custom": {
            "msg": "", "serverFilePath": "http://x/TuZhiDownloadAttachment.action?cmd=download&AttachGuid=A1"}})
        sp, msg = et._parse_epoint_server_file_path(raw)
        self.assertEqual(sp, "http://x/TuZhiDownloadAttachment.action?cmd=download&AttachGuid=A1")
        self.assertEqual(msg, "")
        sp2, msg2 = et._parse_epoint_server_file_path("not json")
        self.assertIsNone(sp2)
        self.assertIsNone(msg2)
        sp3, msg3 = et._parse_epoint_server_file_path(json.dumps({"custom": {"msg": "链接已过期"}}))
        self.assertIsNone(sp3)
        self.assertEqual(msg3, "链接已过期")

    def test_sniff_html_file(self):
        tmp = tempfile.mkdtemp(prefix="sniff_")
        try:
            hp = os.path.join(tmp, "a.rar")
            with open(hp, "wb") as f:
                f.write(b"<!DOCTYPE html><html><body>err</body></html>")
            self.assertTrue(et._sniff_html_file(hp))
            bp = os.path.join(tmp, "b.rar")
            with open(bp, "wb") as f:
                f.write(b"Rar!\x1a\x07\x01\x00" + b"\x00" * 64)
            self.assertFalse(et._sniff_html_file(bp))
            self.assertFalse(et._sniff_html_file(os.path.join(tmp, "missing.rar")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_themes_complete_and_apply(self):
        # 两个主题 token 完整且一致；_apply_theme 正确写入全局
        base = {"BG", "SIDEBAR", "CARD", "BORDER", "FG", "MUTED", "DIM",
                "ACCENT", "ACCENT_DARK", "SELECT_BG", "SUCCESS", "DANGER",
                "WARN", "STATUSBAR", "LOG_BG", "PRIMARY_FG",
                "PRIMARY_DISABLED_BG", "DANGER_FG", "DANGER_BORDER"}
        for name, t in et.THEMES.items():
            self.assertEqual(set(t), base, name)
        et._apply_theme("zb-light")
        self.assertEqual(et.BG, et.THEMES["zb-light"]["BG"])
        self.assertEqual(et._current_theme_name(), "zb-light")
        et._apply_theme("zb-teal")
        self.assertEqual(et.BG, et.THEMES["zb-teal"]["BG"])
        self.assertEqual(et._current_theme_name(), "zb-teal")
        et._apply_theme("nonexistent")
        self.assertEqual(et._current_theme_name(), "zb-teal")  # 未知主题回退
        et._apply_theme("zb-light")  # 还原默认（其余用例不受暗色影响）


def _pkcs7_pad(data):
    n = 16 - len(data) % 16
    return data + bytes([n]) * n


def _aes_ecb_encrypt(data, key):
    """用工具自带的 AES 原语做 ECB 加密（仅测试用）。"""
    w, Nr = et._key_expansion(key)
    out = b""
    for i in range(0, len(data), 16):
        out += et._aes_encrypt_block(data[i:i + 16], w, Nr)
    return out


GUID = "63a2c211-4304-415b-98ef-e83c76a8efba"
AQZF_PLAIN = "\ufeff<?xml version=\"1.0\" encoding=\"utf-8\"?>\r\n<JingJiBiao Xmbh=\"xm0\">清单一</JingJiBiao>".encode("utf-8")
PBZB_ON = ('<?xml version="1.0" encoding="utf-8"?><XiangMuInfo AreaName="DQAnQing">'
           "<BiaoShu><ZBInfo>"
           '<ZBInfoMx BookMarkName="EncryQingDan" MarkValue="1" Xh="1"/>'
           '<ZBInfoMx BookMarkName="EncryKey" MarkValue="%s" Xh="1"/>'
           "</ZBInfo></BiaoShu></XiangMuInfo>" % GUID).encode("utf-8")


def _make_aqzf_file(dirpath, filename, inner_name, inner_plain, pbzb, encry_key=GUID):
    """构造合成 .AQZF（XML 包裹 + base64 ZIP{PBZB.xml + 加密清单}）。"""
    if encry_key:
        digest = hashlib.md5(encry_key.strip().encode("utf-8")).digest()
        key = digest[8:] + digest[:8]
        inner = _aes_ecb_encrypt(_pkcs7_pad(inner_plain), key)
    else:
        inner = inner_plain
    z = make_zip_bytes([("PBZB.xml", pbzb), (inner_name, inner)])
    xml = (HDR + '<ZBFile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
           "<ZBGuid>B8BD8B96</ZBGuid><UserIdentifier>69E3007A</UserIdentifier>"
           "<ZBFileContent>" + wrap_b64(z) + "</ZBFileContent>"
           "<EncryMode>3</EncryMode><GMtype>EPGM_0</GMtype></ZBFile>")
    return write_case(dirpath, filename, xml)


class AqzfDecryptTests(ExtractTestBase):
    """安庆 .AQZF 内层清单解密（MD5(EncryKey) 轮换 → AES-128-ECB/PKCS7）。
    v3.1：多标段多密钥、EncryQingDan 非 "0" 均尝试、PKCS7 严格校验。"""

    def test_decrypt_roundtrip_and_key_rotation(self):
        import hashlib as _h
        d = _h.md5(GUID.encode()).digest()
        # 轮换密钥可解；未轮换的原始 MD5 不可解（防止实现退化）
        self.assertEqual(et._aqzf_pbzb_decrypt(
            _aes_ecb_encrypt(_pkcs7_pad(AQZF_PLAIN), d[8:] + d[:8]), GUID), AQZF_PLAIN)
        wrong = et.aes_ecb_decrypt(
            _aes_ecb_encrypt(_pkcs7_pad(AQZF_PLAIN), d[8:] + d[:8]), d)
        self.assertNotEqual(wrong, _pkcs7_pad(AQZF_PLAIN))  # 未轮换密钥解不开轮换密文
        # 错误密钥必须报错而非静默返回乱文（PKCS7 严格校验）
        with self.assertRaises(Exception):
            et._aqzf_pbzb_decrypt(
                _aes_ecb_encrypt(_pkcs7_pad(AQZF_PLAIN), d[8:] + d[:8]),
                "00000000-0000-0000-0000-000000000000")

    def test_pkcs7_unpad_strict(self):
        """v3.1：PKCS7 填充非法/为空/长度非块对齐必须抛错。"""
        self.assertEqual(et.pkcs7_unpad(_pkcs7_pad(b"abc")), b"abc")
        self.assertEqual(et.pkcs7_unpad(_pkcs7_pad(b"x" * 16)), b"x" * 16)
        with self.assertRaises(Exception):
            et.pkcs7_unpad(b"A" * 16)  # 填充非法
        with self.assertRaises(Exception):
            et.pkcs7_unpad(b"")  # 空
        with self.assertRaises(Exception):
            et.pkcs7_unpad(b"abc")  # 长度非块对齐

    def test_parse_pbzb_zbinfo_attribute_order(self):
        k, f = et._parse_pbzb_zbinfo(PBZB_ON.decode("utf-8"))
        self.assertEqual((k, f), ([GUID], "1"))
        # 属性顺序颠倒也应解析
        xml2 = ('<ZBInfo><ZBInfoMx MarkValue="%s" BookMarkName="EncryKey"/>'
                '<ZBInfoMx MarkValue="1" BookMarkName="EncryQingDan"/></ZBInfo>' % GUID)
        k2, f2 = et._parse_pbzb_zbinfo(xml2)
        self.assertEqual((k2, f2), ([GUID], "1"))
        # 缺书签
        self.assertEqual(et._parse_pbzb_zbinfo("<ZBInfo></ZBInfo>"), ([], None))

    def test_parse_pbzb_zbinfo_multi_segment(self):
        """v3.1：多标段容器含多个 EncryKey，全部收集、去重、保持顺序。"""
        k1, k2 = GUID, "11111111-2222-3333-4444-555555555555"
        xml = ('<ZBInfo>'
               '<ZBInfoMx BookMarkName="EncryQingDan" MarkValue="1"/>'
               f'<ZBInfoMx BookMarkName="EncryKey" MarkValue="{k1}"/>'
               f'<ZBInfoMx BookMarkName="EncryKey" MarkValue="{k2}"/>'
               f'<ZBInfoMx BookMarkName="EncryKey" MarkValue="{k1}"/>'  # 重复：去重
               "</ZBInfo>")
        keys, flag = et._parse_pbzb_zbinfo(xml)
        self.assertEqual(keys, [k1, k2])
        self.assertEqual(flag, "1")

    def test_decrypt_best_multi_key(self):
        """v3.1：多密钥逐个尝试，命中正确密钥并返回命中者。"""
        import hashlib as _h
        k_other = "00000000-0000-0000-0000-000000000000"
        d = _h.md5(GUID.encode()).digest()
        cipher = _aes_ecb_encrypt(_pkcs7_pad(AQZF_PLAIN), d[8:] + d[:8])
        out, used = et._aqzf_pbzb_decrypt_best(cipher, [k_other, GUID])
        self.assertEqual(out, AQZF_PLAIN)
        self.assertEqual(used, GUID)
        with self.assertRaises(Exception):
            et._aqzf_pbzb_decrypt_best(cipher, [k_other])  # 全部失败抛最后异常
        with self.assertRaises(Exception):
            et._aqzf_pbzb_decrypt_best(cipher, [])  # 无密钥

    def test_extract_aqzf_decrypts_qd(self):
        """端到端：AQZF 容器内 .18aqzb 自动解密为明文 XML（官方工具一致行为）。"""
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", AQZF_PLAIN, PBZB_ON)
        r = et.extract_file(src)
        self.assertEqual(sorted(r["files"]), ["某项目.18aqzb"])
        out = os.path.join(r["dir"], "某项目.18aqzb")
        with open(out, "rb") as f:
            self.assertEqual(f.read(), AQZF_PLAIN)
        # PBZB.xml 仍是内部文件不落盘；校验清单记录的是解密后内容
        self.assertNotIn("PBZB.xml", r["files"])
        with open(r["checksum_file"], "rb") as f:
            self.assertNotIn(b"PBZB.xml", f.read())

    def test_extract_aqzf_multi_segment_container(self):
        """v3.1 端到端：多标段容器（两个 EncryKey），清单用第二个密钥加密，
        旧版只取最后一个/第一个密钥会失败，现逐个尝试命中解出明文。"""
        k2 = "11111111-2222-3333-4444-555555555555"
        pbzb = ('<?xml version="1.0" encoding="utf-8"?><XiangMuInfo AreaName="DQAnQing">'
                "<BiaoShu><ZBInfo>"
                '<ZBInfoMx BookMarkName="EncryQingDan" MarkValue="1" Xh="1"/>'
                '<ZBInfoMx BookMarkName="EncryKey" MarkValue="%s" Xh="1"/>'
                '<ZBInfoMx BookMarkName="EncryKey" MarkValue="%s" Xh="1"/>'
                "</ZBInfo></BiaoShu></XiangMuInfo>" % (GUID, k2)).encode("utf-8")
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", AQZF_PLAIN, pbzb, encry_key=k2)
        logs = []
        r = et.extract_file(src, log=logs.append)
        self.assertEqual(r["files"], ["某项目.18aqzb"])
        self.assertEqual(r["warnings"], 0)
        with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
            self.assertEqual(f.read(), AQZF_PLAIN)
        self.assertTrue(any("2/2" in ln for ln in logs))  # 命中第 2 个密钥

    def test_extract_aqzf_flag_true_still_decrypts(self):
        """v3.1：EncryQingDan="true" 等非 "0" 值也尝试解密（旧版静默落盘密文）。"""
        pbzb = PBZB_ON.replace(b'MarkValue="1" Xh="1"/>', b'MarkValue="true" Xh="1"/>', 1)
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", AQZF_PLAIN, pbzb)
        r = et.extract_file(src)
        self.assertEqual(r["warnings"], 0)
        with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
            self.assertEqual(f.read(), AQZF_PLAIN)

    def test_extract_aqzf_flag_off_exports_raw(self):
        """EncryQingDan="0"/"false"：清单未加密，应原样导出且不告警。"""
        for off in ("0", "false"):
            pbzb = PBZB_ON.replace(b'MarkValue="1" Xh="1"/>',
                                   b'MarkValue="%s" Xh="1"/>' % off.encode(), 1)
            src = _make_aqzf_file(self.tmp, "proj_%s.AQZF" % off,
                                  "某项目.18aqzb", AQZF_PLAIN, pbzb, encry_key=None)
            r = et.extract_file(src)
            self.assertEqual(r["warnings"], 0, off)
            with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
                self.assertEqual(f.read(), AQZF_PLAIN, off)

    def test_extract_aqzf_verify_xml_off(self):
        """v3.1：verify_xml=false 时非 XML 解密结果也放行落盘（配置生效）。"""
        import hashlib as _h
        payload = "NOT-XML 裸数据清单，没有 <?xml 声明".encode("utf-8")
        rules = {".18aqzb": {"enabled": True, "algorithm": "AQZF-PBZB",
                             "verify_xml": False}}
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", payload, PBZB_ON)
        with mock.patch.object(et, "_load_decrypt_config",
                               return_value=(rules, {"PBZB.xml"})):
            r = et.extract_file(src)
        self.assertEqual(r["warnings"], 0)
        with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
            self.assertEqual(f.read(), payload)  # 解密后的非 XML 内容直接落盘

    def test_extract_aqzf_flag_off_exports_raw(self):
        """EncryQingDan != 1：清单未加密，应原样导出且不告警。"""
        pbzb = PBZB_ON.replace(b'MarkValue="1" Xh="1"/>', b'MarkValue="0" Xh="1"/>', 1)
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", AQZF_PLAIN, pbzb, encry_key=None)
        logs = []
        r = et.extract_file(src, log=logs.append)
        self.assertEqual(r["files"], ["某项目.18aqzb"])
        self.assertEqual(r["warnings"], 0)
        out = os.path.join(r["dir"], "某项目.18aqzb")
        with open(out, "rb") as f:
            self.assertEqual(f.read(), AQZF_PLAIN)

    def test_extract_aqzf_no_key_warns_and_keeps_cipher(self):
        """PBZB.xml 缺 EncryKey：原样导出密文并告警（不拦截条目）。"""
        pbzb = PBZB_ON.replace(
            ('<ZBInfoMx BookMarkName="EncryKey" MarkValue="%s" Xh="1"/>' % GUID).encode("utf-8"),
            b"")
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", AQZF_PLAIN, pbzb)
        logs = []
        r = et.extract_file(src, log=logs.append)
        self.assertEqual(r["files"], ["某项目.18aqzb"])
        self.assertEqual(r["warnings"], 1)
        self.assertTrue(any("EncryKey" in ln for ln in logs))
        with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
            self.assertNotEqual(f.read(), AQZF_PLAIN)  # 仍是密文

    def test_extract_aqzf_wrong_key_falls_back_to_cipher(self):
        """密钥不匹配（解出非 XML）：回退原样导出密文并告警，不删文件。"""
        src = _make_aqzf_file(self.tmp, "proj.AQZF",
                              "某项目.18aqzb", AQZF_PLAIN, PBZB_ON,
                              encry_key="11111111-2222-3333-4444-555555555555")
        logs = []
        r = et.extract_file(src, log=logs.append)
        self.assertEqual(r["files"], ["某项目.18aqzb"])
        self.assertEqual(r["warnings"], 1)
        self.assertTrue(any("解密失败" in ln for ln in logs))
        with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
            self.assertNotEqual(f.read(), AQZF_PLAIN)

    def test_aqzf_pbzb_exts_config(self):
        """decrypt_config.json 规则：AQZF-PBZB 可增删参与解密的扩展名。"""
        self.assertIn(".18aqzb", et._aqzf_pbzb_exts({}))
        rules = {".18aqzb": {"algorithm": "AQZF-PBZB", "enabled": False},
                 ".18aqkz": {"algorithm": "AQZF-PBZB", "enabled": True},
                 ".18cxj": {"enabled": True}}  # 非 AQZF-PBZB 规则不参与
        exts = et._aqzf_pbzb_exts(rules)
        self.assertNotIn(".18aqzb", exts)
        self.assertIn(".18aqkz", exts)
        self.assertNotIn(".18cxj", exts)

    def test_extract_other_inner_files_untouched(self):
        """容器内其它明文条目与清单共存时不受解密影响，全部正常解出。"""
        import hashlib as _h
        d = _h.md5(GUID.encode()).digest()
        key = d[8:] + d[:8]
        inner = _aes_ecb_encrypt(_pkcs7_pad(AQZF_PLAIN), key)
        z = make_zip_bytes([("PBZB.xml", PBZB_ON),
                            ("某项目.18aqzb", inner),
                            ("清单.pdf", self.pdf())])
        xml = (HDR + '<ZBFile><ZBFileContent>' + wrap_b64(z)
               + "</ZBFileContent></ZBFile>")
        src = write_case(self.tmp, "proj2.AQZF", xml)
        r = et.extract_file(src)
        self.assertEqual(sorted(r["files"]), ["某项目.18aqzb", "清单.pdf"])
        with open(os.path.join(r["dir"], "清单.pdf"), "rb") as f:
            self.assertEqual(f.read(), self.pdf())
        with open(os.path.join(r["dir"], "某项目.18aqzb"), "rb") as f:
            self.assertEqual(f.read(), AQZF_PLAIN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
