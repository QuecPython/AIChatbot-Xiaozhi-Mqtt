from usr.protocol import *
import utime
import usocket as socket 
import umqtt
import ujson as json
from usr import uuid
import request
import _thread
uuid = str(uuid.uuid4())
#print(uuid)
head = {
'Accept-Language': 'zh-CN',
'Content-Type': 'application/json',
'User-Agent': 'kevin-box-2/1.0.1',
'Device-Id': '64:e8:33:48:ec:c7',
'Client-Id': uuid
}

ota_data = {
  "application": {
    "version": "1.0.1",
    "elf_sha256": "c8a8ecb6d6fbcda682494d9675cd1ead240ecf38bdde75282a42365a0e396033"
  },
  "board": {
    "type": "kevin-box",
    "name": "kevin-box-2",
    "carrier": "CHINA UNICOM",
    "csq": "22",
    "imei": "****",
    "iccid": "89860125801125426850"
  }
}

aes_opus_info = {
    "type": "hello",
    "version": 3,
    "transport": "udp",
    "udp": {
        "server": "120.24.160.13",
        "port": 8848,
        "encryption": "aes-128-ctr",
        "key": "fe876613dedf5ae64e85b6b7325b31cd",
        "nonce": "0100000077724a860000000000000000"
    },
    "audio_params": {
        "format": "opus",
        "sample_rate": 16000,
        "channels": 1,
        "frame_duration": 100
    },
    "session_id": "bfabef2b"
}
url = "https://api.tenclass.net/xiaozhi/ota/"

UDP_IP = None
UDP_PORT = None

#通过OTA得到mqtt的连接参数
response = request.post(url,data =json.dumps(ota_data),headers=head)
response = response.json()
print(response)
# MQTT_HOST = response["mqtt"]["endpoint"]
# MQTT_USERNAME = response["mqtt"]["username"]
# MQTT_PASSWORD = response["mqtt"]["password"]
# publish_topic = response["mqtt"]["publish_topic"]
# MQTT_client_id = response["mqtt"]["client_id"]
# MAC_ADDR='64:e8:33:48:ec:c7'
# session_id = None
# class JsonMessage(object):

#     def __init__(self, kwargs):
#         self.kwargs = kwargs
    
#     def __str__(self):
#         return str(self.kwargs)
    
#     def to_bytes(self):
#         return json.dumps(self.kwargs)
    
#     @classmethod
#     def from_bytes(cls, data):
#         return cls(json.loads(data))

#     def __getitem__(self, key):
#         return self.kwargs[key]

# hello_msg = {
#   "type": "hello",
#   "version": 3,
#   "transport": "mqtt",
#   "features": {
#     "consistent_sample_rate": True
#   },
#   "audio_params": {
#     "format": "opus",
#     "sample_rate": 16000,
#     "channels": 1,
#     "frame_duration": 100
#   }
# }
# def recv_mqtt(cli):
#     try:
#         cli.wait_msg()
#     except Exception as e:
#         print("MQTT Error:", e)

# def recv_udp(sock):
#     try:
#         sock.recv(1024)
#     except Exception as e:
#         print("UDP Error:", e)
# def sub_cb(topic, msg):
#     print("topic: {} recv msg: {}".format(topic,json.loads(msg)))
#     msg = json.loads(msg)
#     global UDP_IP, UDP_PORT,session_id
#     if msg['type'] == 'hello':
#         UDP_IP = response["udp"]["server"]
#         UDP_PORT = response["udp"]["port"]
#         session_id = msg['session_id']

# cli = umqtt.MQTTClient(client_id=MQTT_client_id, server=MQTT_HOST, port=8883, user=MQTT_USERNAME, password=MQTT_PASSWORD,keepalive=240,ssl=True, ssl_params={},reconn=True,version=4)
# cli.set_callback(sub_cb)
# print("Connecting to MQTT")
# cli.connect()
# subscribe_Topic = "devices/p2p/#" #+ MQTT_client_id #+ MAC_ADDR.replace(':', '_')
# cli.subscribe(subscribe_Topic,qos=1)
# mqtt_recv = _thread.start_new_thread(recv_mqtt, (cli,))
# if cli.publish(publish_topic,json.dumps(hello_msg)):
#     print("Publish topic:", publish_topic, "message:", json.dumps(hello_msg))
#     print("Publish success")
# while True:
#     utime.sleep(5)
#     cli.publish(publish_topic,json.dumps({
#                         "session_id": session_id,
#                         "type": "listen",
#                         "state": "detect",
#                         "text": "小智"  # 唤醒词
#                     }))


# import usocket

# #cli.mqtt_recv_thread()
#  # 创建一个socket实例
# sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM,usocket.IPPROTO_UDP)
# # 建立连接
# utime.sleep(10)
# sock.connect((UDP_IP,UDP_PORT))
# # 向服务端发送消息
# cli.listen("start")
# ret=sock.send('616816161619')
# print('send %d bytes' % ret)

# #接收服务端消息
# data=sock.recv(256)
# print('recv %s bytes:' % len(data))
# print(data.decode())
# utime.sleep(3)






