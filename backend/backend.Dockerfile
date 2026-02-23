FROM python:3.10-slim

WORKDIR /app

# 1. 替换 Debian 系统源为国内镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list || true \
	&& sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list || true \
	&& if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
	sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
	sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
	fi

# 2. 安装系统依赖
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libpq-dev tzdata \
	&& rm -rf /var/lib/apt/lists/*

# Set timezone to Asia/Shanghai
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 3. 复制依赖文件
COPY requirements.txt .

# 4. 安装 Python 依赖（继续使用阿里云镜像，并增加超时容错）
RUN pip install --no-cache-dir --timeout 120 --retries 3 \
	-r requirements.txt \
	-i https://mirrors.aliyun.com/pypi/simple/

# 5. 复制项目代码
COPY . .

EXPOSE 8000

# 6. 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]