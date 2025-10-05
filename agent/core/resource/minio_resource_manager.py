# # 1) 拉取源码（或切换到你想要的 tag）
# git clone https://github.com/minio/minio.git
# cd minio
# # 可选：切换到某个发布标签
# # git checkout RELEASE.2025-09-xxTxx-xx-xxZ
#
# # 2) 用官方 release Dockerfile 构建镜像(------------这一步仍然报错-------------)
# sudo DOCKER_BUILDKIT=1 docker build --network=host -t minio:release -f Dockerfile.release .
# 如果网络问题失败，则直接pull：
#   sudo docker pull docker.io/library/golang:1.24-alpine
#
# # 3) 准备数据目录
# sudo mkdir -p /srv/minio
# sudo chown -R $USER:$USER /srv/minio
#
# # 4) 运行（仅映射到本机端口，待会儿走 Nginx 反代上公网）
# docker run -d --name minio \
#   -p 127.0.0.1:9000:9000 \
#   -p 127.0.0.1:9001:9001 \
#   -v /srv/minio:/data \
#   -e MINIO_ROOT_USER="tutuadmin" \
#   -e MINIO_ROOT_PASSWORD="请改成强随机密码" \
#   -e MINIO_SERVER_URL="https://s3.powerai.cc" \
#   -e MINIO_BROWSER_REDIRECT_URL="https://minio.powerai.cc/" \
#   minio:release server /data --console-address ":9001"

