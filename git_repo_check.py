#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Git 仓库状态检测与配置脚本
功能：检测脚本所在目录的 Git 仓库状态，并根据状态执行相应配置操作
"""

import os
import subprocess
import shutil
import sys


def run_git_command(cmd_args, capture_output=True):
    """
    执行 Git 命令并处理错误
    
    Args:
        cmd_args: Git 命令参数列表
        capture_output: 是否捕获输出
    
    Returns:
        tuple: (success, output, error_message)
    """
    try:
        result = subprocess.run(
            cmd_args,
            capture_output=capture_output,
            text=True,
            check=False,
            shell=True
        )
        
        if result.returncode == 0:
            output = result.stdout.strip() if capture_output else ""
            return True, output, ""
        else:
            error_msg = result.stderr.strip() if result.stderr else f"命令执行失败，返回码: {result.returncode}"
            return False, "", error_msg
            
    except FileNotFoundError:
        return False, "", "Git 命令未找到，请确保 Git 已安装并添加到 PATH"
    except Exception as e:
        return False, "", f"执行命令时发生异常: {str(e)}"


def check_git_available():
    """检查 Git 是否可用"""
    print("正在检查 Git 是否可用...")
    success, version, error = run_git_command(["git", "--version"])
    
    if not success:
        print(f"错误：{error}")
        print("错误：未检测到 Git，请先安装 Git 并添加到 PATH。")
        return False
    
    print(f"Git 版本: {version}")
    return True


def is_git_repo():
    """检查当前目录是否为 Git 仓库"""
    git_dir = os.path.join(os.getcwd(), ".git")
    return os.path.exists(git_dir) and os.path.isdir(git_dir)


def get_local_git_config(key):
    """获取本地 Git 配置"""
    success, value, error = run_git_command(["git", "config", "--local", key])
    if success and value:
        return value.strip()
    return None


def set_local_git_config(key, value):
    """设置本地 Git 配置"""
    success, _, error = run_git_command(["git", "config", "--local", key, value])
    if not success:
        print(f"设置 {key} 失败: {error}")
        return False
    return True


def init_git_repo():
    """初始化 Git 仓库并配置"""
    print("正在初始化 Git 仓库...")
    
    # 1. git init
    success, _, error = run_git_command(["git", "init"])
    if not success:
        print(f"git init 失败: {error}")
        return False
    
    # 2. 设置 user.name
    if not set_local_git_config("user.name", "SPIKE-handler"):
        return False
    
    # 3. 设置 user.email
    if not set_local_git_config("user.email", "SPIKE-handler.com"):
        return False
    
    # 4. 创建并切换到 dev 分支
    print("正在创建并切换到 dev 分支...")
    
    # 先尝试 git checkout -b dev
    success, _, error = run_git_command(["git", "checkout", "-b", "dev"])
    if not success:
        # 如果失败，尝试先创建分支再切换
        success1, _, error1 = run_git_command(["git", "branch", "dev"])
        if success1:
            success2, _, error2 = run_git_command(["git", "checkout", "dev"])
            if not success2:
                print(f"切换到 dev 分支失败: {error2}")
                return False
        else:
            print(f"创建 dev 分支失败: {error1}")
            return False
    
    print("初始化 Git 仓库完成，已设置用户信息，当前分支 dev。")
    return True


def delete_git_dir():
    """删除 .git 目录"""
    git_dir = os.path.join(os.getcwd(), ".git")
    try:
        if os.path.exists(git_dir):
            print(f"正在删除 {git_dir}...")
            shutil.rmtree(git_dir)
            print(".git 目录已删除")
            return True
        else:
            print(".git 目录不存在")
            return False
    except PermissionError:
        print("错误：权限不足，无法删除 .git 目录")
        return False
    except Exception as e:
        print(f"删除 .git 目录时发生错误: {str(e)}")
        return False


def handle_case_a():
    """处理情况 a：当前目录不是 Git 仓库"""
    print("当前目录不是 Git 仓库")
    return init_git_repo()


def handle_case_b():
    """处理情况 b：是 Git 仓库，但缺少本地配置"""
    print("检测到 Git 仓库，但缺少本地用户配置")
    
    user_name = get_local_git_config("user.name")
    user_email = get_local_git_config("user.email")
    
    config_updated = False
    
    if not user_name:
        print("缺少 user.name，正在设置...")
        if set_local_git_config("user.name", "SPIKE-handler"):
            config_updated = True
    
    if not user_email:
        print("缺少 user.email，正在设置...")
        if set_local_git_config("user.email", "SPIKE-handler.com"):
            config_updated = True
    
    if config_updated:
        print("已补充缺失的用户配置。")
    else:
        print("用户配置已完整，无需补充。")
    
    return True


def handle_case_c():
    """处理情况 c：是 Git 仓库，且已配置本地用户信息"""
    user_name = get_local_git_config("user.name")
    user_email = get_local_git_config("user.email")
    
    print(f"当前仓库已配置用户信息：")
    print(f"  user.name: {user_name}")
    print(f"  user.email: {user_email}")
    
    response = input("是否删除现有 .git 目录并重新配置？(y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        if not delete_git_dir():
            return False
        
        return init_git_repo()
    else:
        print("操作已取消。")
        return True


def main():
    """主函数"""
    print("=== Git 仓库状态检测与配置脚本 ===")
    print(f"当前工作目录: {os.getcwd()}")
    print()
    
    # 1. 检查 Git 是否可用
    if not check_git_available():
        input("按回车键退出...")
        sys.exit(1)
    
    print()
    
    # 2. 检测当前目录是否为 Git 仓库
    if not is_git_repo():
        # 情况 a：不是 Git 仓库
        if not handle_case_a():
            input("按回车键退出...")
            sys.exit(1)
    else:
        # 是 Git 仓库，检查配置
        user_name = get_local_git_config("user.name")
        user_email = get_local_git_config("user.email")
        
        if not user_name or not user_email:
            # 情况 b：缺少配置
            if not handle_case_b():
                input("按回车键退出...")
                sys.exit(1)
        else:
            # 情况 c：已有配置
            if not handle_case_c():
                input("按回车键退出...")
                sys.exit(1)
    
    print()
    print("=== 脚本执行完成 ===")
    try:
        input("按回车键退出...")
    except EOFError:
        # 当通过管道输入时忽略EOF错误
        pass


if __name__ == "__main__":
    main()