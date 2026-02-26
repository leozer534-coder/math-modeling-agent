# ❓ 常见问题 FAQ

本文档收集了用户使用 MathModelAgent 过程中最常见的问题和解决方案。

---

## 目录

- [安装部署问题](#安装部署问题)
- [API 配置问题](#api-配置问题)
- [代码执行问题](#代码执行问题)
- [模型生成问题](#模型生成问题)
- [性能优化问题](#性能优化问题)
- [其他问题](#其他问题)

---

## 安装部署问题

### Q1: Docker 启动失败，提示端口被占用

**问题描述:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**解决方案:**

1. 查找占用端口的进程：
```bash
# Linux/macOS
lsof -i :8000
# 或者
netstat -tulpn | grep 8000

# Windows
netstat -ano | findstr :8000
```

2. 停止占用端口的进程：
```bash
# Linux/macOS
sudo kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

3. 或者修改端口映射（`docker-compose.yml`）：
```yaml
ports:
  - "8001:8000"  # 将主机的 8001 端口映射到容器的 8000 端口
```

---

### Q2: Redis 连接失败

**问题描述:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案:**

**Docker 部署:**
```bash
# 检查 Redis 容器状态
docker-compose ps redis

# 重启 Redis
docker-compose restart redis

# 查看 Redis 日志
docker-compose logs redis
```

**本地部署:**
```bash
# 检查 Redis 是否运行
redis-cli ping
# 应该返回 PONG

# 启动 Redis
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Windows
# 运行 redis-server.exe
```

检查 `.env.dev` 配置：
```env
# Docker 环境
REDIS_URL=redis://redis:6379/0

# 本地环境
REDIS_URL=redis://localhost:6379/0
```

---

### Q3: 前端页面空白或无法加载

**问题描述:** 访问 http://localhost:5173 页面空白

**解决方案:**

1. 检查前端是否启动：
```bash
cd frontend
pnpm run dev
```

2. 检查浏览器控制台错误（F12）

3. 清除浏览器缓存或尝试无痕模式

4. 检查后端是否可访问：
```bash
curl http://localhost:8000/health
```

5. 检查前端配置：
```bash
# frontend/.env.development
VITE_API_URL=http://localhost:8000
```

---

### Q4: Python 依赖安装失败

**问题描述:**
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案:**

1. 检查 Python 版本（需要 3.10-3.12）：
```bash
python --version
```

2. 升级 pip：
```bash
python -m pip install --upgrade pip
```

3. 使用 uv（推荐）：
```bash
pip install uv
uv sync
```

4. 使用国内镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

5. 检查网络或配置代理

---

## API 配置问题

### Q5: 应该使用哪个 LLM 模型？

**推荐配置:**

**性价比之选（推荐）:**
```env
COORDINATOR_MODEL=deepseek/deepseek-chat
COORDINATOR_BASE_URL=https://api.deepseek.com
```

**高质量之选:**
```env
COORDINATOR_MODEL=claude-3-5-sonnet-20241022
COORDINATOR_BASE_URL=https://api.anthropic.com
```

**开源之选:**
```env
COORDINATOR_MODEL=qwen/qwen-2.5-72b-instruct
COORDINATOR_BASE_URL=https://api.together.xyz
```

**不同 Agent 使用不同模型:**
```env
# 协调者（需要强推理能力）
COORDINATOR_MODEL=claude-3-5-sonnet-20241022

# 建模者（需要数学能力）
MODELER_MODEL=deepseek/deepseek-chat

# 代码者（需要代码能力）
CODER_MODEL=gpt-4o

# 写作者（需要写作能力）
WRITER_MODEL=deepseek/deepseek-chat
```

---

### Q6: API Key 无效或余额不足

**问题描述:**
```
Error: Invalid API key or insufficient balance
```

**解决方案:**

1. 检查 API Key 是否正确复制（无空格）

2. 检查账户余额：
   - DeepSeek: https://platform.deepseek.com/
   - OpenAI: https://platform.openai.com/account/usage
   - 302.AI: https://console.302.ai/

3. 测试 API 连接：
```bash
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer sk-your-key"
```

4. 检查 Base URL 是否正确

5. 如果使用代理，检查代理配置

---

### Q7: 如何配置多个 LLM 提供商？

**示例配置:**
```env
# 协调者使用 Claude
COORDINATOR_API_KEY=sk-ant-xxx
COORDINATOR_MODEL=claude-3-5-sonnet-20241022
COORDINATOR_BASE_URL=https://api.anthropic.com

# 建模者使用 DeepSeek
MODELER_API_KEY=sk-ds-xxx
MODELER_MODEL=deepseek/deepseek-chat
MODELER_BASE_URL=https://api.deepseek.com

# 代码者使用 GPT-4
CODER_API_KEY=sk-xxx
CODER_MODEL=gpt-4o
CODER_BASE_URL=https://api.openai.com/v1

# 写作者使用 DeepSeek（便宜）
WRITER_API_KEY=sk-ds-xxx
WRITER_MODEL=deepseek/deepseek-chat
WRITER_BASE_URL=https://api.deepseek.com
```

---

## 代码执行问题

### Q8: 代码执行失败，Jupyter 未响应

**问题描述:**
```
Error: Kernel died before replying to kernel_info
```

**解决方案:**

1. 安装 Jupyter：
```bash
pip install jupyter ipykernel
```

2. 检查 Jupyter 是否正常：
```bash
jupyter --version
jupyter kernelspec list
```

3. 重启后端服务

4. 检查代码执行超时设置：
```env
MAX_RETRIES=5
```

5. 使用云端代码执行器（E2B）：
```env
E2B_API_KEY=your-e2b-api-key
```

---

### Q9: 代码运行超时

**问题描述:** 代码执行时间过长被中断

**解决方案:**

1. 优化代码，减少计算量

2. 增加超时设置（修改源码）：
```python
# backend/app/code_executor.py
timeout=300  # 增加到 300 秒
```

3. 使用更强大的模型生成更高效的代码

4. 拆分复杂问题为多个子问题

---

### Q10: 绘图无法显示

**问题描述:** 生成的图表无法在论文中显示

**解决方案:**

1. 确保代码中正确保存图像：
```python
import matplotlib.pyplot as plt

plt.savefig('output.png', dpi=300, bbox_inches='tight')
plt.show()
```

2. 检查输出目录权限：
```bash
ls -la backend/project/work_dir/
```

3. 使用支持的图像格式（PNG、JPG、SVG）

4. 在论文 Markdown 中正确引用：
```markdown
![结果图](./output.png)
```

---

## 模型生成问题

### Q11: 生成的论文格式混乱

**问题描述:** 论文排版不整齐，公式显示异常

**解决方案:**

1. 使用 Markdown 编辑器查看（推荐 Typora、VS Code）

2. 导出为 PDF：
   - 使用 Pandoc：`pandoc res.md -o paper.pdf`
   - 使用在线工具：https://pandoc.org/try/

3. 检查模板配置：
```toml
# backend/app/config/md_template.toml
# 确保模板格式正确
```

4. 使用 LaTeX 模板（待实现）

---

### Q12: 模型生成的内容不准确

**问题描述:** 数学公式错误或逻辑不通

**解决方案:**

1. 使用更强的模型（如 Claude 3.5 Sonnet、GPT-4o）

2. 在问题描述中提供更多背景信息

3. 使用 Human-in-the-loop 模式（待实现）手动修正

4. 添加 Few-shot 示例到 prompt 模板

5. 增加 `MAX_CHAT_TURNS` 让模型有更多思考轮次：
```env
MAX_CHAT_TURNS=100
```

---

### Q13: 中文输出质量差

**问题描述:** 模型输出英文或中式英语

**解决方案:**

1. 在 prompt 中明确要求中文输出：
```
请用中文回答，并撰写中文数学建模论文
```

2. 使用支持中文更好的模型：
   - DeepSeek Chat
   - Qwen 2.5
   - GLM-4

3. 在系统 prompt 中添加语言要求

---

## 性能优化问题

### Q14: 响应速度太慢

**问题描述:** 生成一次回答需要很长时间

**解决方案:**

1. 使用更快的模型（如 DeepSeek 比 Claude 快）

2. 减少 `MAX_CHAT_TURNS`：
```env
MAX_CHAT_TURNS=50  # 默认 70
```

3. 优化网络（使用国内 API 提供商）

4. 使用缓存（待实现）

5. 增加并发 worker 数：
```bash
# 启动多个 uvicorn worker
uvicorn app.main:app --workers 4
```

---

### Q15: 内存占用过高

**问题描述:** 系统内存不足，服务崩溃

**解决方案:**

1. 限制 Docker 容器内存：
```yaml
# docker-compose.yml
services:
  backend:
    mem_limit: 2g
    mem_reservation: 1g
```

2. 减少并发请求数

3. 定期清理 Redis：
```bash
docker-compose exec redis redis-cli FLUSHALL
```

4. 清理工作目录：
```bash
rm -rf backend/project/work_dir/*
```

5. 升级到更大内存的服务器

---

### Q16: 如何批量处理多个问题？

**解决方案:**

目前不支持批量处理，但可以通过以下方式实现：

1. 使用 API 脚本：
```python
import requests

questions = ["问题 1", "问题 2", "问题 3"]
for q in questions:
    response = requests.post(
        "http://localhost:8000/api/solve",
        json={"question": q},
        headers={"Authorization": "Bearer your-key"}
    )
    print(response.json())
```

2. 使用队列系统（待实现）

3. 提交 GitHub Issue 请求该功能

---

## 其他问题

### Q17: 如何保存和导出论文？

**解决方案:**

1. 在聊天界面复制生成的内容

2. 下载生成的文件：
```bash
# 论文 Markdown
cat backend/project/work_dir/xxx/res.md

# 代码 Notebook
cat backend/project/work_dir/xxx/notebook.ipynb
```

3. 转换为 PDF：
```bash
pandoc backend/project/work_dir/xxx/res.md -o paper.pdf
```

4. 转换为 Word：
```bash
pandoc backend/project/work_dir/xxx/res.md -o paper.docx
```

---

### Q18: 可以用于商业比赛吗？

**回答:**

根据 [License](./License.md)：
- ✅ 个人免费使用
- ❌ 请勿商业用途
- 💼 商业用途请联系作者

**注意:** AI 生成内容仅供参考，直接参加国赛获奖目前还有难度，但可以作为辅助工具。

---

### Q19: 如何贡献代码或提交案例？

**贡献代码:**

1. Fork 项目
2. 创建分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

**提交案例:**

提交到示例仓库：
https://github.com/jihe520/MathModelAgent-Example

---

### Q20: 项目未来有什么计划？

**开发计划:**

- [ ] 完善的教程、文档
- [ ] 提供 Web 服务（云端部署）
- [ ] 英文支持（美赛）
- [ ] 集成 LaTeX 模板
- [ ] 接入视觉模型
- [ ] Human in loop (HIL)
- [ ] 多语言支持（R、Matlab）
- [ ] 更多绘图支持（napkin、draw.io、mermaid）
- [ ] Web search tool
- [ ] RAG 知识库
- [ ] Benchmark 测试

查看完整计划：[README.md](../../README.md#-后期计划)

---

## 获取帮助

如果以上 FAQ 没有解决你的问题：

1. 📖 查看 [详细部署教程](./deployment.md)
2. 📚 查看 [快速开始指南](./quickstart.md)
3. 💬 加入社区：
   - QQ 群：699970403 / 779159301
   - [Discord](https://discord.gg/3Jmpqg5J)
   - [腾讯频道](https://pd.qq.com/s/7rfbai3au)
4. 🐛 提交 [GitHub Issue](https://github.com/leozer534-coder/math-modeling-agent/issues)
5. 📧 联系作者

---

**提示:** 提问前请提供：
- 操作系统和版本
- 部署方式（Docker/本地）
- 错误日志（完整）
- 已尝试的解决方案

这样可以更快获得帮助！
