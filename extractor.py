import os
import sys
import shutil
import zipfile
import re

def is_valid_dir_name(name):
    """
    检查目录名是否合法：
    - 不能为空
    - 不能包含路径分隔符 (/ \\)
    - 不能包含 Windows 非法字符 (\\/:*?"<>|)
    - 不能是 . 或 ..
    """
    if not name or name.strip() == "":
        return False, "名称不能为空，请重新输入："
    if name in ('.', '..'):
        return False, "名称不能为 . 或 ..，请重新输入："
    if re.search(r'[\\/:*?\"<>|]', name):
        return False, "名称包含非法字符 (\\/:*?\"<>|)，请重新输入："
    return True, ""

def extract_sb3_logic(target_dir, pkg_name):
    """
    处理 target_dir 下的 scratch.sb3 文件。
    如果存在，将其解压到 scratch/ 目录并删除原始 .sb3 文件。
    """
    # 查找所有 .sb3 文件
    try:
        sb3_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.sb3')]
    except Exception as e:
        return False, f"读取目录 {target_dir} 失败: {str(e)}"
    
    if not sb3_files:
        err = f"{pkg_name}/ 目录下未找到 scratch.sb3 文件"
        # 用户要求保持原有风格，这里稍微调整提示，因为 pkg_name 可能是重命名后的
        print(f"  [错误] {err}")
        return False, err
    
    if len(sb3_files) > 1:
        err = f"{pkg_name}/ 目录下找到多个 .sb3 文件：{', '.join(sb3_files)}"
        print(f"  [错误] {err}")
        return False, err

    sb3_filename = 'scratch.sb3'
    sb3_path = os.path.join(target_dir, sb3_filename)
    
    if not os.path.exists(sb3_path):
        err = f"{pkg_name}/ 目录下未找到精确命名的 scratch.sb3 文件"
        print(f"  [错误] {err}")
        return False, err

    scratch_dir = os.path.join(target_dir, 'scratch')
    print(f"  解压 {pkg_name}/{sb3_filename} -> {pkg_name}/scratch/")
    
    try:
        # 如果 scratch/ 目录已存在，一律采用覆盖模式（删除已有 scratch/ 再解压）
        if os.path.exists(scratch_dir):
            shutil.rmtree(scratch_dir)
        os.makedirs(scratch_dir)
        
        with zipfile.ZipFile(sb3_path, 'r') as zip_ref:
            zip_ref.extractall(scratch_dir)
            
        # 解压完成后删除原始 .sb3
        os.remove(sb3_path)
        print(f"  删除原始文件 {pkg_name}/{sb3_filename}")
        return True, ""
    except Exception as e:
        err = f"处理 {pkg_name}/{sb3_filename} 失败：{str(e)}"
        print(f"  [错误] {err}")
        return False, err

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2.1 扫描所有 .llsp3 文件
    llsp3_files = [f for f in os.listdir(base_dir) 
                   if f.lower().endswith('.llsp3') and os.path.isfile(os.path.join(base_dir, f))]
    
    if not llsp3_files:
        print("当前目录下未找到任何 .llsp3 文件。")
        input("按回车键退出...")
        return

    # 2.2 预检查与用户确认
    print(f"即将解压 {len(llsp3_files)} 个 .llsp3 文件，是否继续？(y/n)")
    confirm = input().strip().lower()
    if confirm != 'y' and confirm != '':
        return

    pkg_mgr_dir = os.path.join(base_dir, 'package-manager')
    if not os.path.exists(pkg_mgr_dir):
        os.makedirs(pkg_mgr_dir)
    
    overwrite_all = False
    
    success_list = []
    skip_list = []
    fail_list = []

    # 2.3 逐个文件处理
    for file in llsp3_files:
        file_path = os.path.join(base_dir, file)
        pkg_name = os.path.splitext(file)[0]
        default_target_dir = os.path.join(pkg_mgr_dir, pkg_name)
        
        # 实际使用的解压目录
        target_dir = default_target_dir
        actual_pkg_name = pkg_name
        choice = None  # 初始化用户选择

        # 检查目标目录是否存在且非空
        is_conflict = os.path.exists(target_dir) and os.listdir(target_dir)
        
        if is_conflict and not overwrite_all:
            print(f"\n目标目录 ./package-manager/{pkg_name}/ 已存在，如何处理？")
            print("[o] 覆盖 (Overwrite) - 删除现有目录，重新解压")
            print("[r] 重命名已有目录 (Rename existing) - 将已存在的目录改名，然后解压新目录为原名")
            print("[n] 重命名新目录 (Rename new) - 将即将解压的新目录另存为其他名称")
            print("[s] 跳过 (Skip) - 不解压此文件，继续下一个")
            print("[a] 全部覆盖 (All overwrite) - 覆盖当前及后续所有冲突（不再询问）")
            print("[q] 退出 (Quit) - 终止整个程序")
            
            while True:
                choice = input("请选择 (o/r/n/s/a/q): ").strip().lower()
                
                if choice == 'o':
                    print(f"覆盖已存在的目录 ./package-manager/{pkg_name}/")
                    try:
                        shutil.rmtree(target_dir)
                    except Exception as e:
                        print(f"解压 {file} 失败：无法删除现有目录 ({str(e)})")
                        fail_list.append(f"{file}（无法删除现有目录）")
                        target_dir = None
                    break
                elif choice == 'r':
                    prompt = "请输入已存在目录的新名称（仅目录名，不含路径）: "
                    while True:
                        new_old_name = input(prompt).strip()
                        valid, err = is_valid_dir_name(new_old_name)
                        if not valid:
                            prompt = err
                            continue
                        
                        new_old_path = os.path.join(pkg_mgr_dir, new_old_name)
                        if os.path.exists(new_old_path):
                            prompt = "该名称已存在，请重新输入："
                            continue
                        
                        try:
                            os.rename(target_dir, new_old_path)
                            print(f"已将已存在的目录 {pkg_name}/ 重命名为 {new_old_name}/")
                            print(f"正在解压 {file} -> ./package-manager/{pkg_name}/")
                            break
                        except Exception as e:
                            print(f"重命名目录失败: {str(e)}")
                            fail_list.append(f"{file}（重命名失败）")
                            target_dir = None
                            break
                    break
                elif choice == 'n':
                    prompt = "请输入新目录要使用的名称（仅目录名，不含路径）: "
                    while True:
                        new_name = input(prompt).strip()
                        valid, err = is_valid_dir_name(new_name)
                        if not valid:
                            prompt = err
                            continue
                        
                        new_path = os.path.join(pkg_mgr_dir, new_name)
                        if os.path.exists(new_path):
                            prompt = "该名称已存在，请重新输入："
                            continue
                        
                        target_dir = new_path
                        actual_pkg_name = new_name
                        print(f"正在解压 {file} -> ./package-manager/{new_name}/")
                        break
                    break
                elif choice == 's':
                    print(f"跳过 {file}（用户选择跳过）")
                    skip_list.append(f"{file}（用户选择跳过）")
                    target_dir = None
                    break
                elif choice == 'a':
                    overwrite_all = True
                    print(f"覆盖已存在的目录 ./package-manager/{pkg_name}/")
                    try:
                        if target_dir is not None:
                            shutil.rmtree(target_dir)
                    except Exception as e:
                        print(f"解压 {file} 失败：无法删除现有目录 ({str(e)})")
                        fail_list.append(f"{file}（无法删除现有目录）")
                        target_dir = None
                    break
                elif choice == 'q':
                    print("用户终止")
                    return
                else:
                    print("无效输入，请重新输入。")
        elif is_conflict and overwrite_all:
            print(f"覆盖已存在的目录 ./package-manager/{pkg_name}/")
            if target_dir is not None:
                try:
                    shutil.rmtree(target_dir)
                except Exception as e:
                    print(f"解压 {file} 失败：无法删除现有目录 ({str(e)})")
                    fail_list.append(f"{file}（无法删除现有目录）")
                    target_dir = None

        if target_dir is None:
            continue

        # 开始解压
        # 只有在非冲突场景，或冲突但选择覆盖（o/a）场景下，才打印标准解压日志
        # 重命名场景（r/n）在上面的逻辑中已经打印过详细的“正在解压...”日志了
        if not (is_conflict and choice in ('r', 'n')):
            print(f"正在解压 {file} -> ./package-manager/{actual_pkg_name}/")
        
        try:
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # 处理 scratch.sb3
            sb3_success, sb3_err = extract_sb3_logic(target_dir, actual_pkg_name)
            
            if sb3_success:
                success_list.append(file)
            else:
                # 即使 sb3 失败，主文件也解压了，但按原有逻辑列为失败
                fail_list.append(f"{file}（{sb3_err}）")
        except Exception as e:
            print(f"解压 {file} 失败：{str(e)}")
            fail_list.append(f"{file}（{str(e)}）")
            continue

    # 4. 汇总结果
    print("\n========== 解压完成 ==========")
    if success_list:
        print(f"成功解压: {', '.join(success_list)}")
    if skip_list:
        for s in skip_list:
            print(f"跳过: {s}")
    if fail_list:
        for f in fail_list:
            print(f"失败: {f}")
    print("===============================")
    
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户强制终止。")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        input("按回车键退出...")
        sys.exit(1)
