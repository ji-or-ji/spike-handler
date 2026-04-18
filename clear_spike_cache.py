import os
import shutil
import glob
import sys
import ctypes
import argparse

def is_admin():
    """检测当前是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    """尝试以管理员身份重新运行脚本"""
    # 构造重新运行的参数，添加 --elevated 标志避免死循环
    # 使用 sys.argv[1:] 获取除脚本名外的所有参数
    args = sys.argv[1:]
    if "--elevated" not in args:
        args.append("--elevated")
    
    params = " ".join([f'"{arg}"' for arg in args])
    
    # ShellExecuteW 使用 "runas" 谓词触发 UAC 提权
    # sys.executable 是 python.exe，sys.argv[0] 是脚本路径
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{sys.argv[0]}" {params}', None, 1
    )
    
    # 返回值大于 32 表示成功启动
    return int(ret) > 32

def clear_cache(silent=False):
    """执行清理逻辑"""
    username = os.getenv("USERNAME")
    # 动态获取路径
    appdata_path = os.path.join(os.environ.get('APPDATA', f'C:\\Users\\{username}\\AppData\\Roaming'), "SPIKE3")
    documents_path = os.path.join(os.environ.get('USERPROFILE', f'C:\\Users\\{username}'), "Documents", "LEGO Education SPIKE")
    prefetch_pattern = r"C:\Windows\Prefetch\SPIKE-*"

    if not silent:
        print(f"即将永久删除以下路径：")
        print(f"1. {appdata_path}\\")
        print(f"2. {prefetch_pattern}")
        print(f"3. {documents_path}")
        confirm = input("\n是否继续？(y/n): ").lower().strip()
        if confirm != 'y':
            print("操作已取消。")
            return

    success_items = []
    failed_items = []

    # 处理目录路径 (1 和 3)
    for path in [appdata_path, documents_path]:
        if not os.path.exists(path):
            print(f"目录不存在，跳过: {path}")
            continue
        
        print(f"正在删除目录: {path}")
        try:
            shutil.rmtree(path)
            success_items.append(path)
            print(f"成功删除: {path}")
        except Exception as e:
            failed_items.append((path, str(e)))
            print(f"删除失败: {path}, 原因: {e}")

    # 处理通配符文件 (2)
    print(f"正在匹配预读文件: {prefetch_pattern}")
    prefetch_files = glob.glob(prefetch_pattern)
    if not prefetch_files:
        print("未找到匹配的预读文件，跳过。")
    else:
        for f in prefetch_files:
            try:
                os.remove(f)
                success_items.append(f)
                print(f"成功删除文件: {f}")
            except Exception as e:
                failed_items.append((f, str(e)))
                print(f"删除失败: {f}, 原因: {e}")

    # 输出汇总
    print("\n========== 清理汇总 ==========")
    if success_items:
        print(f"成功清理项数: {len(success_items)}")
    if failed_items:
        print(f"失败项数: {len(failed_items)}")
        for item, err in failed_items:
            print(f"  - {item}: {err}")
    if not success_items and not failed_items:
        print("未发现需要清理的内容。")
    print("==============================")

def main():
    parser = argparse.ArgumentParser(description="SPIKE 缓存清理工具")
    parser.add_argument("--silent", "-s", action="store_true", help="静默模式，不显示确认对话框")
    parser.add_argument("--elevated", action="store_true", help="提权标志，请勿手动指定")
    args = parser.parse_args()

    # 权限检查与提权
    if not is_admin():
        if args.elevated:
            # 如果已经尝试过提权但还是没权限，说明失败了
            print("错误：无法获取管理员权限。请右键点击脚本并选择“以管理员身份运行”。")
            if not args.silent:
                input("按回车键退出...")
            sys.exit(1)
        
        print("正在尝试获取管理员权限以清理系统目录...")
        if elevate():
            sys.exit(0) # 提权后的新进程已启动，当前进程退出
        else:
            print("错误：管理员权限请求被拒绝。")
            if not args.silent:
                input("按回车键退出...")
            sys.exit(1)

    # 执行清理
    clear_cache(silent=args.silent)
    
    # 交互模式下等待退出
    if not args.silent:
        input("\n所有操作已完成，按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已被用户终止。")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序运行发生异常: {e}")
        input("按回车键退出...")
        sys.exit(1)
