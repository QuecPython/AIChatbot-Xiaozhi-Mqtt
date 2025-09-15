"""
提高 CPU 主频: AT+LOG=17,5
"""
import utime
import gc
from machine import ExtInt,Pin
from usr.protocol import MqttClient
from usr.utils import ChargeManager, AudioManager, NetManager, TaskManager
from usr.threading import Thread, Event, Condition
from usr.logging import getLogger
from usr.ui import *
import sys_bus


logger = getLogger(__name__)


class Application(object):

    def __init__(self):

        Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_PD, 1)
        self.prev_emoj = None        
        
        #初始化UI
        self.lvgl_manager = lvglManager()
        # 初始化充电管理
        self.charge_manager = ChargeManager()

        # 初始化音频管理
        self.audio_manager = AudioManager()
        self.audio_manager.set_kws_cb(self.on_keyword_spotting)
        self.audio_manager.set_vad_cb(self.on_voice_activity_detection)

        # 初始化网络管理
        self.net_manager = NetManager()

        # 初始化任务调度器
        self.task_manager = TaskManager()

        # 初始化协议
        self.__protocol = MqttClient()
        self.__protocol.set_callback(
            audio_message_handler=self.on_audio_message,
            json_message_handler=self.on_json_message
        )

        self.__working_thread = None
        self.__record_thread = None
        self.__record_thread_stop_event = Event()
        self.__voice_activity_event = Event()
        self.__keyword_spotting_event = Event()

        self.last_msg = None

    def __record_thread_handler(self):
        """纯粹是为了kws&vad能识别才起的线程持续读音频"""
        logger.debug("record thread handler enter")
        count = 0
        while not self.__record_thread_stop_event.is_set():
            self.audio_manager.opus_read()
            utime.sleep_ms(5)
        logger.debug("record thread handler exit")

    def start_kws(self):
        self.audio_manager.start_kws()
        self.__record_thread_stop_event.clear()
        self.__record_thread = Thread(target=self.__record_thread_handler)
        self.__record_thread.start(stack_size=64)
    
    def stop_kws(self):
        self.__record_thread_stop_event.set()
        self.__record_thread.join()
        self.audio_manager.stop_kws()

    def start_vad(self):
        self.audio_manager.start_vad()
    
    def stop_vad(self):
        self.audio_manager.stop_vad()

    def __working_thread_handler(self):
        t = Thread(target=self.__chat_process)
        t.start(stack_size=64)
        self.__keyword_spotting_event.wait()
        self.stop_kws()
        t.join()
        self.start_kws()

    def __chat_process(self):
        self.start_vad()
        try:
            with self.__protocol:
                #self.__protocol.wakeword_detected("小智")
                logger.debug("connect xiaozhiAI success")
                is_listen_flag = False
                while True:
                    data = self.audio_manager.opus_read()
                    if self.__voice_activity_event.is_set():
                        # 有人声
                        if not is_listen_flag:
                            self.__protocol.listen("start")
                            is_listen_flag = True
                        self.__protocol.udp_send(data)
                    else:
                        if is_listen_flag:
                            self.__protocol.listen("stop")
                            is_listen_flag = False
                    if not self.__protocol.is_state_ok():
                        logger.info("mqtt client is not ok")
                        break
                    #logger.debug("read opus data length: {}".format(len(data)))

        except Exception as e:
            logger.debug("working thread handler got Exception: {}".format(repr(e)))
        finally:
            logger.debug("working thread handler exit")
            self.stop_vad()
            sys_bus.publish("update_emoji","sleepy")
        
    def on_keyword_spotting(self, state):
        logger.info("on_keyword_spotting: {}".format(state))
        print("state: ",state)
        if state[0] == 0:
            # 唤醒词触发
            if self.__working_thread is not None and self.__working_thread.is_running():
                return
            self.__working_thread = Thread(target=self.__working_thread_handler)
            self.__working_thread.start()
            self.__keyword_spotting_event.clear()
        else:
            self.__keyword_spotting_event.set()


    def on_voice_activity_detection(self, state):
        logger.info("on_voice_activity_detection: {}".format(state))
        if state == 1:
            if self.__protocol.is_state_ok():  # 状态正常
                self.__protocol.abort()
            self.__voice_activity_event.set()  # 有人声
        else:
            self.__voice_activity_event.clear()  # 无人声

    def on_audio_message(self, raw):
        # raise NotImplementedError("on_audio_message not implemented")
        self.audio_manager.opus_write(raw)

    def on_json_message(self, msg):
        return getattr(self, "handle_{}_message".format(msg["type"]))(msg)

    def handle_stt_message(data, msg):
        logger.info("send msg: ",msg["text"])
        #raise NotImplementedError("handle_stt_message not implemented")
    
    def handle_mcp_message(self, msg):
        #logger.info('收到MCP消息',msg)
        payload = msg["payload"]
        method = payload["method"]
        id = payload.get('id')
        if method == 'tools/call':
            params = payload["params"]
            tool_name = params["name"]
            arguments = params["arguments"]
            if tool_name == 'self.audio_speaker.get_volume':
                volume = self.audio_manager.get_volume()
                result = {"volume": volume}
                self.__protocol.mcp_tool_call(id, 'self.audio_speaker.get_volume', iserror = False,result = result)
                return
            elif tool_name == 'self.audio_speaker.set_volume':
                volume = arguments["volume"]
                self.audio_manager.set_volume(volume)
                result = {"volume": volume}
                self.__protocol.mcp_tool_call(id, 'self.audio_speaker.set_volume', iserror = False,result = result)
            else:
                self.__protocol.mcp_tool_call(id,tool_name,iserror = False)
        else:
            self.__protocol.handle_mcptool_message(method,id)

        #raise NotImplementedError("handle_mcp_message not implemented")

    def handle_tts_message(self, msg):
        try:
            if msg["text"] != self.last_msg:
                logger.info(msg["text"])
                self.last_msg = msg["text"]
        except:
            pass
        #raise NotImplementedError("handle_tts_message not implemented")

#"happy" "cool"  "angry"  "think"
# ... existing code ...
    def handle_llm_message(data, msg):
        #logger.info("handle_llm_message: ", msg)
        sys_bus.publish("update_emoji",msg["emotion"])
        #raise NotImplementedError("handle_llm_message not implemented")
        
    def handle_iot_message(data, msg):
        raise NotImplementedError("handle_iot_message not implemented")
        

    def run(self):
        self.charge_manager.enable_charge()
        self.audio_manager.open_opus()
        self.start_kws()

if __name__ == "__main__":
    app = Application()
    app.run()