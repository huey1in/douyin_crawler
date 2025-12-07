#!/usr/bin/env python3
"""
抖音直播间数据爬虫
"""

import codecs
import gzip
import hashlib
import json
import os
import random
import re
import string
import subprocess
import threading
import time
import urllib.parse
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch
import sys
import argparse
import logging

import requests
import websocket
from protobuf.douyin import *

# JavaScript运行时
_js_runtime = None

def get_js_runtime():
    """获取JavaScript运行时环境"""
    global _js_runtime
    
    if _js_runtime is not None:
        return _js_runtime
        
    try:
        # 使用 py_mini_racer 作为JavaScript运行时
        from py_mini_racer import MiniRacer
        _js_runtime = MiniRacer()
        logger.info("使用 py_mini_racer 作为JavaScript运行时")
        return _js_runtime
    except ImportError:
        logger.error("未安装 py_mini_racer")
        logger.error("请安装: pip install mini-racer")
        return None
    except Exception as e:
        logger.error(f"初始化JavaScript运行时出错: {str(e)}")
        return None

def clear_js_runtime_cache():
    """清理JavaScript运行时缓存"""
    global _js_runtime
    _js_runtime = None

def generateMsToken(length=107):
    """
    产生请求头部cookie中的msToken字段，其实为随机的107位字符
    :param length:字符位数
    :return:msToken
    """
    random_str = ""
    base_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789="
    for _ in range(length):
        random_str += base_str[random.randint(0, len(base_str) - 1)]
    return random_str

# 设置日志
# 确保日志目录存在
os.makedirs('data/logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/crawler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    possible_paths = [
        os.path.join(base_path, relative_path),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path),
        os.path.join(os.getcwd(), relative_path),
        os.path.abspath(relative_path),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return os.path.join(base_path, relative_path)

@contextmanager
def patched_popen_encoding(encoding='utf-8'):
    original_popen_init = subprocess.Popen.__init__
    
    def new_popen_init(self, *args, **kwargs):
        kwargs['encoding'] = encoding
        original_popen_init(self, *args, **kwargs)
    
    with patch.object(subprocess.Popen, '__init__', new_popen_init):
        yield

