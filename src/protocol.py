import modem
import ujson as json
from usr import uuid
import usocket as socket
from usr.threading import Thread, Condition,Event
from usr.logging import getLogger
import umqtt
import request
import ubinascii
import ustruct as struct
import utime
import ucryptolib 

logger = getLogger(__name__)

class JsonMessage(object):

    def __init__(self, kwargs):
        self.kwargs = kwargs
    
    def __str__(self):
        return str(self.kwargs)
    
    def to_bytes(self):
        return json.dumps(self.kwargs)
    
    @classmethod
    def from_bytes(cls, data):
        return cls(json.loads(data))

    def __getitem__(self, key):
        return self.kwargs[key]
    
    def __setitem__(self, key, value): 
        self.kwargs[key] = value

aes_opus_info = {
    "type": "hello",
    "version": 3,
    "transport": "udp",
    "udp": {
        "server": "120.24.160.13",
        "port": 8848,
        "encryption": "aes-128-ctr",
        "key": "263094c3aa28cb42f3965a1020cb21a7",
        "nonce": "01000000ccba9720b4bc268100000000"
    },
    "audio_params": {
        "format": "opus",
        "sample_rate": 16000,
        "channels": 1,
        "frame_duration": 100
    },
    "session_id": "b23ebfe9"
}

