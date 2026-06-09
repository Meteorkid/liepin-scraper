#!/bin/bash
# 自动提交数据文件到 Git
# 用法: ./auto_commit.sh [提交信息]

cd /Users/meteor/爬虫实习项目/猎聘

# 添加数据文件
git add *.xlsx *.csv

# 提交
if [ -n "$1" ]; then
    git commit -m "data: $1"
else
    git commit -m "data: auto-save $(date '+%Y-%m-%d %H:%M')"
fi

echo "✅ 已提交到 Git"
git log --oneline -3
