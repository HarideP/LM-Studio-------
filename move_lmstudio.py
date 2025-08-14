import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import threading
import contextlib
import argparse

try:
	import tkinter as tk
	from tkinter import ttk, filedialog, messagebox
	from tkinter.scrolledtext import ScrolledText
except Exception:
	tk = None


def is_admin() -> bool:

	try:
		import ctypes  # noqa: WPS433 - windows admin check
		return bool(ctypes.windll.shell32.IsUserAnAdmin())
	except Exception:
		return False


def detect_lmstudio_processes() -> list[str]:

	try:
		completed = subprocess.run(["tasklist"], capture_output=True, text=True, shell=True)
		output = completed.stdout or ""
		matches: list[str] = []
		for line in output.splitlines():
			lower = line.lower()
			if "lmstudio" in lower or "lm studio" in lower:
				matches.append(line)
		return matches
	except Exception:
		return []


def format_bytes(num_bytes: int) -> str:

	units = ["B", "KB", "MB", "GB", "TB"]
	amount = float(num_bytes)
	for unit in units:
		if amount < 1024.0:
			return f"{amount:.2f} {unit}"
		amount /= 1024.0
	return f"{amount:.2f} PB"


def walk_dir_size(directory: Path) -> int:

	total_size = 0
	for root, dirs, files in os.walk(directory, topdown=True):
		for file_name in files:
			file_path = Path(root) / file_name
			try:
				total_size += file_path.stat().st_size
			except OSError:
				pass
	return total_size


def collect_dir_info(path: Path) -> dict:

	info = {
		"exists": path.exists(),
		"is_dir": path.is_dir(),
		"file_count": 0,
		"dir_count": 0,
		"total_size": 0,
		"is_empty": True,
	}

	if info["exists"] and info["is_dir"]:
		file_count = 0
		dir_count = 0
		for _, dirs, files in os.walk(path, topdown=True):
			dir_count += len(dirs)
			file_count += len(files)
		info["file_count"] = file_count
		info["dir_count"] = dir_count
		info["is_empty"] = (file_count == 0 and dir_count == 0)
		info["total_size"] = walk_dir_size(path)

	return info


def print_dir_info(title: str, path: Path, info: dict) -> None:

	print(f"\n=== {title} ===")
	print(f"路径: {path}")
	if not info["exists"]:
		print("状态: 不存在")
		return
	print("类型: 目录" if info["is_dir"] else "类型: 非目录(请检查)")
	print(f"文件数: {info['file_count']} | 子目录数: {info['dir_count']}")
	print(f"总大小: {format_bytes(info['total_size'])}")
	print("是否为空: 是" if info["is_empty"] else "是否为空: 否")


def ask_yes_no(prompt: str, default: str | None = None) -> bool:

	default_hint = " [Y/n]" if default in (None, "y", "Y") else " [y/N]"
	while True:
		answer = input(f"{prompt}{default_hint}: ").strip().lower()
		if not answer and default is not None:
			return default.lower() == "y"
		if answer in ("y", "yes", "是", "好", "确认"):
			return True
		if answer in ("n", "no", "否", "不", "取消"):
			return False
		print("请输入 y 或 n。")


def prompt_for_path(prompt: str, default: Path | None = None) -> Path:

	while True:
		default_str = f" (回车使用默认: {default})" if default else ""
		text = input(f"{prompt}{default_str}: ").strip()
		if not text and default is not None:
			return default
		candidate = Path(text).expanduser().resolve()
		if str(candidate):
			return candidate
		print("路径无效，请重试。")


def ensure_directory(path: Path) -> None:

	path.mkdir(parents=True, exist_ok=True)


def run_robocopy(source: Path, target: Path) -> bool:

	cmd = [
		"robocopy",
		str(source),
		str(target),
		"/E",
		"/COPYALL",
		"/R:1",
		"/W:1",
	]
	print("\n正在复制(robocopy)...")
	print("命令:", " ".join(cmd))
	try:
		completed = subprocess.run(cmd, capture_output=True, text=True, shell=False)
		print(completed.stdout)
		if completed.returncode <= 7:
			print("复制成功。")
			return True
		print("复制失败，返回码:", completed.returncode)
		print(completed.stderr)
		return False
	except FileNotFoundError:
		print("未找到 robocopy，将使用 Python 复制。")
		return False


def copy_directory(source: Path, target: Path) -> None:

	ensure_directory(target)
	used_robocopy = run_robocopy(source, target)
	if used_robocopy:
		return
	print("\n正在复制(Python shutil)... 这可能较慢。")
	for root, dirs, files in os.walk(source):
		rel_root = os.path.relpath(root, source)
		dest_root = target / rel_root if rel_root != "." else target
		ensure_directory(dest_root)
		for file_name in files:
			from_path = Path(root) / file_name
			to_path = dest_root / file_name
			if not to_path.exists():
				shutil.copy2(from_path, to_path)


