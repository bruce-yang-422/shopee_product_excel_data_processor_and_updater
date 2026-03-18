#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: project_tree_structure_generator.py
用途: 增強版目錄樹生成器
說明: 簡單的專案目錄樹結構生成工具，建立專案資料夾結構的視覺化表示
     將目錄樹結構儲存到 project_tree_structure.txt，適用於文件記錄和專案結構概覽
     自動掃描專案資料夾並生成層級式目錄結構
重要提醒: 輸出檔案為根目錄的 project_tree_structure.txt
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.1 (2025-07-14)
"""
import os
import argparse
from pathlib import Path

EXCLUDE_DIRS = {
    '.git', '__pycache__', '.mypy_cache', '.pytest_cache', '.DS_Store', 
    'dist', 'build', '.coverage', '.tox', '.eggs'
}

SHOW_DIRS_ONLY = {
    '.venv', '.idea', '.vscode', 'env', 'venv', 'node_modules'
}

EXCLUDE_FILES = {
    '.gitignore', '.DS_Store', 'Thumbs.db', '.env', '.env.local',
    '.coverage', '.pyc', '.pyo', '.pyd', '.log', '.tmp', '.cache'
}

def get_file_emoji(filename):
    """根據檔案類型返回對應的 emoji"""
    ext = os.path.splitext(filename)[1].lower()
    
    emoji_map = {
        # 程式碼檔案
        '.py': '🐍', '.js': '🟨', '.ts': '🔷', '.jsx': '⚛️', '.tsx': '⚛️',
        '.html': '🌐', '.css': '🎨', '.scss': '🎨', '.sass': '🎨',
        '.java': '☕', '.cpp': '⚡', '.c': '⚡', '.cs': '💎', '.php': '🐘',
        '.rb': '💎', '.go': '🐹', '.rs': '🦀', '.swift': '🍎', '.kt': '🤖',
        '.vue': '💚', '.svelte': '🧡', '.dart': '🎯', '.scala': '🔴',
        
        # 資料檔案
        '.json': '📋', '.xml': '📋', '.yaml': '📋', '.yml': '📋',
        '.csv': '📊', '.xlsx': '📈', '.xls': '📈', '.sql': '🗃️',
        '.db': '🗃️', '.sqlite': '🗃️', '.sqlite3': '🗃️',
        
        # 文件檔案
        '.md': '📝', '.txt': '📄', '.pdf': '📕', '.doc': '📘', '.docx': '📘',
        '.rtf': '📄', '.odt': '📄', '.pages': '📄',
        
        # 圖片檔案
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
        '.bmp': '🖼️', '.tiff': '🖼️', '.svg': '🎨', '.ico': '🖼️',
        '.webp': '🖼️', '.heic': '🖼️', '.raw': '📸',
        
        # 影音檔案
        '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
        '.wmv': '🎬', '.flv': '🎬', '.webm': '🎬',
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.aac': '🎵',
        '.ogg': '🎵', '.m4a': '🎵',
        
        # 壓縮檔案
        '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦',
        '.gz': '📦', '.bz2': '📦', '.xz': '📦',
        
        # 設定檔案
        '.config': '⚙️', '.conf': '⚙️', '.cfg': '⚙️', '.ini': '⚙️',
        '.toml': '⚙️', '.env': '🔧', '.properties': '⚙️',
        
        # 其他常見檔案
        '.log': '📋', '.tmp': '🗂️', '.cache': '🗂️', '.lock': '🔒',
        '.key': '🔑', '.pem': '🔑', '.crt': '🔑', '.cert': '🔑',
        '.gitignore': '🚫', '.dockerignore': '🚫',
        '.dockerfile': '🐳', '.docker': '🐳',
        'makefile': '🔨', '.mk': '🔨',
        '.sh': '💻', '.bat': '💻', '.cmd': '💻', '.ps1': '💻',
    }
    
    # 特殊檔案名稱處理
    lower_name = filename.lower()
    if lower_name in ['readme', 'readme.md', 'readme.txt']:
        return '📖'
    elif lower_name in ['license', 'license.txt', 'license.md']:
        return '📜'
    elif lower_name in ['dockerfile']:
        return '🐳'
    elif lower_name in ['makefile']:
        return '🔨'
    elif lower_name.startswith('requirements'):
        return '📋'
    elif lower_name in ['package.json', 'package-lock.json']:
        return '📦'
    elif lower_name in ['yarn.lock', 'pnpm-lock.yaml']:
        return '🔒'
    elif lower_name in ['pyproject.toml', 'poetry.lock']:
        return '🐍'
    elif lower_name in ['cargo.toml', 'cargo.lock']:
        return '🦀'
    elif lower_name in ['go.mod', 'go.sum']:
        return '🐹'
    
    return emoji_map.get(ext, '📄')

def should_exclude(name, is_dir=False):
    """檢查是否應該排除此項目"""
    if is_dir:
        return name in EXCLUDE_DIRS
    else:
        return name in EXCLUDE_FILES or name.startswith('.') and name not in ['.env', '.gitignore']

def group_files_by_extension(files):
    """將檔案按副檔名分組，重要檔案類型不省略"""
    # 重要檔案類型：腳本類和環境配置類
    IMPORTANT_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.sh', '.bat', '.cmd', '.ps1',
        '.json', '.yaml', '.yml', '.toml', '.env', '.config', '.conf', '.cfg', '.ini'
    }
    
    groups = {}
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext not in groups:
            groups[ext] = []
        groups[ext].append(file)
    
    result = []
    for ext, file_list in groups.items():
        if ext in IMPORTANT_EXTENSIONS:
            # 重要檔案類型全部列出
            result.extend(file_list)
        else:
            # 其他檔案類型最多顯示3個
            if len(file_list) <= 3:
                result.extend(file_list)
            else:
                result.extend(file_list[:3])
                result.append(f"... 還有 {len(file_list) - 3} 個 {ext} 檔案")
    
    return result

def get_file_size(path):
    """獲取檔案大小（以人類可讀格式）"""
    try:
        size = os.path.getsize(path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    except OSError:
        return ""

def print_tree(root, prefix="", file=None, show_size=False, max_depth=None, current_depth=0):
    """遞歸打印目錄樹"""
    if max_depth is not None and current_depth >= max_depth:
        return
    
    try:
        all_entries = os.listdir(root)
        
        # 分離目錄和檔案
        directories = []
        files = []
        
        for entry in all_entries:
            path = os.path.join(root, entry)
            if os.path.isdir(path):
                # 檢查是否為只顯示目錄的特殊目錄
                if entry in SHOW_DIRS_ONLY:
                    directories.append(entry)
                elif not should_exclude(entry, True):
                    directories.append(entry)
            else:
                if not should_exclude(entry, False):
                    files.append(entry)
        
        # 對目錄排序
        directories.sort()
        
        # 對檔案按副檔名分組並限制數量
        grouped_files = group_files_by_extension(files)
        grouped_files.sort()
        
        # 合併目錄和檔案
        all_entries = directories + grouped_files
        
        for idx, entry in enumerate(all_entries):
            connector = "└── " if idx == len(all_entries) - 1 else "├── "
            
            # 檢查是否為統計資訊
            if entry.startswith("... 還有"):
                file.write(prefix + connector + f"📊 {entry}\n")
                continue
            
            path = os.path.join(root, entry)
            
            # 準備顯示文字
            if os.path.isdir(path):
                # 目錄圖示
                if entry in SHOW_DIRS_ONLY:
                    emoji = "📁"
                else:
                    emoji = "📂"
                display_text = f"{emoji} {entry}"
            else:
                # 檔案圖示
                emoji = get_file_emoji(entry)
                display_text = f"{emoji} {entry}"
                
                if show_size:
                    size = get_file_size(path)
                    if size:
                        display_text += f" ({size})"
            
            file.write(prefix + connector + display_text + "\n")
            
            # 如果是目錄且不在只顯示目錄的清單中，遞歸處理
            if os.path.isdir(path) and entry not in SHOW_DIRS_ONLY:
                extension = "    " if idx == len(all_entries) - 1 else "│   "
                print_tree(path, prefix + extension, file, show_size, max_depth, current_depth + 1)
                
    except PermissionError:
        file.write(prefix + "├── 🚫 [權限不足]\n")
    except Exception as e:
        file.write(prefix + f"├── ❌ [錯誤: {str(e)}]\n")

def count_items(root, max_depth=None, current_depth=0):
    """計算目錄和檔案數量"""
    if max_depth is not None and current_depth >= max_depth:
        return 0, 0
    
    dirs = 0
    files = 0
    
    try:
        for entry in os.listdir(root):
            path = os.path.join(root, entry)
            if os.path.isdir(path):
                if entry in SHOW_DIRS_ONLY:
                    dirs += 1
                elif not should_exclude(entry, True):
                    dirs += 1
                    sub_dirs, sub_files = count_items(path, max_depth, current_depth + 1)
                    dirs += sub_dirs
                    files += sub_files
            else:
                if not should_exclude(entry, False):
                    files += 1
    except (PermissionError, OSError):
        pass
    
    return dirs, files

def main():
    parser = argparse.ArgumentParser(description='生成目錄樹結構')
    parser.add_argument('-o', '--output', default='project_tree_structure.txt', help='輸出檔案名稱')
    parser.add_argument('-s', '--size', action='store_true', help='顯示檔案大小')
    parser.add_argument('-d', '--depth', type=int, help='最大深度限制')
    parser.add_argument('-p', '--path', default='.', help='指定掃描路徑')
    parser.add_argument('--stats', action='store_true', help='顯示統計資訊')
    
    args = parser.parse_args()
    
    root_path = os.path.abspath(args.path)
    if not os.path.exists(root_path):
        print(f"錯誤：路徑 '{args.path}' 不存在")
        return
    
    folder_name = os.path.basename(root_path)
    if not folder_name:  # 處理根目錄情況
        folder_name = root_path
    
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            # 寫入標題
            f.write(f"📁 {folder_name}\n")
            
            # 生成樹狀結構
            print_tree(root_path, file=f, show_size=args.size, max_depth=args.depth)
            
            # 添加統計資訊
            if args.stats:
                dirs, files = count_items(root_path, args.depth)
                f.write(f"\n📊 統計資訊:\n")
                f.write(f"📂 目錄數量: {dirs}\n")
                f.write(f"📄 檔案數量: {files}\n")
                f.write(f"📋 總計: {dirs + files} 個項目\n")
        
        print(f"🌳 樹狀圖已輸出到 {args.output}（根目錄為：{folder_name}）")
        
        if args.stats:
            dirs, files = count_items(root_path, args.depth)
            print(f"📊 統計：{dirs} 個目錄，{files} 個檔案")
            
    except Exception as e:
        print(f"錯誤：無法寫入檔案 {args.output}: {str(e)}")

if __name__ == "__main__":
    main()
