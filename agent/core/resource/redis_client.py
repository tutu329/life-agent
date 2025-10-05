 # 安装redis服务
#     sudo apt install redis-server
#     sudo systemctl start redis-server
#     sudo systemctl restart redis-server
#     sudo systemctl enable redis-server
#     sudo systemctl status redis-server
#
# 配置redis
#     sudo vi /etc/redis/redis.conf
#     bind 127.0.0.1 改为 bind 0.0.0.0
#     port 6379 改为 8010(https时，是tls-port设置为8010)
#     sudo systemctl restart redis-server
#     验证：
#         redis-cli -p 8010
#         ping（如果返回PONG则正常）
#
# win下安装redis-cli
#     https://github.com/microsoftarchive/redis/releases下载最新msi，安装即可
#     控制台下验证：
#         redis-cli -h powerai.cc -p 8010
#         ping（如果返回PONG则正常）
#
# 关于TLS(https)：
#     1、sudo cat /etc/redis/redis.conf | grep tls
#     2、确保crt和key文件没有过期
#     3、redis-cli --tls -h powerai.cc -p 8010 --cacert /etc/ssl/certs/ca-certificates.crt -a 'YOUR_STRONG_PASS' PING
#     4、取消TLS，/etc/redis/redis.conf中，注释掉所有tls开头的配置，port 0改为port 8010