def generateSignature(wss, script_file='sign.js'):
    """生成签名"""
    params = ("live_id,aid,version_code,webcast_sdk_version,"
             "room_id,sub_room_id,sub_channel_id,did_rule,"
             "user_unique_id,device_platform,device_type,ac,"
             "identity").split(',')
    
    try:
        wss_params = urllib.parse.urlparse(wss).query.split('&')
        wss_maps = {i.split('=')[0]: i.split("=")[-1] for i in wss_params if '=' in i}
        tpl_params = [f"{i}={wss_maps.get(i, '')}" for i in params]
        param = ','.join(tpl_params)
        
        md5 = hashlib.md5()
        md5.update(param.encode())
        md5_param = md5.hexdigest()
        
        js_runtime = get_js_runtime()
        if not js_runtime:
            logger.error("无法获取JavaScript运行时")
            return None
            
        # 读取JavaScript文件
        script_path = get_resource_path(script_file)
        if not os.path.exists(script_path):
            logger.error(f"签名脚本文件不存在: {script_path}")
            return None
            
        with open(script_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        
        # 为非浏览器环境添加全局对象补丁，确保兼容性
        # 这解决了 py_mini_racer 中缺少window/document等全局对象的问题
        global_patch = """
var window = globalThis;
var document = {};
var navigator = {userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'};
var self = globalThis;
var global = globalThis;
"""
        # 将补丁代码插入到JavaScript代码开头
        js_code_with_patch = global_patch + js_code
        
        # 使用 py_mini_racer 执行 JavaScript
        js_runtime.eval(js_code_with_patch)
        signature = js_runtime.call("get_sign", md5_param)
            
        return signature
            
    except Exception as e:
        logger.error(f"生成签名时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        # 清理缓存便于重试
        clear_js_runtime_cache()
        return None

class DouyinLiveCrawler:
    def __init__(self, live_id, auto_save_interval=300):
        """初始化直播爬虫"""
        self.__ttwid = None
        self.__room_id = None
        self.live_id = live_id
        self.live_url = "https://live.douyin.com/"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # WebSocket相关
        self.ws = None
        self.ws_thread = None
        self.heartbeat_thread = None
        self.is_running = True
        
        # 数据统计
        self.data_dir = os.path.join("data", "live_data")
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.session_count = self._get_next_session_count()
        
        # 数据存储
        self.data = {
            "live_id": live_id,
            "date": self.today,
            "session": self.session_count,
            "user_id": "",
            "nickname": "",
            "total_viewers": 0,
            "total_likes": 0,
            "chat_messages": [],
            "gifts": {},
            "members": set(),
            "follows": []
        }
        
        # 去重集合
        self.message_cache = {
            "members": set(),
            "gifts": set()
        }
        self.cache_expire_time = 10
        self.last_cache_clean = time.time()
        
        # 自动保存设置
        self.auto_save_interval = auto_save_interval
        self.auto_save_thread = None
        self.auto_save_running = False
        
        # 状态回调
        self.status_callback = None
        self.is_live = True
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs("data/logs", exist_ok=True)

    def _get_next_session_count(self):
        """获取下一个场次编号"""
        import glob
        pattern = os.path.join(self.data_dir, f"{self.live_id}_*_*.json")
        files = glob.glob(pattern)
        max_count = 0
        
        for file in files:
            try:
                count = int(os.path.basename(file).split("_")[1])
                max_count = max(max_count, count)
            except (ValueError, IndexError):
                continue
                
        return max_count + 1

    @property
    def ttwid(self):
        """
        产生请求头部cookie中的ttwid字段，访问抖音网页版直播间首页可以获取到响应cookie中的ttwid
        :return: ttwid
        """
        if self.__ttwid:
            return self.__ttwid
        headers = {
            "User-Agent": self.user_agent,
        }
        try:
            response = requests.get(self.live_url, headers=headers)
            response.raise_for_status()
        except Exception as err:
            logger.error(f"请求直播首页失败: {err}")
        else:
            self.__ttwid = response.cookies.get('ttwid')
            return self.__ttwid
    
    @property
    def room_id(self):
        """
        根据直播间的地址获取到真正的直播间roomId
        :return:room_id
        """
        if self.__room_id:
            return self.__room_id
        url = self.live_url + self.live_id
        headers = {
            "User-Agent": self.user_agent,
            "cookie": f"ttwid={self.ttwid}&msToken={generateMsToken()}; __ac_nonce=0123407cc00a9e438deb4",
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except Exception as err:
            logger.error(f"请求直播间页面失败: {err}")
        else:
            match = re.search(r'roomId\\":\\"(\d+)\\"', response.text)
            if match is None or len(match.groups()) < 1:
                logger.warning("未找到roomId，可能是未开播状态，使用live_id作为fallback")
                self.__room_id = self.live_id
                self.is_live = False
            else:
                self.__room_id = match.group(1)
                
            return self.__room_id
    
    def start(self):
        """启动爬虫"""
        logger.info(f"开始抓取直播间: {self.live_id}")
        
        # 启动自动保存线程
        self.auto_save_running = True
        self.auto_save_thread = threading.Thread(target=self._auto_save_worker)
        self.auto_save_thread.daemon = True
        self.auto_save_thread.start()
        
        # 启动WebSocket连接线程
        self.ws_thread = threading.Thread(target=self._connectWebSocket)
        self.ws_thread.daemon = True
        self.ws_thread.start()
    
    def stop(self):
        """停止爬虫"""
        try:
            logger.info("正在停止抓取...")
            
            self.is_running = False
            self.auto_save_running = False
            
            if self.ws:
                try:
                    self.ws.close()
                except Exception as e:
                    logger.warning(f"关闭WebSocket时出错: {e}")
                    
            # 保存最终数据
            self._save_data()
            clear_js_runtime_cache()
            
            logger.info("抓取已停止")
            
        except Exception as e:
            logger.error(f"停止抓取时出错: {e}")

    def _connectWebSocket(self):
        """连接WebSocket"""
        retry_count = 0
        max_retries = 3
        retry_delay = 3
        
        while self.is_running and retry_count < max_retries:
            try:
                # 生成WebSocket URL
                wss_url = self._generate_ws_url()
                signature = generateSignature(wss_url)
                if not signature:
                    logger.error("生成签名失败")
                    return
                    
                final_url = f"{wss_url}&signature={signature}"
                
                headers = {
                    "cookie": f"ttwid={self.ttwid}",
                    "user-agent": self.user_agent,
                }
                
                logger.info("开始连接WebSocket...")
                
                # 创建WebSocket连接
                self.ws = websocket.WebSocketApp(
                    final_url,
                    header=[f"User-Agent: {self.user_agent}", f"Cookie: ttwid={self.ttwid}"],
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                # 启动心跳线程
                if hasattr(self, 'heartbeat_thread') and self.heartbeat_thread:
                    try:
                        self.heartbeat_thread.join(timeout=1)
                    except:
                        pass
                self.heartbeat_thread = threading.Thread(target=self._heartbeat)
                self.heartbeat_thread.daemon = True
                self.heartbeat_thread.start()
                
                # 运行WebSocket客户端（添加ping参数）
                self.ws.run_forever(ping_timeout=10, ping_interval=30)
                break
                
            except Exception as e:
                retry_count += 1
                logger.error(f"WebSocket连接异常 (尝试 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(retry_delay)
                else:
                    logger.error("WebSocket连接失败，已达最大重试次数")
                    break

    def _generate_ws_url(self):
        """生成WebSocket连接URL"""
        return ("wss://webcast5-ws-web-hl.douyin.com/webcast/im/push/v2/?"
                f"aid=6383&live_id=1&device_platform=web&room_id={self.room_id}"
                "&support_wrds=1&version_code=180800&webcast_sdk_version=1.0.14"
                "&update_version_code=1.0.14&compress=gzip&internal_ext="
                f"internal_src:dim|wss_push_room_id:{self.room_id}|wss_push_did"
                ":7319483754668557238|fetch_time:1721106114633|seq:1|"
                "wss_info:0-1721106114633-0-0&cursor=d-1_u-1_h-1_t-1721106114633"
                "&host=https://live.douyin.com&im_path=/webcast/im/fetch/&user_unique_id="
                f"&identity=audience&need_persist_msg_count=15&heartbeatDuration=0")
    
    
    def _on_open(self, ws):
        """WebSocket连接打开"""
        logger.info("WebSocket连接已建立")
    
    def _on_message(self, ws, message):
        """处理WebSocket消息"""
        try:
            # 先解析PushFrame包装
            package = PushFrame().parse(message)
            
            # 解压缩payload
            compressed_data = gzip.decompress(package.payload)
            
            # 解析protobuf消息
            response = Response().parse(compressed_data)
            
            # 如果需要ACK，发送确认消息
            if response.need_ack:
                ack = PushFrame(
                    log_id=package.log_id,
                    payload_type='ack',
                    payload=response.internal_ext.encode('utf-8')
                ).SerializeToString()
                ws.send(ack, websocket.ABNF.OPCODE_BINARY)
            
            # 处理消息列表
            for msg in response.messages_list:
                self._process_message(msg)
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            logger.debug(f"消息内容: {message[:50]}...")
    
    def _on_error(self, ws, error):
        """WebSocket错误处理"""
        logger.error(f"WebSocket错误: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭"""
        logger.info("WebSocket连接已关闭")
        
        # 如果还在运行状态，尝试重连
        if self.is_running:
            time.sleep(5)
            logger.info("尝试重新连接...")
            threading.Thread(target=self._connectWebSocket).start()
    
    def _heartbeat(self):
        """心跳保持连接"""
        while self.is_running and self.ws and self.ws.sock:
            try:
                # 发送心跳包 - 使用protobuf格式
                ping_msg = PushFrame(
                    payload_type='hb',
                    payload=b'',
                    log_id=int(time.time() * 1000)
                ).SerializeToString()
                
                self.ws.send(ping_msg, websocket.ABNF.OPCODE_BINARY)
                logger.debug("发送心跳包...")
                time.sleep(10)  # 每10秒发送一次心跳包
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                break
    
    def _process_message(self, msg):
        """处理具体消息类型"""
        try:
            method = msg.method
            
            if method == "WebcastChatMessage":
                self._process_chat_message(msg)
            elif method == "WebcastGiftMessage":
                self._process_gift_message(msg)
            elif method == "WebcastMemberMessage":
                self._process_member_message(msg)
            elif method == "WebcastLikeMessage":
                self._process_like_message(msg)
            elif method == "WebcastSocialMessage":
                self._process_follow_message(msg)
            elif method == "WebcastRoomUserSeqMessage":
                self._process_viewer_count(msg)
                
        except Exception as e:
            logger.error(f"处理消息类型 {msg.method} 失败: {e}")
    
    def _process_chat_message(self, msg):
        """处理聊天消息"""
        try:
            chat_msg = ChatMessage().parse(msg.payload)
            user = chat_msg.user
            content = chat_msg.content
            
            message_data = {
                "timestamp": int(time.time()),
                "user_id": str(user.id),
                "nickname": user.nick_name,
                "content": content,
                "type": "chat"
            }
            
            self.data["chat_messages"].append(message_data)
            logger.info(f"[聊天] {user.nick_name}: {content}")
            
        except Exception as e:
            logger.error(f"处理聊天消息失败: {e}")
    
    def _process_gift_message(self, msg):
        """处理礼物消息"""
        try:
            gift_msg = GiftMessage().parse(msg.payload)
            user = gift_msg.user
            gift = gift_msg.gift
            
            gift_name = gift.name
            gift_count = gift_msg.repeat_count
            gift_value = gift.diamond_count * gift_count
            
            # 统计礼物
            if gift_name not in self.data["gifts"]:
                self.data["gifts"][gift_name] = {
                    "count": 0,
                    "total_value": 0,
                    "senders": set()
                }
            
            # 确保senders始终是set类型
            if not isinstance(self.data["gifts"][gift_name]["senders"], set):
                self.data["gifts"][gift_name]["senders"] = set(self.data["gifts"][gift_name]["senders"])
            
            self.data["gifts"][gift_name]["count"] += gift_count
            self.data["gifts"][gift_name]["total_value"] += gift_value
            self.data["gifts"][gift_name]["senders"].add(user.nick_name)
            
            logger.info(f"[礼物] {user.nick_name} 送出 {gift_name} x{gift_count}")
            
        except Exception as e:
            logger.error(f"处理礼物消息失败: {e}")
    
    def _process_member_message(self, msg):
        """处理观众进入消息"""
        try:
            member_msg = MemberMessage().parse(msg.payload)
            user = member_msg.user
            
            # 去重检查
            user_key = str(user.id)
            if user_key not in self.message_cache["members"]:
                # 确保members是set类型
                if not isinstance(self.data["members"], set):
                    self.data["members"] = set(self.data["members"])
                    
                self.message_cache["members"].add(user_key)
                self.data["members"].add(user.nick_name)
                logger.info(f"[进入] {user.nick_name} 进入直播间")
            
        except Exception as e:
            logger.error(f"处理观众进入消息失败: {e}")
    
    def _process_like_message(self, msg):
        """处理点赞消息"""
        try:
            like_msg = LikeMessage().parse(msg.payload)
            count = like_msg.count
            self.data["total_likes"] += count
            
            if count > 1:
                logger.info(f"[点赞] 收到 {count} 个点赞")
                
        except Exception as e:
            logger.error(f"处理点赞消息失败: {e}")
    
    def _process_follow_message(self, msg):
        """处理关注消息"""
        try:
            social_msg = SocialMessage().parse(msg.payload)
            user = social_msg.user
            
            follow_data = {
                "timestamp": int(time.time()),
                "user_id": str(user.id),
                "nickname": user.nick_name
            }
            
            self.data["follows"].append(follow_data)
            logger.info(f"[关注] {user.nick_name} 关注了主播")
            
        except Exception as e:
            logger.error(f"处理关注消息失败: {e}")
    
    def _process_viewer_count(self, msg):
        """处理观众人数消息"""
        try:
            seq_msg = RoomUserSeqMessage().parse(msg.payload)
            total_user = seq_msg.total_user
            self.data["total_viewers"] = total_user
            
        except Exception as e:
            logger.error(f"处理观众人数消息失败: {e}")
    
    def _auto_save_worker(self):
        """自动保存工作线程"""
        while self.auto_save_running:
            time.sleep(self.auto_save_interval)
            if self.auto_save_running:
                self._save_data()
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            # 转换set为list以便JSON序列化
            data_copy = self.data.copy()
            data_copy["members"] = list(data_copy["members"])
            
            # 处理礼物数据中的set
            for gift_name, gift_data in data_copy["gifts"].items():
                if "senders" in gift_data and isinstance(gift_data["senders"], set):
                    gift_data["senders"] = list(gift_data["senders"])
            
            # 添加统计信息
            data_copy["stats"] = {
                "total_chat_messages": len(data_copy["chat_messages"]),
                "total_members": len(data_copy["members"]),
                "total_follows": len(data_copy["follows"]),
                "total_gift_types": len(data_copy["gifts"]),
                "save_time": datetime.now().isoformat()
            }
            
            filename = f"{self.live_id}_{self.session_count}_{self.today}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_copy, f, ensure_ascii=False, indent=2)
                
            logger.info(f"数据已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存数据失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='抖音直播间数据爬虫')
    parser.add_argument('live_id', help='直播间ID')
    parser.add_argument('--save-interval', type=int, default=300, 
                       help='自动保存间隔(秒)，默认300秒')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    crawler = DouyinLiveCrawler(args.live_id, args.save_interval)
    
    try:
        crawler.start()
        
        # 主循环
        logger.info("爬虫已启动，按 Ctrl+C 停止")
        while crawler.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    except Exception as e:
        logger.error(f"运行时错误: {e}")
    finally:
        crawler.stop()

if __name__ == "__main__":
    main()