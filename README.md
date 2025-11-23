# 抖音直播间数据爬虫

这是一个专门用于采集抖音直播间数据的命令行工具，可以实时抓取直播间的弹幕、礼物、观众进入、点赞、关注等数据。
## 最后一次测试可用时间：2025-11-23

## 功能特点

- 实时采集直播间数据（弹幕、礼物、观众、点赞、关注等）
- 自动保存数据到JSON文件
- 支持断线重连
- 详细的日志记录
- 命令行参数配置
- 数据去重和统计

## 安装依赖

```bash
pip install -r requirements.txt
```

### JavaScript 运行时环境

程序需要JavaScript运行时来执行签名算法，支持以下两种：

1. **PyExecJS** (推荐，已包含在requirements.txt中)
2. **py_mini_racer** (可选，性能更好)

如果想使用更高性能的mini_racer，可以额外安装：
```bash
pip install mini-racer
```

## 使用方法

### 基本用法

```bash
python douyin_live_crawler.py <直播间ID>
```

或者使用启动脚本：
```bash
python run.py <直播间ID>
```

例如：
```bash
python douyin_live_crawler.py 123456789
# 或
python run.py 123456789
```

### 高级参数

```bash
python douyin_live_crawler.py <直播间ID> [选项]

选项:
  --save-interval SECONDS  自动保存间隔(秒)，默认300秒
  --log-level LEVEL       日志级别: DEBUG, INFO, WARNING, ERROR (默认: INFO)
```

例如：
```bash
# 设置5分钟自动保存，DEBUG级别日志
python douyin_live_crawler.py 123456789 --save-interval 300 --log-level DEBUG
```

## 输出数据格式

采集的数据会自动保存到 `data/live_data/` 目录下，文件名格式为：
```
{直播间ID}_{场次}_{日期}.json
```

数据结构：
```json
{
  "live_id": "直播间ID",
  "date": "2024-01-01",
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
    "save_time": "2024-01-01T12:00:00"
  }
}
```

## 目录结构

```
douyin_crawler_cli/
├── douyin_live_crawler.py  # 主程序
├── run.py                  # 启动脚本
├── sign.js                 # 签名算法文件
├── requirements.txt        # 依赖包列表
├── README.md              # 使用说明
├── protobuf/              # Protocol Buffers定义
│   ├── __init__.py
│   └── douyin.py
└── data/                  # 数据存储目录
    ├── live_data/         # 直播数据
    └── logs/              # 日志文件
```

## 运行日志

程序运行时会输出实时日志：
```
2024-01-01 12:00:00 - INFO - 开始抓取直播间: 123456789
2024-01-01 12:00:01 - INFO - WebSocket连接已建立
2024-01-01 12:00:02 - INFO - 💬 用户A: 主播好棒！
2024-01-01 12:00:03 - INFO - 🎁 用户B 送出 玫瑰 x1
2024-01-01 12:00:04 - INFO - 👥 用户C 进入直播间
2024-01-01 12:00:05 - INFO - ❤️ 用户D 关注了主播
```

## 停止程序

在终端中按 `Ctrl+C` 即可优雅停止程序，程序会自动保存当前数据。

## 注意事项

1. 请确保网络连接稳定
2. 首次运行时程序会自动创建必要的目录
3. 数据文件较大时请注意磁盘空间
4. 本工具仅供学习研究使用，请遵守相关平台的服务条款

## 免责声明

本代码库所有代码均只用于学习研究交流，严禁用于包括但不限于商业谋利、破坏系统、盗取个人信息等不良不法行为，违反此声明使用所产生的一切后果均由违反声明使用者承担。
