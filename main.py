import json
from utils import make_save_dir, safe_sleep, get_synced_ids, save_synced_id
from onelap import OnelapMagene
from igpsport import IGPSPORT


def main():
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

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
