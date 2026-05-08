"""
IGPSPORT平台 API 封装
提供登录、上传FIT文件等功能
"""
import requests
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
        
        # 添加重试机制，自动处理临时网络错误和5xx错误
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=2, # 最多重试2次
            backoff_factor=1, # 重试间隔：1s、2s
            status_forcelist=[429, 500, 502, 503, 504] # 这些状态码自动重试
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({"User-Agent": UA})
    
    def login(self) -> bool:
        """
        登录IGPSPORT平台，先获取CSRF Token，兼容中英文界面
        Returns:
            登录是否成功
        """
        login_page_url = "https://www.igpsport.com/user/login"
        try:
            # 1. 先获取登录页面，提取CSRF Token
            resp = self.session.get(login_page_url, timeout=15)
            resp.raise_for_status()
            
            # 从页面中提取CSRF Token
            csrf_match = re.search(r'name="csrf_token" value="(.+?)"', resp.text)
            csrf_token = csrf_match.group(1) if csrf_match else None
            
            # 2. 提交登录表单，带上CSRF Token
            login_url = "https://www.igpsport.com/user/login"
            payload = {
                "email": self.username,
                "password": self.password,
                "remember": 1
            }
            if csrf_token:
                payload["csrf_token"] = csrf_token
            
            resp = self.session.post(login_url, data=payload, timeout=15)
            resp.raise_for_status()
            
            # 3. 检查登录是否成功，兼容中英文界面
            if resp.history or "logout" in resp.text.lower() or "退出登录" in resp.text or self.session.cookies.get("sessionid"):
                logger.info("✅ IGPSPORT 登录成功")
                return True
            else:
                logger.error("❌ IGPSPORT 登录失败：请检查用户名和密码")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ IGPSPORT 登录失败: {e}")
            return False
    
    def upload_fit_file(self, fit_path: str) -> bool:
        """
        上传FIT文件到IGPSPORT，使用标准FIT MIME类型
        Args:
            fit_path: FIT文件路径
        Returns:
            上传是否成功
        """
        upload_url = "https://www.igpsport.com/upload/file"
        
        try:
            with open(fit_path, "rb") as f:
                # 使用标准的FIT文件MIME类型
                files = {"file": (fit_path.split("/")[-1], f, "application/vnd.ant.fit")}
                resp = self.session.post(upload_url, files=files, timeout=60)
                resp.raise_for_status()
            
            logger.info(f"✅ 上传FIT文件到IGPSPORT成功: {fit_path.split('/')[-1]}")
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ 文件不存在: {fit_path}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 上传FIT文件失败: {e}")
            return False
        except IOError as e:
            logger.error(f"❌ 读取文件失败: {e}")
            return False
