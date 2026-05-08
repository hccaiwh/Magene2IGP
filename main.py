""" Magene2IGP 主程序 自动同步迈金(Magene/Onelap)运动记录到 IGPSPORT 平台 """
import json
import os
import sys
import random
import logging
from typing import Dict, Any
from utils import make_save_dir, safe_sleep, get_synced_ids, save_synced_id
from onelap import OnelapMagene
from igpsport import IGPSPORT

# 配置日志，自动带时间戳，规范输出
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def safe_int_env(key: str, default: int) -> int:
    """安全获取整数类型的环境变量，处理空值/非数字值，避免程序崩溃"""
    val = os.getenv(key)
    if val and val.strip().isdigit():
        return int(val.strip())
    return default

def load_config() -> Dict[str, Any]:
    """
    加载配置，优先使用环境变量，否则使用配置文件
    
    Returns:
        配置字典
    """
    # 支持两种配置方式：
    # 1. 分别配置：MAGENE_USERNAME/PASSWORD 和 IGPSPORT_USERNAME/PASSWORD
    # 2. 统一配置：USERNAME/PASSWORD（同时用于两个平台）
    magene_username = os.getenv("MAGENE_USERNAME") or os.getenv("USERNAME")
    magene_password = os.getenv("MAGENE_PASSWORD") or os.getenv("PASSWORD")
    igpsport_username = os.getenv("IGSPORT_USERNAME") or os.getenv("USERNAME")
    igpsport_password = os.getenv("IGSPORT_PASSWORD") or os.getenv("PASSWORD")

    config = {
        "magene": {
            "username": magene_username,
            "password": magene_password
        },
        "igpsport": {
            "username": igpsport_username,
            "password": igpsport_password
        },
        "limit": safe_int_env("LIMIT", 5),
        "delay_sec": safe_int_env("DELAY_SEC", 2)
    }

    # 如果环境变量未设置，则从配置文件读取
    if not config["magene"]["username"] or not config["magene"]["password"]:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                file_config = json.load(f)
                if not config["magene"]["username"]:
                    config["magene"]["username"] = file_config["magene"]["username"]
                if not config["magene"]["password"]:
                    config["magene"]["password"] = file_config["magene"]["password"]
                if not config["igpsport"]["username"]:
                    config["igpsport"]["username"] = file_config["igpsport"]["username"]
                if not config["igpsport"]["password"]:
                    config["igpsport"]["password"] = file_config["igpsport"]["password"]
                config["limit"] = file_config.get("limit", config["limit"])
                config["delay_sec"] = file_config.get("delay_sec", config["delay_sec"])
        except FileNotFoundError:
            pass

    return config

def validate_config(config: Dict[str, Any]) -> bool:
    """
    验证配置是否完整
    
    Args:
        config: 配置字典
    
    Returns:
        配置是否有效
    """
    magene = config.get("magene", {})
    igpsport = config.get("igpsport", {})
    
    if not magene.get("username") or not magene.get("password"):
        logger.error("错误：迈金(Magene)用户名或密码未配置")
        return False
    
    if not igpsport.get("username") or not igpsport.get("password"):
        logger.error("错误：IGPSPORT用户名或密码未配置")
        return False
    
    return True

def main() -> None:
    """主函数"""
    logger.info("🚀 Magene2IGP 同步工具启动")
    logger.info("=" * 50)
    
    # 加载配置
    cfg = load_config()
    
    # 验证配置
    if not validate_config(cfg):
        logger.info("\n💡 提示：请设置环境变量或在 config.json 中配置用户名和密码")
        sys.exit(1)
    
    magene_cfg = cfg["magene"]
    igp_cfg = cfg["igpsport"]
    limit = cfg["limit"]
    delay = cfg["delay_sec"]
    
    logger.info(f"ℹ️ 配置信息：每次同步最多 {limit} 条记录，延迟 {delay} 秒")
    
    # 创建保存目录
    save_dir = make_save_dir("fit_files")
    
    # 获取已同步的记录
    synced_ids = get_synced_ids()
    logger.info(f"ℹ️ 已有已同步记录数量：{len(synced_ids)} 条")
    
    # 登录迈金
    logger.info("\n📝 正在登录迈金平台...")
    magene = OnelapMagene(magene_cfg["username"], magene_cfg["password"])
    if not magene.login():
        logger.error("❌ 迈金登录失败，程序退出")
        sys.exit(1)
    
    # 登录IGPSPORT（移到循环外，整个流程只登录一次）
    logger.info("\n📝 正在登录IGPSPORT平台...")
    igp = IGPSPORT(igp_cfg["username"], igp_cfg["password"])
    if not igp.login():
        logger.error("❌ IGPSPORT登录失败，程序退出")
        sys.exit(1)
    
    # 获取活动列表
    logger.info(f"\n📋 正在获取最近 {limit} 条运动记录...")
    act_list = magene.get_activity_list(limit=limit)
    
    if not act_list:
        logger.info("ℹ️ 未获取到迈金运动记录")
        return
    
    logger.info(f"✅ 共获取到迈金运动记录：{len(act_list)} 条")
    
    # 同步每条记录
    success_count = 0
    skip_count = 0
    
    for act in act_list:
        # 提取活动唯一ID（适配新API返回格式）
        act_id = act.get("fitUrl") or act.get("fileKey") or str(act.get("id", ""))
        if not act_id:
            continue
        
        # 检查是否已同步
        if str(act_id) in synced_ids:
            logger.info(f"\n⏭️ 运动ID {act_id} 已同步过，自动跳过")
            skip_count += 1
            continue
        
        # 下载FIT文件（传入整个activity字典）
        logger.info(f"\n===== 开始同步新运动ID: {act_id} =====")
        fit_path = magene.download_fit(act, save_dir)
        
        if not fit_path:
            logger.warning(f"⚠️ 下载失败，跳过运动ID {act_id}")
            continue
        
        # 上传到IGPSPORT
        logger.info(f"📤 正在上传到IGPSPORT...")
        if igp.upload_fit_file(fit_path):
            save_synced_id(str(act_id))
            logger.info(f"✅ 运动ID {act_id} 同步成功")
            success_count += 1
            # 带随机抖动的休眠，避免固定频率触发平台限流
            safe_sleep(delay + random.uniform(0, 1))
        else:
            logger.warning(f"⚠️ 上传失败，运动ID {act_id}")
        
        # 清理临时FIT文件，避免累积占用空间
        try:
            os.remove(fit_path)
        except Exception:
            pass # 忽略删除失败，不影响主流程
    
    # 输出总结
    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 本轮同步任务执行完毕")
    logger.info(f"  成功：{success_count} 条")
    logger.info(f"  跳过：{skip_count} 条")
    logger.info(f"  总计：{len(act_list)} 条")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ 程序异常：{e}", exc_info=True)
        sys.exit(1)
