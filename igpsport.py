"""
IGPSPORT平台 API 封装
提供登录、上传FIT文件等功能
"""
import requests
from typing import Optional


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class IGPSPORT:
    """IGPSPORT平台API封装类"""
    
    def __init__(self, username: str, password: str):
        """
        初始化IGPSPORT API客户端
        
        Args:
            username: 用户名/邮箱
            password: 密码
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def login(self) -> bool:
        """
        登录IGPSPORT平台
        
        Returns:
            登录是否成功
        """
        login_url = "https://www.igpsport.com/user/login"
        payload = {
            "email": self.username,
            "password": self.password,
            "remember": 1
        }
        
        try:
            resp = self.session.post(login_url, data=payload, timeout=15)
            resp.raise_for_status()
            
            # 检查登录是否成功（根据实际响应调整）
            if "登录成功" in resp.text or resp.status_code == 200:
                print("✅ IGPSPORT 登录成功")
                return True
            else:
                print("❌ IGPSPORT 登录失败：请检查用户名和密码")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ IGPSPORT 登录失败: {e}")
            return False

    def upload_fit_file(self, fit_path: str) -> bool:
        """
        上传FIT文件到IGPSPORT
        
        Args:
            fit_path: FIT文件路径
            
        Returns:
            上传是否成功
        """
        upload_url = "https://www.igpsport.com/upload/file"
        
        try:
            with open(fit_path, "rb") as f:
                files = {"file": (fit_path.split("/")[-1], f, "application/octet-stream")}
                resp = self.session.post(upload_url, files=files, timeout=60)
                resp.raise_for_status()
            
            print(f"✅ 上传FIT文件到IGPSPORT成功: {fit_path.split('/')[-1]}")
            return True
            
        except FileNotFoundError:
            print(f"❌ 文件不存在: {fit_path}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 上传FIT文件失败: {e}")
            return False
        except IOError as e:
            print(f"❌ 读取文件失败: {e}")
            return False