def delete_directory(path: Path) -> None:

	if not path.exists():
		return
	print(f"\n正在删除源目录: {path}")
	shutil.rmtree(path, ignore_errors=False)


def create_junction(link_path: Path, target_path: Path) -> None:

	if link_path.exists() or link_path.is_symlink():
		raise RuntimeError(f"链接位置已存在: {link_path}")
	print(f"\n正在创建目录联接(Junction): {link_path} -> {target_path}")
	cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)]
	completed = subprocess.run(cmd, capture_output=True, text=True, shell=True)
	if completed.returncode != 0:
		stderr = (completed.stderr or "").strip()
		stdout = (completed.stdout or "").strip()
		raise RuntimeError(f"创建联接失败。\nSTDOUT: {stdout}\nSTDERR: {stderr}")
	print("联接创建成功。")


def ensure_windows() -> None:

	if platform.system().lower() != "windows":
		raise SystemExit("此工具仅支持 Windows。")


def run_cli() -> None:

	ensure_windows()
	print("LM Studio 目录迁移与联接工具")
	print("- 复制源目录到目标位置\n- 删除源目录\n- 创建目录联接(Junction) 指向目标\n")

	default_source = (Path.home() / ".lmstudio").resolve()
	default_target = Path("D:/LMstudio_AIModels").resolve()

	# 选择源目录
	source_dir = prompt_for_path("请输入源目录", default_source)
	source_info = collect_dir_info(source_dir)
	print_dir_info("源目录信息", source_dir, source_info)

	if not source_info["exists"]:
		if ask_yes_no("源目录不存在，是否创建并继续?", default="y"):
			ensure_directory(source_dir)
			source_info = collect_dir_info(source_dir)
			print_dir_info("源目录信息(已创建)", source_dir, source_info)
		else:
			print("已取消。")
			return

	if source_info["exists"] and source_info["is_dir"] and source_info["is_empty"]:
		if not ask_yes_no("源目录为空，是否继续?", default="n"):
			print("已取消。")
			return

	# 选择目标目录
	while True:
		target_dir = prompt_for_path("请输入目标目录", default_target)
		target_info = collect_dir_info(target_dir)
		print_dir_info("目标目录信息", target_dir, target_info)

		if target_info["exists"]:
			print("\n检测到目标目录已存在。可选操作:")
			print("1) 重新输入目标目录")
			print("2) 删除目标后复制 (覆盖)")
			print("3) 跳过复制，仅删除源并把源创建为指向现有目标的联接")
			print("4) 退出")
			choice = input("请选择 [1-4]: ").strip()
			if choice == "1":
				continue
			elif choice == "2":
				if not ask_yes_no("确认删除现有目标并覆盖? 此操作不可恢复!", default="n"):
					continue
				print(f"\n正在删除现有目标: {target_dir}")
				shutil.rmtree(target_dir, ignore_errors=False)
				break
			elif choice == "3":
				if not ask_yes_no("确认跳过复制，仅联接到现有目标?", default="n"):
					continue
				# 仅联接: 删除源 -> 在源位置创建联接到现有目标
				if source_dir.exists():
					delete_directory(source_dir)
				create_junction(source_dir, target_dir)
				print("操作完成。")
				return
			elif choice == "4":
				print("已取消。")
				return
			else:
				print("无效选择，请重试。")
				continue
		else:
			# 目标不存在时，正常流程
			break

	# 开始执行前提示：管理员权限与 LM Studio 关闭
	admin_ok = is_admin()
	procs = detect_lmstudio_processes()
	print("\n开始前确认:")
	print(f"- 管理员运行: {'是' if admin_ok else '否'}")
	print(f"- 运行中的 LM Studio 进程: {len(procs)} 个")
	if procs:
		print("示例进程(最多列出5条):")
		for line in procs[:5]:
			print("  ", line)
	if not ask_yes_no("请确认已以管理员身份运行并完全关闭 LM Studio，继续?", default="n"):
		print("已取消。")
		return

	# 执行复制
	try:
		copy_directory(source_dir, target_dir)
	except Exception as exc:
		print(f"复制过程中发生错误: {exc}")
		return

	# 删除源目录
	try:
		delete_directory(source_dir)
	except Exception as exc:
		print(f"删除源目录失败: {exc}")
		print("为避免数据损坏，未创建联接。请手动检查后重试。")
		return

	# 创建目录联接
	try:
		create_junction(source_dir, target_dir)
	except Exception as exc:
		print(f"创建目录联接失败: {exc}")
		print("请以管理员身份运行终端，或开启 Windows 开发者模式 再重试。")
		return

	# 验证
	if source_dir.exists() and source_dir.is_dir():
		print("\n验证: 联接已存在。现在源路径将指向目标目录。")
	else:
		print("\n警告: 未能验证联接存在，请手动检查。")

	print("\n操作完成！")


