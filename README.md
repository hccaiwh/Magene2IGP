# Magene2IGP
自动同步迈金(Magene/Onelap)运动记录到 IGPSPORT 的工具。
## 功能
- 自动从迈金平台下载运动记录（FIT 文件）
- 自动上传到 IGPSPORT 平台
- 支持增量同步（已同步的记录不会重复上传）
- 支持通过 GitHub Actions 自动化运行
## 使用方法
### 本地运行
1. 安装依赖：
```bash
pip install -r requirements.txt
```
2. 配置 `config.json`（或设置环境变量）
3. 运行：
```bash
python main.py
```
### 通过 GitHub Actions 自动运行
项目已配置 GitHub Actions 工作流，支持：
1. **手动触发**：在 GitHub 仓库 → Actions → "Sync Magene to IGPSPORT" → "Run workflow"
2. **定时运行**：每周一早上 8:00（北京时间）自动运行（如需启用请取消工作流中的注释）
#### 配置 GitHub Secrets
在 GitHub 仓库设置中添加以下 Secrets：
- `USERNAME`：迈金和 IGPSPORT 的用户名（手机号）
- `PASSWORD`：密码
（可选）自定义同步参数：
- `LIMIT`：每次同步的最大记录数（默认：5）
- `DELAY_SEC`：每次上传后的延迟秒数（默认：2）
## 文件说明
- `main.py`：主程序入口
- `onelap.py`：迈金平台 API 封装
- `igpsport.py`：IGPSPORT 平台 API 封装
- `utils.py`：工具函数（文件下载、目录创建等）
- `config.json`：配置文件模板（不包含真实密码）
- `.github/workflows/sync.yml`：GitHub Actions 工作流配置
## 注意事项
- 首次运行会同步最近的 limit 条新记录
- 已同步的记录 ID 保存在 `synced_ids.txt` 中
- GitHub Actions 运行时会自动保存/恢复同步状态，增量同步正常生效
## 许可
MIT License
