#!/bin/bash

# 要追加的内容
append_content=$(cat <<EOF
alias p='ps aux | grep -v "grep" | grep \$1'
alias s='systemctl list-unit-files | grep \$1'
alias d='du -sh .; df -h .'
EOF
)

# 将内容追加到 .bashrc 文件的末尾
echo "$append_content" >> ~/.bashrc

# 重新加载 .bashrc 以立即生效
source ~/.bashrc