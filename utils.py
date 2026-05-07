"""
工具函数模块
提供文件操作、目录创建、同步记录管理等功能
"""
import time
import json
from pathlib import Path
from typing import Set

SYNC_RECORD_FILE = "synced_ids.txt"


def make_save_dir(dir_name: str = "fit_files") -> str:
    """
    创建保存目录
    
    Args:
        dir_name: 目录名称
        
    Returns:
        创建的目录路径
    """
    Path(dir_name).mkdir(parents=True, exist_ok=True)
    return dir_name


def safe_sleep(sec: int) -> None:
    """
    安全休眠
    
    Args:
        sec: 休眠秒数
    """
    time.sleep(sec)


def get_synced_ids() -> Set[str]:
    """
    获取已同步的活动ID集合
    
    Returns:
        已同步的活动ID集合
    """
    sync_file = Path(SYNC_RECORD_FILE)
    
    if not sync_file.exists():
        return set()
    
    try:
        with open(sync_file, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"⚠️ 读取同步记录失败: {e}")
        return set()


def save_synced_id(act_id: str) -> None:
    """
    保存已同步的活动ID
    
    Args:
        act_id: 活动ID
    """
    sync_file = Path(SYNC_RECORD_FILE)
    synced_ids = get_synced_ids()
    
    if act_id not in synced_ids:
        try:
            with open(sync_file, "a", encoding="utf-8") as f:
                f.write(f"{act_id}\n")
            print(f"✅ 活动ID {act_id} 已保存到同步记录")
        except Exception as e:
            print(f"❌ 保存同步记录失败: {e}")
