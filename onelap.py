import requests
from utils import safe_sleep

BASE_API = "https://api.onelap.cn"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"

class OnelapMagene:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})
        self.token = None

    def login(self):
        url = f"{BASE_API}/v1/auth/login"
        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "client_id": "onelap_app"
        }
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            data = resp.json()
            self.token = data.get("access_token")
            if not self.token:
                raise Exception("未获取到token，登录失败")
            print("✅ 迈金顽鹿登录成功")
            return True
        except Exception as e:
            print(f"❌ 迈金登录失败: {e}")
            return False

    def get_activity_list(self, page=1, limit=5):
        if not self.token:
            return []
        url = f"{BASE_API}/v1/activities"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"page": page, "limit": limit}
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=15)
            data = resp.json()
            return data.get("data", {}).get("list", [])
        except Exception as e:
            print(f"❌ 获取运动列表失败: {e}")
            return []

    def download_fit(self, activity_id, save_dir):
        if not self.token:
            return None
        url = f"{BASE_API}/v1/activities/{activity_id}/download_fit"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            resp = self.session.get(url, headers=headers, stream=True, timeout=30)
            save_path = f"{save_dir}/{activity_id}.fit"
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"📥 下载FIT完成: {activity_id}.fit")
            return save_path
        except Exception as e:
            print(f"❌ 下载FIT失败 {activity_id}: {e}")
            return None
