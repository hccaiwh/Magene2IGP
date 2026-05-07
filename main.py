import json
import os
from utils import make_save_dir, safe_sleep, get_synced_ids, save_synced_id
from onelap import OnelapMagene
from igpsport import IGPSPORT


def load_config():
    """加载配置，优先使用环境变量，否则使用配置文件"""
    # 支持两种配置方式：
    # 1. 分别配置：MAGENE_USERNAME/PASSWORD 和 IGPSPORT_USERNAME/PASSWORD
    # 2. 统一配置：USERNAME/PASSWORD（同时用于两个平台）

    magene_username = os.getenv("MAGENE_USERNAME") or os.getenv("USERNAME")
    magene_password = os.getenv("MAGENE_PASSWORD") or os.getenv("PASSWORD")
    igpsport_username = os.getenv("IGPSPORT_USERNAME") or os.getenv("USERNAME")
    igpsport_password = os.getenv("IGPSPORT_PASSWORD") or os.getenv("PASSWORD")

    config = {
        "magene": {
            "username": magene_username,
            "password": magene_password
        },
        "igpsport": {
            "username": igpsport_username,
            "password": igpsport_password
        },
        "limit": int(os.getenv("LIMIT", 5)),
        "delay_sec": int(os.getenv("DELAY_SEC", 2))
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


def main():
    cfg = load_config()

    magene_cfg = cfg["magene"]
    igp_cfg = cfg["igpsport"]
    limit = cfg["limit"]
    delay = cfg["delay_sec"]

    save_dir = make_save_dir("fit_files")
    synced_ids = get_synced_ids()
    print(f"ℹ️ 已有已同步记录数量：{len(synced_ids)} 条")

    magene = OnelapMagene(magene_cfg["username"], magene_cfg["password"])
    if not magene.login():
        return

    act_list = magene.get_activity_list(page=1, limit=limit)
    if not act_list:
        print("ℹ️ 未获取到迈金运动记录")
        return
    print(f"📋 共获取到迈金运动记录：{len(act_list)} 条")

    for act in act_list:
        act_id = act.get("id")
        if not act_id:
            continue

        if act_id in synced_ids:
            print(f"\n⏭️ 运动ID {act_id} 已同步过，自动跳过")
            continue

        print(f"\n===== 开始同步新运动ID: {act_id} =====")
        fit_path = magene.download_fit(act_id, save_dir)
        if not fit_path:
            continue

        igp = IGPSPORT(igp_cfg["username"], igp_cfg["password"])
        if igp.login():
            ok = igp.upload_fit_file(fit_path)
            if ok:
                save_synced_id(act_id)
                print(f"✅ 运动ID {act_id} 已标记为已同步")
        safe_sleep(delay)

    print("\n🎉 本轮同步任务执行完毕")


if __name__ == "__main__":
    main()
