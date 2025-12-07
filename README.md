# 抖音直播间数据爬虫

> 一个专门用于采集抖音直播间数据的高效命令行工具

[![GitHub Stars](https://img.shields.io/github/stars/huey1in/douyin_crawler?style=flat-square&logo=github)](https://github.com/huey1in/douyin_crawler)
[![GitHub Forks](https://img.shields.io/github/forks/huey1in/douyin_crawler?style=flat-square&logo=github)](https://github.com/huey1in/douyin_crawler)
[![Python Version](https://img.shields.io/badge/Python-3.11.9+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**最后测试时间：2025-12-27** | **状态：可用**


## 安装指南

### 1. 基础依赖

```bash
pip install -r requirements.txt
```

---

## 使用方法

### 基本用法

```bash
# 方式一：直接运行主程序
python douyin_live_crawler.py <直播间ID>

# 方式二：使用启动脚本（推荐）
python run.py <直播间ID>
```

**示例：**
```bash
python run.py 646454278948
```

### 高级参数

```bash
python douyin_live_crawler.py <直播间ID> [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--save-interval` | 自动保存间隔（秒） | 300 |
| `--log-level` | 日志级别 (DEBUG/INFO/WARNING/ERROR) | INFO |

**示例：**
```bash
# 每5分钟保存一次，输出DEBUG级别日志
python run.py 646454278948 --save-interval 300 --log-level DEBUG

# 每10分钟保存一次
python run.py 646454278948 --save-interval 600
```

---

## 输出数据格式

采集的数据会自动保存到 `data/live_data/` 目录下

**文件名格式：** `{直播间ID}_{场次}_{日期}.json`

**示例：** `646454278948_1_2025-12-07.json`

### 数据结构示例

```json
{
  "live_id": "646454278948",
  "date": "2025-12-07",
  "session": 1,
  "user_id": "主播用户ID",
  "nickname": "主播昵称",
  "total_viewers": 1000,
  "total_likes": 5000,
  "chat_messages": [
    {
      "timestamp": 1640995200,
      "user_id": "用户ID",
      "nickname": "用户昵称",
      "content": "消息内容",
      "type": "chat"
    }
  ],
  "gifts": {
    "礼物名称": {
      "count": 10,
      "total_value": 1000,
      "senders": ["用户1", "用户2"]
    }
  },
  "members": ["进入直播间的用户昵称"],
  "follows": [
    {
      "timestamp": 1640995200,
      "user_id": "用户ID",
      "nickname": "用户昵称"
    }
  ],
  "stats": {
    "total_chat_messages": 100,
    "total_members": 50,
    "total_follows": 10,
    "total_gift_types": 5,
    "save_time": "2025-12-07T12:00:00"
  }
}
```

---

## 目录结构

```
douyin_crawler/
├── douyin_live_crawler.py    主程序（核心爬虫逻辑）
├── run.py                    启动脚本
├── sign.js                   JavaScript 签名算法
├── requirements.txt          项目依赖列表
├── README.md                 项目说明文档
│
├── protobuf/                 Protocol Buffers 定义
│   ├── __init__.py
│   └── douyin.py
│
└── data/                     数据存储目录（自动创建）
    ├── live_data/            直播数据（JSON 文件）
    └── logs/                 日志文件
```

---

## 运行日志

程序运行时会输出实时日志：

```
2025-12-07 12:00:00,000 - INFO - 开始抓取直播间: 646454278948
2025-12-07 12:00:01,123 - INFO - 使用 py_mini_racer 作为JavaScript运行时
2025-12-07 12:00:02,456 - INFO - WebSocket连接已建立
2025-12-07 12:00:03,789 - INFO - [聊天] 用户A: 主播好棒！
2025-12-07 12:00:04,012 - INFO - [礼物] 用户B 送出 玫瑰 x1
2025-12-07 12:00:05,345 - INFO - [进入] 用户C 进入直播间
2025-12-07 12:00:06,678 - INFO - [点赞] 收到 5 个点赞
2025-12-07 12:05:00,234 - INFO - 数据已保存到: data/live_data/646454278948_1_2025-12-07.json
```

---

## 停止程序

在终端中按 `Ctrl+C` 即可优雅停止程序，程序会自动保存当前数据。

```bash
^C
正在停止抓取...
数据已保存到: data/live_data/646454278948_1_2025-12-07.json
抓取已停止
```

---

## 免责声明

本代码库所有代码均只用于**学习研究交流**，严禁用于包括但不限于：
- 商业谋利
- 破坏系统
- 盗取个人信息等不良不法行为

违反此声明使用所产生的一切后果均由违反声明使用者承担。

---

**如有问题或建议，欢迎提交 Issue 或 Pull Request！**
