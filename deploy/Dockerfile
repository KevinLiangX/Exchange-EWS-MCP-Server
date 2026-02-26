# syntax=docker/dockerfile:1
# 推荐使用官方专门为 UV 构建优化的镜像基础底包
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，启用字节码缓存并禁止构建环境缓冲
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# 同步项目依赖。通过单独复制相关锁定文件，充分利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
# --no-install-project 表示此时只装上游依赖库，不安装本项目源代码（加快二次构建速度）
RUN uv sync --frozen --no-install-project --no-dev

# 复制真正的项目源代码
COPY src ./src
COPY main.py ./

# 再次完整安装包括项目自身模块的依赖链
RUN uv sync --frozen --no-dev

# 对外暴露运行 SSE 或 HTTP 服务的端口 (由环境变量也可控)
EXPOSE 3101

# 启动命令（默认以 SSE 模式起服，具体可通过 k8s env/args 覆盖）
CMD ["uv", "run", "main.py"]
