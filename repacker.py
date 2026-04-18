import os
import zipfile
import sys
import re
import shutil
import subprocess

def clean_filename(filename):
    """去除非法字符 \\/:*?\"<>|，替换为 _"""
    return re.sub(r'[\\/:*?\"<>|]', '_', filename)

def get_unique_filename(base_name, suffix_template="_backup_{}"):
    """获取不冲突的唯一文件名"""
    counter = 1
    # 确保 base_name 不含 .llsp3
    name_without_ext = base_name[:-6] if base_name.lower().endswith(".llsp3") else base_name
    while True:
        new_name = f"{name_without_ext}{suffix_template.format(counter)}.llsp3"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

def list_subdirs(base_path):
    """获取 package-manager 下的一级子目录"""
    if not os.path.exists(base_path):
        print("错误：未找到 package-manager 目录，请先运行解压程序。")
        input("按回车键退出...")
        sys.exit(1)
    
    subdirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not subdirs:
        print("错误：package-manager 中没有可打包的子目录，请先运行解压程序。")
        input("按回车键退出...")
        sys.exit(1)
    
    return sorted(subdirs)

def preprocess_scratch(source_dir, subdir_name):
    """
    预处理：检查并压缩 scratch/ 文件夹为 scratch.sb3，然后删除原文件夹。
    """
    scratch_dir = os.path.join(source_dir, 'scratch')
    if not os.path.exists(scratch_dir) or not os.path.isdir(scratch_dir):
        # 如果不存在 scratch/ 文件夹，则不做任何处理
        return True, ""

    target_sb3 = os.path.join(source_dir, 'scratch.sb3')
    
    # 检查 scratch/ 是否为空
    with os.scandir(scratch_dir) as it:
        if not any(it):
            return False, f"预处理失败：{subdir_name}/scratch/ 目录为空"

    print(f"正在压缩 {subdir_name}/scratch/ -> {subdir_name}/scratch.sb3")
    try:
        # 压缩 scratch/ 文件夹下的所有内容，不包含 scratch/ 本身
        with zipfile.ZipFile(target_sb3, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(scratch_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, scratch_dir)
                    zipf.write(file_path, arcname)
        
        # 压缩成功后删除原文件夹
        shutil.rmtree(scratch_dir)
        print(f"已删除原始目录 {subdir_name}/scratch/")
        return True, ""
    except Exception as e:
        # 如果压缩过程中失败，记录错误日志
        if os.path.exists(target_sb3):
            try: os.remove(target_sb3)
            except: pass
        return False, f"预处理失败：无法压缩 {subdir_name}/scratch/，原因：{str(e)}"

def pack_subdir(subdir_name, base_path, overwrite_all):
    """打包单个子目录"""
    source_dir = os.path.join(base_path, subdir_name)
    
    # 1. 询问是否修改文件名
    print(f"\n--- 正在处理子目录: {subdir_name} ---")
    target_name_base = subdir_name
    while True:
        modify_name = input(f"是否要修改生成的 .llsp3 文件名？(y/n): ").lower().strip()
        if modify_name == 'y':
            new_name = input("请输入新文件名（不含 .llsp3 扩展名）: ").strip()
            if new_name:
                target_name_base = clean_filename(new_name)
            break
        elif modify_name == 'n' or modify_name == '':
            break
        else:
            print("无效输入，请输入 y 或 n。")
    
    target_file = f"{target_name_base}.llsp3"
    
    # 检查子目录是否为空
    with os.scandir(source_dir) as it:
        if not any(it):
            return False, "目录为空", overwrite_all, target_file

    # 冲突处理
    while os.path.exists(target_file):
        if overwrite_all:
            # 全部覆盖模式下直接跳过询问并覆盖
            break
            
        print(f"\n目标文件 {target_file} 已存在，如何处理？")
        print("[o] 覆盖 (Overwrite) - 用新文件替换已有文件")
        print("[r] 重命名已有文件 (Rename existing) - 将已存在的 .llsp3 文件改名，然后打包新文件为原名")
        print("[n] 重命名新文件 (Rename new) - 将即将打包的新文件另存为其他名称")
        print("[s] 跳过 (Skip) - 不打包此子目录，继续下一个")
        print("[a] 全部覆盖 (All overwrite) - 覆盖当前及后续所有冲突（不再询问）")
        print("[q] 退出 (Quit) - 终止整个程序")
        
        choice = input("请选择 (o/r/n/s/a/q): ").lower().strip()
        
        if choice == 'o':
            break
        elif choice == 'r':
            while True:
                new_old_name = input("请输入已存在文件的新名称（不含 .llsp3）: ").strip()
                if not new_old_name:
                    new_old_full = get_unique_filename(target_name_base, "_backup_{}")
                else:
                    new_old_full = f"{clean_filename(new_old_name)}.llsp3"
                
                if os.path.exists(new_old_full):
                    confirm = input(f"文件名 {new_old_full} 已存在，是否覆盖？(y/n): ").lower().strip()
                    if confirm == 'y':
                        os.remove(new_old_full)
                    else:
                        continue
                
                os.rename(target_file, new_old_full)
                print(f"已将已存在的文件 {target_file} 重命名为 {new_old_full}")
                break
            # 重命名后，target_file 已经不存在了，循环会结束并进行打包
        elif choice == 'n':
            while True:
                new_new_name = input("请输入新文件要保存的名称（不含 .llsp3）: ").strip()
                if not new_new_name:
                    target_file = get_unique_filename(target_name_base, "_new_{}")
                else:
                    target_file = f"{clean_filename(new_new_name)}.llsp3"
                
                if os.path.exists(target_file):
                    confirm = input(f"文件名 {target_file} 已存在，是否覆盖？(y/n): ").lower().strip()
                    if confirm == 'y':
                        # 准备覆盖这个新指定的文件，跳出内层循环，外层循环通过 break 离开
                        break
                    else:
                        continue
                else:
                    break
            # 无论是因为不重名还是选择覆盖，target_file 已确定，跳出冲突循环
            break
        elif choice == 's':
            return None, "用户选择跳过", overwrite_all, target_file
        elif choice == 'a':
            overwrite_all = True
            break
        elif choice == 'q':
            print("用户终止。")
            sys.exit(0)
        else:
            print("无效选择，请重新输入。")

    # --- 开始预处理与打包 ---
    # 3. 预处理：压缩 scratch/ 文件夹为 scratch.sb3，删除原文件夹
    preprocess_success, error_msg = preprocess_scratch(source_dir, subdir_name)
    if not preprocess_success:
        return False, error_msg, overwrite_all, target_file

    # 4. 打包子目录内容到 .llsp3
    print(f"正在打包 {subdir_name}/ -> {target_file}")
    try:
        # 如果是覆盖操作，ZipFile 'w' 模式会自动覆盖
        with zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
        return True, "打包成功", overwrite_all, target_file
    except Exception as e:
        return False, str(e), overwrite_all, target_file

def main():
    base_path = './package-manager'
    subdirs = list_subdirs(base_path)

    print("可打包的子目录列表：")
    for i, d in enumerate(subdirs, 1):
        print(f"{i}. {d}")

    selected_indices = []
    while True:
        user_input = input("\n请输入要打包的目录编号 (例如: 1,3,5 或 1 3 5 或 all): ").strip().lower()
        if user_input == 'all':
            selected_indices = list(range(len(subdirs)))
            break
        
        try:
            # 支持逗号或空格分隔
            parts = user_input.replace(',', ' ').split()
            indices = [int(p) - 1 for p in parts]
            if all(0 <= i < len(subdirs) for i in indices):
                selected_indices = indices
                break
            else:
                print("错误：编号超出范围，请重新输入。")
        except ValueError:
            print("错误：输入格式无效，请输入数字或 all。")

    success_list = []
    failure_list = []
    overwrite_all = False

    for idx in selected_indices:
        subdir = subdirs[idx]
        result, info, overwrite_all, target_file = pack_subdir(subdir, base_path, overwrite_all)
        
        if result is True:
            success_list.append(target_file)
            print(f"成功打包: {target_file}")
        elif result is None:
            print(f"跳过 {subdir}/（{info}）")
        else:
            failure_list.append(f"{subdir}/ - 原因：{info}")
            print(f"打包失败: {subdir}/ - 原因：{info}")

    print("\n========== 打包完成 ==========")
    if success_list:
        print(f"成功打包: {', '.join(success_list)}")
    if failure_list:
        for fail in failure_list:
            print(f"失败: {fail}")
    print("==============================")

    print()
    clear_choice = input("是否清除 SPIKE 缓存？（这将删除 SPIKE3 缓存目录、预读文件及文档文件夹，建议在打包后执行）(y/n): ").lower().strip()
    if clear_choice == 'y':
        clear_script = "clear_spike_cache.py"
        if os.path.exists(clear_script):
            print("正在调用清理脚本...")
            # 使用 sys.executable 确保使用相同的 Python 解释器运行
            subprocess.run([sys.executable, clear_script, "--silent"], check=False)
            print("缓存清理已执行，详情请查看控制台输出。")
        else:
            print(f"错误：未找到清理脚本，请确保 {clear_script} 存在于当前目录。")
    
    input("\n打包程序运行结束，按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已被用户终止。")
        sys.exit(0)
