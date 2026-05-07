import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

class IGPSPORT:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def login(self):
        login_url = "https://www.igpsport.com/user/login"
        payload = {
            "email": self.username,
            "password": self.password,
            "remember": 1
        }
        try:
            resp = self.session.post(login_url, data=payload, timeout=15)
            if resp.status_code == 200:
                print("✅ IGPSPORT 登录成功")
                return True
            else:
                raise Exception("登录接口返回异常")
        except Exception as e:
            print(f"❌ IGPSPORT 登录失败: {e}")
            return False

    def upload_fit_file(self, fit_path):
        upload_url = "https://www.igpsport.com/upload/file"
        try:
            with open(fit_path, "rb") as f:
                files = {"file": f}
                resp = self.session.post(upload_url, files=files, timeout=60)
            print(f"📤 上传FIT到IGPSPORT成功")
            return True
        except Exception as e:
            print(f"❌ 上传FIT失败: {e}")
            return False