'''
OTA 返回的数据格式
{'websocket': {'url': 'wss://api.tenclass.net/xiaozhi/v1/', 'token': 'test-token'}, 
 'mqtt': {'endpoint': 'mqtt.xiaozhi.me', 'publish_topic': 'device-server', 
        'client_id': 'GID_test@@@64_e8_33_48_ec_c0@@@7c18371a-3594-4380-be56-f1e934f4f2fa', 
        'username': 'eyJpcCI6IjIyMC4yMDAuMTI2LjE5In0=', 'password': 'Kduh/1JI4ZyxmyPSDGs0UMvYXZQxw1+clxXl4YOAOFU=', 
        'subscribe_topic': 'null'}, 
 'server_time': {'timezone_offset': 480, 'timestamp': 1755139312182}, 
 'firmware': {'url': '', 'version': '1.0.1'}}
'''
class MqttClient(object):
    def __init__(self):
        self._host = 'mqtt.xiaozhi.me'
        self._port = 8883
        self._username = None
        self._password = None
        self.client_id = None 
        self._keepalive = 120
        self._pub_topic = None
        self._sub_topic = None
        self.udp_socket = None
        self._mqtt_recv = None
        self._udp_recv = None
        self.audio_encryptor = None
        self._running = False  # 添加线程运行标志
        self.udp_connect_event = Event()
        self.mqtt_udp_flag = Event()
        self.ota_get()

    def ota_get(self):
        cli_uuid = str(uuid.uuid4())
        head = {
            'Accept-Language': 'zh-CN',
            'Content-Type': 'application/json',
            'User-Agent': 'kevin-box-2/1.0.1',
            'Device-Id': self.get_mac_address(),
            'Client-Id': cli_uuid
        }
        ota_data = JsonMessage({
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
        })
        ota_url = "https://api.tenclass.net/xiaozhi/ota/"
        #通过OTA得到mqtt的连接参数
        response = request.post(ota_url,data =(ota_data.to_bytes()),headers=head)
        response = response.json()
        print(response)
        self._host = response["mqtt"]["endpoint"]
        self._username = response["mqtt"]["username"]
        self._password = response["mqtt"]["password"]
        self._pub_topic = response["mqtt"]["publish_topic"]
        self._sub_topic = "devices/p2p/#"
        self.client_id = response["mqtt"]["client_id"]
    def __str__(self):
        return "{}(host=\"{}\")".format(type(self).__name__, self._host)

    def __enter__(self):
        self.connect()
        pass
    def is_state_ok(self):
        return self.cli.get_mqttsta() == 0 
    def __exit__(self, *args, **kwargs):
        logger.debug("__exit__ result udp close")
        if not self.mqtt_udp_flag.is_set():
            self.disconnect()
        self.mqtt_udp_flag.clear()
    def connect(self):
        hello_msg = JsonMessage({
            "type": "hello",
            "version": 3,
            "transport": "udp",
            "features": {
                "consistent_sample_rate": True
            },
            "audio_params": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 60
            }
        })
        try:
            self.cli = umqtt.MQTTClient(self.client_id, self._host, self._port, self._username, self._password, keepalive=self._keepalive,ssl=True)
            self.cli.set_callback(self.__handle_mqtt_message)
            logger.info("connecting to mqtt...")
            self._running = True  
            self.cli.connect()
            if self.cli.get_mqttsta() == 0:  # 0表示连接成功
                self._mqtt_recv = Thread(target=self._mqtt_recv_thread)
                self._mqtt_recv.start(stack_size=64)
                self.cli.subscribe(self._sub_topic)
                utime.sleep(1)  # 确保订阅完成
                self.mqtt_send(hello_msg.to_bytes())            
            while not self.udp_connect_event.is_set():
                logger.debug("waitting for udp connection")
                utime.sleep(1)
            if self.udp_connect_event.is_set() :
                logger.debug("mqtt and udp connect success")
            else :
                logger.debug("mqtt and udp connect fail")     

        except Exception as e:
            logger.error("{} connect failed: {}".format(self, e))
            self.cli = None
            return False
        # else:
        #     setattr(self, "__client__", self.cli)

    def disconnect(self):
        self._running = False
        self.udp_connect_event.clear()
        if self.udp_socket:
            self.udp_socket.close()
            self.udp_socket = None
        if self.cli:
            self.cli.disconnect()
            self.cli = None
        # 确保线程完全退出后再清理
        if self._udp_recv:
            self._udp_recv.join()
            self._udp_recv = None
        if self._mqtt_recv:
            self._mqtt_recv.join()
            self._mqtt_recv = None
        else:
            logger.info("receive thread already closed")
    def mqtt_send(self, data):
        """send data to server"""
        #logger.info("send data:{} ".format(data))
        self.cli.publish(self._pub_topic,data)

    def udp_send(self, data):
        if self.audio_encryptor is None:
            self.audio_encryptor = AudioEncryptor(aes_opus_info["udp"]["key"], 
                                                aes_opus_info["udp"]["nonce"])

        encrypt_data = self.audio_encryptor.encrypt_packet(data)
        #logger.debug("send data:{} ".format(encrypt_data))

        ret = self.udp_socket.sendto(encrypt_data,(aes_opus_info["udp"]["server"],aes_opus_info["udp"]["port"]))
        #logger.debug('send %d bytes' % ret)
        
    def set_callback(self, audio_message_handler=None, json_message_handler=None):
        if audio_message_handler is not None and callable(audio_message_handler):
            self.__audio_message_handler = audio_message_handler
        else:
            raise TypeError("audio_message_handler must be callable")
        
        if json_message_handler is not None and callable(json_message_handler):
            self.__json_message_handler = json_message_handler
        else:
            raise TypeError("json_message_handler must be callable")
        
    @staticmethod
    def get_mac_address():
        # mac = str(uuid.UUID(int=int(modem.getDevImei())))[-12:]
        # return ":".join([mac[i:i + 2] for i in range(0, 12, 2)])
        return "64:e8:33:48:ec:c1"
    def __handle_mqtt_message(self,topic,msg):
        global aes_opus_info
        msg = JsonMessage.from_bytes(msg)
        #logger.info("recv data: ", msg)
        if msg["type"] == "hello":
            #logger.info("recv hello msg: ", msg)
            aes_opus_info = msg
            self.audio_encryptor = None  # 强制下次发送时用新配置初始化
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,socket.IPPROTO_UDP)
            self.udp_socket.connect((aes_opus_info['udp']['server'], aes_opus_info['udp']['port']))
            logger.debug("UDP connect to ",aes_opus_info['udp']['server'], aes_opus_info['udp']['port'])
            #self.udp_socket.settimeout(1)  # 设置1秒超时
            self._udp_recv = Thread(target=self._udp_recv_thread)
            self._udp_recv.start(stack_size=128)
            self.udp_connect_event.set()
        elif msg["type"] == "goodbye":
            logger.info("recv goodbye message")
            print(msg)
            aes_opus_info["session_id"] = None  # 清理会话标识
            self.mqtt_udp_flag.set()
            self.disconnect()
            
        else:
            self.__handle_json_message(msg)
    def _mqtt_recv_thread(self):
        while self._running:
            try:
                self.cli.wait_msg()
            except Exception as e:
                if self._running:
                    logger.error("recv_thread error: ", e)
    def _udp_recv_thread(self):
        logger.debug("udp recv thread start run")
        while self._running:
            try:
                
                raw = self.udp_socket.recv(256)
                #logger.info("udp recv: ", raw)

                # 确保加密器已初始化
                if self.audio_encryptor is None:
                    logger.warn("Encryptor not initialized!")
                    continue
                
                decrypted = self.audio_encryptor.decrypt_packet(raw)
                if decrypted is None:
                    logger.warn("The data received via UDP is abnormal.")
                    continue
                self.__handle_audio_message(decrypted)
            # except socket.timeout:
            #     continue  # 超时属于正常情况，继续等
            except Exception as e:
                if self._running:
                    logger.debug("udp recv thread error")
                utime.sleep(1)
            
                

    def __handle_audio_message(self, raw):
        if self.__audio_message_handler is None:
            logger.warn("audio message handler is None, did you forget to set it?")
            return
        try:
            self.__audio_message_handler(raw)
        except Exception as e:
            logger.error("{} handle audio message failed, Exception details: {}".format(self, repr(e)))

    def __handle_json_message(self, msg):
        if self.__json_message_handler is None:
            logger.warn("json message handler is None, did you forget to set it?")
            return
        try:
            self.__json_message_handler(msg)
        except Exception as e:
            logger.debug("{} handle json message failed, Exception details: {}".format(self, repr(e)))

    def listen(self, state, mode="manual"):
            self.mqtt_send(
                JsonMessage(
                    {
                        "session_id": aes_opus_info["session_id"],  # 会话ID
                        "type": "listen",
                        "state": state,  # "start": 开始识别; "stop": 停止识别; "detect": 唤醒词检测
                        "mode": mode  # "auto": 自动停止; "manual": 手动停止; "realtime": 持续监听
                    }
                ).to_bytes()
            )
    
    def wakeword_detected(self, wakeword):
            self.mqtt_send(
                JsonMessage(
                    {
                        "session_id": aes_opus_info["session_id"],
                        "type": "listen",
                        "state": "detect",
                        "text": wakeword  # 唤醒词
                    }
                ).to_bytes()
            )
    
    def abort(self, reason=""):
            self.mqtt_send(
                JsonMessage(
                    {
                        "session_id": aes_opus_info["session_id"],
                        "type": "abort",
                        "reason": reason
                    }
                ).to_bytes()
            )
    
