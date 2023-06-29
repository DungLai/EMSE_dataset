import os
import time
from datetime import datetime

import itchat
import requests
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup

import city_dict


class GFWeather:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36",
    }
    dictum_channel_name = {1: 'ONEâä¸ä¸ª', 2: 'è¯é¸(æ¯æ¥è±è¯­)', 3: 'åå³æè¯'}

    def __init__(self):
        self.girlfriend_list, self.alarm_hour, self.alarm_minute, self.dictum_channel = self.get_init_data()

    def get_init_data(self):
        '''
        åå§ååºç¡æ°æ®
        :return:
        '''
        with open('_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=yaml.Loader)

        alarm_timed = config.get('alarm_timed').strip()
        init_msg = f"æ¯å¤©å®æ¶åéæ¶é´ï¼{alarm_timed}\n"

        dictum_channel = config.get('dictum_channel', -1)
        init_msg += f"æ ¼è¨è·åæ¸ éï¼{self.dictum_channel_name.get(dictum_channel, 'æ ')}\n"

        girlfriend_list = []
        girlfriend_infos = config.get('girlfriend_infos')
        for girlfriend in girlfriend_infos:
            girlfriend.get('wechat_name').strip()
            # æ ¹æ®åå¸åç§°è·ååå¸ç¼å·ï¼ç¨äºæ¥è¯¢å¤©æ°ãæ¥çæ¯æçåå¸ä¸ºï¼http://cdn.sojson.com/_city.json
            city_name = girlfriend.get('city_name').strip()
            city_code = city_dict.city_dict.get(city_name)
            if not city_code:
                print('æ¨è¾å¥çåå¸æ æ³æ¶åå°å¤©æ°ä¿¡æ¯')
                break
            girlfriend['city_code'] = city_code
            girlfriend_list.append(girlfriend)

            print_msg = f"å¥³æåçå¾®ä¿¡æµç§°ï¼{girlfriend.get('wechat_name')}\n\tå¥³åæå¨åå¸åç§°ï¼{girlfriend.get('city_name')}\n\t" \
                f"å¨ä¸èµ·çç¬¬ä¸å¤©æ¥æï¼{girlfriend.get('start_date')}\n\tæåä¸å¥ä¸ºï¼{girlfriend.get('sweet_words')}\n"
            init_msg += print_msg

        print(u"*" * 50)
        print(init_msg)

        hour, minute = [int(x) for x in alarm_timed.split(':')]
        return girlfriend_list, hour, minute, dictum_channel

    def is_online(self, auto_login=False):
        '''
        å¤æ­æ¯å¦è¿å¨çº¿,
        :param auto_login:True,å¦ææçº¿äºåèªå¨ç»å½ã
        :return: True ï¼è¿å¨çº¿ï¼False ä¸å¨çº¿äº
        '''

        def online():
            '''
            éè¿è·åå¥½åä¿¡æ¯ï¼å¤æ­ç¨æ·æ¯å¦è¿å¨çº¿
            :return: True ï¼è¿å¨çº¿ï¼False ä¸å¨çº¿äº
            '''
            try:
                if itchat.search_friends():
                    return True
            except:
                return False
            return True

        if online():
            return True
        # ä»ä»å¤æ­æ¯å¦å¨çº¿
        if not auto_login:
            return online()

        # ç»éï¼å°è¯ 5 æ¬¡
        for _ in range(5):
            # å½ä»¤è¡æ¾ç¤ºç»å½äºç»´ç 
            # itchat.auto_login(enableCmdQR=True)
            if os.environ.get('MODE') == 'server':
                itchat.auto_login(enableCmdQR=2)
            else:
                itchat.auto_login()
            if online():
                print('ç»å½æå')
                return True
        else:
            print('ç»å½æå')
            return False

    def run(self):
        '''
        ä¸»è¿è¡å¥å£
        :return:None
        '''
        # èªå¨ç»å½
        if not self.is_online(auto_login=True):
            return
        for girlfriend in self.girlfriend_list:
            wechat_name = girlfriend.get('wechat_name')
            friends = itchat.search_friends(name=wechat_name)
            if not friends:
                print('æµç§°éè¯¯')
                return
            name_uuid = friends[0].get('UserName')
            girlfriend['name_uuid'] = name_uuid

        # å®æ¶ä»»å¡
        scheduler = BlockingScheduler()
        # æ¯å¤©9ï¼30å·¦å³ç»å¥³æååéæ¯æ¥ä¸å¥
        scheduler.add_job(self.start_today_info, 'cron', hour=self.alarm_hour, minute=self.alarm_minute)
        # æ¯é2åéåéä¸æ¡æ°æ®ç¨äºæµè¯ã
        # scheduler.add_job(self.start_today_info, 'interval', seconds=30)
        scheduler.start()

    def start_today_info(self, is_test=False):

        '''
        æ¯æ¥å®æ¶å¼å§å¤çã
        :param is_test: æµè¯æ å¿ï¼å½ä¸ºTrueæ¶ï¼ä¸åéå¾®ä¿¡ä¿¡æ¯ï¼ä»ä»è·åæ°æ®ã
        :return:
        '''
        print("*" * 50)
        print('è·åç¸å³ä¿¡æ¯...')

        if self.dictum_channel == 1:
            dictum_msg = self.get_dictum_info()
        elif self.dictum_channel == 2:
            dictum_msg = self.get_ciba_info()
        elif self.dictum_channel == 3:
            dictum_msg = self.get_lovelive_info()
        else:
            dictum_msg = ''

        for girlfriend in self.girlfriend_list:
            city_code = girlfriend.get('city_code')
            start_date = girlfriend.get('start_date')
            sweet_words = girlfriend.get('sweet_words')
            today_msg = self.get_weather_info(dictum_msg, city_code=city_code, start_date=start_date,
                                              sweet_words=sweet_words)
            name_uuid = girlfriend.get('name_uuid')
            wechat_name = girlfriend.get('wechat_name')
            print(f'ç»ã{wechat_name}ãåéçåå®¹æ¯:\n{today_msg}')

            if not is_test:
                if self.is_online(auto_login=True):
                    itchat.send(today_msg, toUserName=name_uuid)
                # é²æ­¢ä¿¡æ¯åéè¿å¿«ã
                time.sleep(5)

        print('åéæå..\n')

    def isJson(self, resp):
        '''
        å¤æ­æ°æ®æ¯å¦è½è¢« Json åã True è½ï¼False å¦ã
        :param resp:
        :return:
        '''
        try:
            resp.json()
            return True
        except:
            return False

    def get_ciba_info(self):
        '''
        ä»è¯é¸ä¸­è·åæ¯æ¥ä¸å¥ï¼å¸¦è±æã
        :return:
        '''
        resp = requests.get('http://open.iciba.com/dsapi')
        if resp.status_code == 200 and self.isJson(resp):
            conentJson = resp.json()
            content = conentJson.get('content')
            note = conentJson.get('note')
            # print(f"{content}\n{note}")
            return f"{content}\n{note}\n"
        else:
            print("æ²¡æè·åå°æ°æ®")
            return None

    def get_dictum_info(self):
        '''
        è·åæ ¼è¨ä¿¡æ¯ï¼ä»ãä¸ä¸ªãoneãè·åä¿¡æ¯ http://wufazhuce.com/ï¼
        :return: str ä¸å¥æ ¼è¨æèç­è¯­
        '''
        print('è·åæ ¼è¨ä¿¡æ¯..')
        user_url = 'http://wufazhuce.com/'
        resp = requests.get(user_url, headers=self.headers)
        soup_texts = BeautifulSoup(resp.text, 'lxml')
        # ãone -ä¸ªã ä¸­çæ¯æ¥ä¸å¥
        every_msg = soup_texts.find_all('div', class_='fp-one-cita')[0].find('a').text
        return every_msg + "\n"


    def get_lovelive_info(self):
        '''
        ä»åå³æè¯ä¸­è·åæ¯æ¥ä¸å¥ã
        '''
        resp = requests.get("https://api.lovelive.tools/api/SweetNothings")
        return resp.text + "\n"

   
    def get_weather_info(self, dictum_msg='', city_code='101030100', start_date='2018-01-01', sweet_words='From your Valentine'):

        '''
        è·åå¤©æ°ä¿¡æ¯ãç½åï¼https://www.sojson.com/blog/305.html
        :param dictum_msg: åéç»æåçä¿¡æ¯
        :param city_code: åå¸å¯¹åºç¼ç 
        :param start_date: æç±ç¬¬ä¸å¤©æ¥æ
        :param sweet_words: æ¥èªè°ççè¨
        :return: éè¦åéçè¯ã
        '''
        print('è·åå¤©æ°ä¿¡æ¯..')
        weather_url = f'http://t.weather.sojson.com/api/weather/city/{city_code}'
        resp = requests.get(url=weather_url)
        if resp.status_code == 200 and self.isJson(resp) and resp.json().get('status') == 200:
            weatherJson = resp.json()
            # ä»æ¥å¤©æ°
            today_weather = weatherJson.get('data').get('forecast')[1]
            # ä»æ¥æ¥æ
            today_time = datetime.now().strftime('%Y{y}%m{m}%d{d} %H:%M:%S').format(y='å¹´', m='æ', d='æ¥')
            # ä»æ¥å¤©æ°æ³¨æäºé¡¹
            notice = today_weather.get('notice')
            # æ¸©åº¦
            high = today_weather.get('high')
            high_c = high[high.find(' ') + 1:]
            low = today_weather.get('low')
            low_c = low[low.find(' ') + 1:]
            temperature = f"æ¸©åº¦ : {low_c}/{high_c}"

            # é£
            fx = today_weather.get('fx')
            fl = today_weather.get('fl')
            wind = f"{fx} : {fl}"

            # ç©ºæ°ææ°
            aqi = today_weather.get('aqi')
            aqi = f"ç©ºæ° : {aqi}"

            # å¨ä¸èµ·ï¼ä¸å±å¤å°å¤©äºï¼å¦ææ²¡æè®¾ç½®åå§æ¥æï¼åä¸ç¨å¤ç
            if start_date:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                day_delta = (datetime.now() - start_datetime).days
                delta_msg = f'å®è´è¿æ¯æä»¬å¨ä¸èµ·çç¬¬ {day_delta} å¤©ã\n'
            else:
                delta_msg = ''

            today_msg = f'{today_time}\n{delta_msg}{notice}ã\n{temperature}\n{wind}\n{aqi}\n{dictum_msg}{sweet_words if sweet_words else ""}\n'
            return today_msg


if __name__ == '__main__':

    # ç´æ¥è¿è¡
    # gfweather().run()

    # åªæ¥çè·åæ°æ®ï¼
    # gfweather().start_today_info(True)

    # æµè¯è·åè¯é¸ä¿¡æ¯
    # ciba = gfweather().get_ciba_info()
    # print(ciba)

    # æµè¯è·åæ¯æ¥ä¸å¥ä¿¡æ¯
    # dictum = gfweather().get_dictum_info()
    # print(dictum)

    # æµè¯è·åå¤©æ°ä¿¡æ¯
    # wi = gfweather().get_weather_info('ä¸½å\n')
    # print(wi)
    pass