class GuiWriter:

	def __init__(self, callback):
		self._callback = callback

	def write(self, data: str) -> None:
		if not data:
			return
		self._callback(str(data))

	def flush(self) -> None:
		pass


class MoveApp(tk.Tk):

	def __init__(self) -> None:
		super().__init__()
		self.title("LM Studio 迁移与联接工具")
		self.geometry("780x560")

		self.source_var = tk.StringVar()
		self.target_var = tk.StringVar()
		self.overwrite_var = tk.BooleanVar(value=False)
		self.link_only_var = tk.BooleanVar(value=False)

		self._build_ui()
		self._running = False

	def _build_ui(self) -> None:

		pad = {"padx": 8, "pady": 6}

		frm_paths = ttk.LabelFrame(self, text="路径设置")
		frm_paths.pack(fill=tk.X, **pad)

		# Source
		row1 = ttk.Frame(frm_paths)
		row1.pack(fill=tk.X, padx=8, pady=6)
		ttk.Label(row1, text="源目录:", width=10).pack(side=tk.LEFT)
		self.ent_source = ttk.Entry(row1, textvariable=self.source_var)
		self.ent_source.pack(side=tk.LEFT, fill=tk.X, expand=True)
		ttk.Button(row1, text="浏览...", command=self._browse_source).pack(side=tk.LEFT, padx=6)

		# Target
		row2 = ttk.Frame(frm_paths)
		row2.pack(fill=tk.X, padx=8, pady=6)
		ttk.Label(row2, text="目标目录:", width=10).pack(side=tk.LEFT)
		self.ent_target = ttk.Entry(row2, textvariable=self.target_var)
		self.ent_target.pack(side=tk.LEFT, fill=tk.X, expand=True)
		ttk.Button(row2, text="浏览...", command=self._browse_target).pack(side=tk.LEFT, padx=6)

		# Options
		frm_opts = ttk.LabelFrame(self, text="选项")
		frm_opts.pack(fill=tk.X, **pad)
		chk_over = ttk.Checkbutton(frm_opts, text="若目标已存在则删除并覆盖复制", variable=self.overwrite_var, command=self._sync_option_states)
		chk_over.pack(anchor=tk.W, padx=8, pady=2)
		chk_link = ttk.Checkbutton(frm_opts, text="跳过复制，仅在源位置创建指向目标的目录联接", variable=self.link_only_var, command=self._sync_option_states)
		chk_link.pack(anchor=tk.W, padx=8, pady=2)

		# Actions
		frm_actions = ttk.Frame(self)
		frm_actions.pack(fill=tk.X, **pad)
		ttk.Button(frm_actions, text="查看目录信息", command=self._show_info).pack(side=tk.LEFT)
		self.btn_start = ttk.Button(frm_actions, text="开始执行", command=self._start)
		self.btn_start.pack(side=tk.LEFT, padx=8)
		ttk.Button(frm_actions, text="清空日志", command=self._clear_log).pack(side=tk.LEFT)

		# Log
		frm_log = ttk.LabelFrame(self, text="日志")
		frm_log.pack(fill=tk.BOTH, expand=True, **pad)
		self.txt_log = ScrolledText(frm_log, height=18)
		self.txt_log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

	def _sync_option_states(self) -> None:

		# 互斥: 选择仅联接时，忽略覆盖；取消仅联接时，恢复可选
		if self.link_only_var.get():
			self.overwrite_var.set(False)
			self.ent_target.state(["!disabled"])  # 目标仍需可编辑
		else:
			pass

	def _append_log(self, text: str) -> None:

		def _do_insert() -> None:
			self.txt_log.insert(tk.END, text)
			self.txt_log.see(tk.END)
		self.after(0, _do_insert)

	def _clear_log(self) -> None:

		self.txt_log.delete("1.0", tk.END)

	def _browse_source(self) -> None:

		path = filedialog.askdirectory(title="选择源目录")
		if path:
			self.source_var.set(path)

	def _browse_target(self) -> None:

		path = filedialog.askdirectory(title="选择目标目录")
		if path:
			self.target_var.set(path)

	def _format_info(self, title: str, p: Path, info: dict) -> str:

		lines = [f"\n=== {title} ===", f"路径: {p}"]
		if not info["exists"]:
			lines.append("状态: 不存在")
			return "\n".join(lines) + "\n"
		lines.append("类型: 目录" if info["is_dir"] else "类型: 非目录(请检查)")
		lines.append(f"文件数: {info['file_count']} | 子目录数: {info['dir_count']}")
		lines.append(f"总大小: {format_bytes(info['total_size'])}")
		lines.append("是否为空: 是" if info["is_empty"] else "是否为空: 否")
		return "\n".join(lines) + "\n"

	def _show_info(self) -> None:

		source = Path(self.source_var.get()).expanduser().resolve()
		target = Path(self.target_var.get()).expanduser().resolve()
		si = collect_dir_info(source)
		ti = collect_dir_info(target)
		self._append_log(self._format_info("源目录信息", source, si))
		self._append_log(self._format_info("目标目录信息", target, ti))

	def _set_running(self, running: bool) -> None:

		self._running = running
		state = ("disabled" if running else "!disabled")
		for w in (self.ent_source, self.ent_target, self.btn_start):
			try:
				w.state([state])
			except Exception:
				w.configure(state=("disabled" if running else "normal"))

	def _start(self) -> None:

		ensure_windows()
		source = Path(self.source_var.get()).expanduser().resolve()
		target = Path(self.target_var.get()).expanduser().resolve()
		link_only = self.link_only_var.get()
		overwrite = self.overwrite_var.get()

		if not str(source):
			messagebox.showerror("错误", "请填写源目录")
			return
		if not str(target):
			messagebox.showerror("错误", "请填写目标目录")
			return

		si = collect_dir_info(source)
		ti = collect_dir_info(target)

		# 源目录存在性与空目录确认
		if not si["exists"]:
			if not messagebox.askyesno("确认", "源目录不存在，是否创建并继续？"):
				return
			try:
				ensure_directory(source)
			except Exception as exc:
				messagebox.showerror("错误", f"创建源目录失败: {exc}")
				return
			# 刷新信息
			si = collect_dir_info(source)

		if si["is_dir"] and si["is_empty"]:
			if not messagebox.askyesno("确认", "源目录为空，是否继续？"):
				return

		# 目标存在处理
		if not link_only:
			if ti["exists"]:
				if overwrite:
					if not messagebox.askyesno("危险操作确认", "将删除现有目标并覆盖复制，是否继续？"):
						return
				else:
					messagebox.showwarning("已存在", "目标目录已存在。请勾选覆盖，或选择其他目标路径。")
					return

		# 开始执行前提示：管理员权限与 LM Studio 关闭
		admin_ok = is_admin()
		procs = detect_lmstudio_processes()
		msg = [
			"即将开始迁移。请确认：",
			"1) 以管理员身份运行程序",
			"2) 已完全关闭 LM Studio",
			"",
			f"检测结果 - 管理员: {'是' if admin_ok else '否'}",
			f"检测结果 - 运行中的 LM Studio 进程: {len(procs)} 个",
		]
		if procs:
			msg.append("")
			msg.extend(["示例进程："] + procs[:5])
		if not messagebox.askyesno("开始前确认", "\n".join(msg)):
			return

		self._set_running(True)

		def worker() -> None:
			try:
				with contextlib.redirect_stdout(GuiWriter(self._append_log)), contextlib.redirect_stderr(GuiWriter(self._append_log)):
					if link_only:
						if source.exists():
							delete_directory(source)
						create_junction(source, target)
						print("操作完成。\n")
						return

					# 覆盖时先删除目标
					if overwrite and target.exists():
						print(f"\n正在删除现有目标: {target}")
						shutil.rmtree(target, ignore_errors=False)

					copy_directory(source, target)
					delete_directory(source)
					create_junction(source, target)
					print("\n操作完成！\n")
			finally:
				self._set_running(False)

		threading.Thread(target=worker, daemon=True).start()


def run_gui() -> None:

	ensure_windows()
	if tk is None:
		raise SystemExit("未检测到 Tkinter，无法启动图形界面。")
	app = MoveApp()
	app.source_var.set(str((Path.home() / ".lmstudio").resolve()))
	app.target_var.set(str(Path("D:/LMstudio_AIModels").resolve()))
	app.mainloop()


if __name__ == "__main__":

	try:
		parser = argparse.ArgumentParser(description="LM Studio 目录迁移与联接工具")
		parser.add_argument("--cli", action="store_true", help="使用命令行模式")
		parser.add_argument("--gui", action="store_true", help="使用图形界面模式")
		args = parser.parse_args()
		if args.cli:
			run_cli()
		else:
			run_gui()
	except KeyboardInterrupt:
		print("\n已取消。")