class AudioEncryptor:
    def __init__(self, key_hex, nonce_hex):
        self.key = ubinascii.unhexlify(key_hex)
        self.nonce = nonce_hex
        self.seq_num = 0
        
        # 验证密钥长度
        if len(self.key) != 16:
            raise ValueError("Invalid key length")

    
    def _generate_nonce(self, data_length):
        """nonce生成逻辑"""
        data_length = "{:04x}".format(data_length)
        seq_num = "{:08x}".format(self.seq_num)
        
        return self.nonce[0:4] + data_length + self.nonce[8:24] + seq_num
    
    def encrypt_packet(self, payload):
        """加密音频包"""
        nonce = self._generate_nonce(len(payload))
        nonce = ubinascii.unhexlify(nonce)
        
        # 使用CTR模式加密
        aes = ucryptolib.aes(self.key, ucryptolib.MODE_CTR, nonce)
        encrypted = aes.encrypt(payload)
        
        # 更新序列号
        self.seq_num += 1
        
        # 返回nonce + 加密数据
        return nonce + encrypted
    
    def decrypt_packet(self, raw):
        """解密音频包"""
        if len(raw) < 16:
            logger.warn("Packet too short: {} bytes".format(len(raw)))
            return None
        
        # 提取nonce和密文
        nonce = raw[:16]
        ciphertext = raw[16:]
        
        try:
            # 使用CTR模式解密
            aes = ucryptolib.aes(self.key, ucryptolib.MODE_CTR, nonce)
            return aes.decrypt(ciphertext)
        except Exception as e:
            logger.error("Decrypt failed: {}".format(e))
            return None
