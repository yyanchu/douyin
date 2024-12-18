# -*- encoding: utf-8 -*-
'''
@File    :   main.py
@Time    :   2024年12月17日 20:56:14 星期二
@Desc    :   抖音爬虫
'''

# -*- encoding: utf-8 -*-

import os
import re
from threading import Lock
from typing import List
from urllib.parse import parse_qs, quote, unquote, urlparse

import ujson as json
from loguru import logger

from utils.request import Request
from utils.util import quit, save_json, str_to_path, url_redirect


class Douyin(object):

    def __init__(self, target: str = '', limit: int = 0, type: str = 'post', down_path: str = '下载', cookie: str = ''):
        """
        初始化信息
        """
        self.target = target
        self.limit = limit
        self.type = type

        self.down_path = os.path.join('.', down_path)
        if not os.path.exists(self.down_path):
            os.makedirs(self.down_path)

        self.has_more = True
        self.results_old = []
        self.results = []
        self.lock = Lock()

        req = Request(cookie)
        self.http = req.http
        self.request = req.request

    def run(self):

        self.__get_target_info()

        if self.type in ['user', 'follow', 'fans']:
            self.get_awemes_list()
        # elif self.type in ['live']:
        #     pass
        elif self.type in ['post', 'like', 'favorite', 'search', 'music', 'hashtag', 'collection']:
            self.get_awemes_list()
        elif self.type in ['video', 'note']:
            self.get_aweme()
        else:  # 其他情况
            quit(f'获取目标类型错误, type: {self.type}')

    def __get_target_id(self):
        if self.target:  # 根据输入目标自动判断部分类型
            target = self.target.strip()
            hostname = urlparse(target).hostname
            # 输入链接
            if hostname and hostname.endswith('douyin.com'):
                if hostname == 'v.douyin.com':
                    target = url_redirect(target)
                *_, _type, id = unquote(urlparse(target).path.strip('/')).split('/')
                self.url = target
                # 自动识别 单个作品 搜索、音乐、合集
                if _type in ['video', 'note', 'music', 'hashtag', 'collection']:
                    self.type = _type
                    if self.type in ['video', 'note']:
                        self.url = f'https://www.douyin.com/note/{id}'
                elif _type == 'search':
                    id = unquote(id)
                    search_type = parse_qs(urlparse(target).query).get('type')
                    if search_type is None or search_type[0] in ['video', 'general']:
                        self.type = 'search'
                    else:
                        self.type = search_type[0]
            # 输入非链接
            else:
                id = target
                if self.type in ['search', 'user', 'live']:  # 搜索 视频 用户 直播间
                    url = f'https://www.douyin.com/search/{quote(id)}'
                    if self.type == 'search':
                        self.url = f'{url}?type=video'
                    else:
                        self.url = f'{url}?type={self.type}'
                # 数字ID: 单个作品id 音乐id 合集id
                elif self.type in ['video', 'note', 'music', 'hashtag', 'collection'] and id.isdigit():
                    if self.type in ['video', 'note']:
                        self.url = f'https://www.douyin.com/note/{id}'
                    self.url = f'https://www.douyin.com/{self.type}/{id}'
                # 用户uid
                elif self.type in ['post', 'like', 'favorite', 'follow', 'fans'] and id.startswith('MS4wLjABAAAA'):
                    self.url = f'https://www.douyin.com/user/{id}'
                else:  # 其他情况
                    quit(f'[{id}]目标输入错误，请检查参数')
        else:  # 未输入目标，直接采集本账号数据
            id = self.__get_self_uid()
            self.url = 'https://www.douyin.com/user/self'
        self.id = id

    def __get_target_info(self):
        self.__get_target_id()
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'cookie': 'UIFID_TEMP=973a3fd64dcc46a3490fd9b60d4a8e663b34df4ccc4bbcf97643172fb712d8b03b42275a5a6cb168b8e6d17134cd64d2a83801c87cc74bd4befe0506d8c634c4017a43e2ee5d781f62ac0d5086c521d5; fpk1=U2FsdGVkX183/wARk4f3SUMj03G6CodXIj1zcMPsS/3ythFPPCHWyaAGRnR3MKDBIFtXfFUayrKGbITFb2e5zQ==; fpk2=362d7fe3d8b2581bffa359f0eeda7106; bd_ticket_guard_client_web_domain=2; UIFID=973a3fd64dcc46a3490fd9b60d4a8e663b34df4ccc4bbcf97643172fb712d8b08e16b75177a850c9e11487bc98127157390c8bd30dd913b5cb930457cd36999bfe578ed67f01b90381a36cbe7506a081f47057b7b0e073672474c7d2b728959c2d2fe50d9e368cc8c26506149097f44fc252719e4450e2d18b566da9c9e6c36a28353dc20f66561b7555dac9acfb270887095292c1ca535ec44372e70cf5e392; SEARCH_RESULT_LIST_TYPE=%22single%22; xgplayer_user_id=951619778125; live_use_vvc=%22false%22; _bd_ticket_crypt_doamin=2; __security_server_data_status=1; store-region=cn-xj; store-region-src=uid; hevc_supported=true; passport_mfa_token=CjdGGCdj8US%2Bn1fd0dO91pOXXFSJJSGivpus49ZVugxkIdZrL%2BkpuN4qOQWES8CVS4Omji%2BkCIkwGkoKPMvl1tLMHMFoRprc8xArnXorMol0ni0GPIxSmZ0gMUBSgb72V1NyP8glQa3%2B6YAoBEOgFx%2B5OjQN8C84%2FhDL8eENGPax0WwgAiIBA9ey2NE%3D; d_ticket=6ed7538e32df68bcb632791896c6577a7706d; n_mh=t_N21gqZcMnZzBdfMM9XczFD6UCar4zCBRTzrHTcw2Y; is_staff_user=false; SelfTabRedDotControl=%5B%5D; passport_assist_user=CkGizeV98Oh6hzKXvnjD81Aq4k6aPw80rvr4M5DpbhWfYVvFrFARb95RgBcmuwS8pKZjDCLwziR1nKDT_-aOO2_-QxpKCjw867n4gi-nJG9oK-lXhQHkpQUyj9IooW5sx66b5Ry28H-vgm2MnYwAzT9frXUKznGd6y_Z0p4-QV2j8p4Qt_jhDRiJr9ZUIAEiAQOEdxAa; sso_uid_tt=684a2698eab767025c35b262683c18a3; sso_uid_tt_ss=684a2698eab767025c35b262683c18a3; toutiao_sso_user=b1c083b9f8b76e7f5f1ea4cbf0320158; toutiao_sso_user_ss=b1c083b9f8b76e7f5f1ea4cbf0320158; sid_ucp_sso_v1=1.0.0-KDhmYzQ5YmJjM2E4Mzk1NWJiMjAyODM3ZjFhZWM0ZTlhMmM0OGZmMGUKIQiT4NC72My1AhChnvW5BhjvMSAMMOPv4bIGOAZA9AdIBhoCbGYiIGIxYzA4M2I5ZjhiNzZlN2Y1ZjFlYTRjYmYwMzIwMTU4; ssid_ucp_sso_v1=1.0.0-KDhmYzQ5YmJjM2E4Mzk1NWJiMjAyODM3ZjFhZWM0ZTlhMmM0OGZmMGUKIQiT4NC72My1AhChnvW5BhjvMSAMMOPv4bIGOAZA9AdIBhoCbGYiIGIxYzA4M2I5ZjhiNzZlN2Y1ZjFlYTRjYmYwMzIwMTU4; login_time=1732071198629; passport_auth_status=492224e3abd3f53158d4547d7c16e19f%2Cf68677e06a5f6bb4e57cb02eabbe5adb; passport_auth_status_ss=492224e3abd3f53158d4547d7c16e19f%2Cf68677e06a5f6bb4e57cb02eabbe5adb; uid_tt=7443427f76f098d459b2b236be44b9b1; uid_tt_ss=7443427f76f098d459b2b236be44b9b1; sid_tt=c7581180ab4a9f00a79b3067871e3cf5; sessionid=c7581180ab4a9f00a79b3067871e3cf5; sessionid_ss=c7581180ab4a9f00a79b3067871e3cf5; _bd_ticket_crypt_cookie=cbd4587090740e83e3c93dcf8d2ea8dc; dy_swidth=1920; dy_sheight=1080; is_dash_user=1; s_v_web_id=verify_m4h13uvf_4h5J2qAV_OnhH_4flt_BY8o_rOtuHwC56VZR; passport_csrf_token=5811dbdfba95dfda808d876f9da6a6bf; passport_csrf_token_default=5811dbdfba95dfda808d876f9da6a6bf; publish_badge_show_info=%220%2C0%2C0%2C1734421624368%22; sid_guard=c7581180ab4a9f00a79b3067871e3cf5%7C1734421627%7C5184000%7CSat%2C+15-Feb-2025+07%3A47%3A07+GMT; sid_ucp_v1=1.0.0-KDViZGQzOTg1NWU2OTI0NGY0ZThkOTU3MzZlY2ExYWVhYWZlZDE3ZWYKGwiT4NC72My1AhD72IS7BhjvMSAMOAZA9AdIBBoCaGwiIGM3NTgxMTgwYWI0YTlmMDBhNzliMzA2Nzg3MWUzY2Y1; ssid_ucp_v1=1.0.0-KDViZGQzOTg1NWU2OTI0NGY0ZThkOTU3MzZlY2ExYWVhYWZlZDE3ZWYKGwiT4NC72My1AhD72IS7BhjvMSAMOAZA9AdIBBoCaGwiIGM3NTgxMTgwYWI0YTlmMDBhNzliMzA2Nzg3MWUzY2Y1; xgplayer_device_id=4377705565; __live_version__=%221.1.2.6318%22; live_can_add_dy_2_desktop=%221%22; EnhanceDownloadGuide=%220_0_1_1734421659_0_0%22; ttwid=1%7CGpSAyGYdCgz_iYgsr3qhRYSlEqvsDLshBhkjZgTsLQs%7C1734422071%7Ca5698d9beb4fb8395cb1d6e1441b2743228d8a3df24831d01f6584723450cf61; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; download_guide=%223%2F20241217%2F0%22; __ac_nonce=067625925002e7510857c; __ac_signature=_02B4Z6wo00f01ySqQAwAAIDDE46EUydht1MkikSAAK5T73; douyin.com; device_web_cpu_core=16; device_web_memory_size=8; architecture=amd64; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A100%7D%22; csrf_session_id=57a0be7861226a1889217c02ca758dc9; strategyABtestKey=%221734498595.094%22; biz_trace_id=a2852bf4; xg_device_score=7.762105674549726; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A1%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; passport_fe_beating_status=true; odin_tt=4be1a35a00448bc77908bbf19e5d26e45eaa80a83be8a4d45cde37187a5a5423ea9be4d9621ef23ed1e22cfed5de8e5c; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCT3A2eWpSV0VWVjNmMnBmYnUxaWdCaVQxQkhrWFdnaXNsaXlEVzk5TTFyemkrRWJLV2tzQWV6WGMvSnEyR3NZWjN0MTZJYVhwNkhZeGlzMW5YUy9nRXM9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; IsDouyinActive=false',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        response = self.http.get(self.url, headers=headers)
        print(self.url)
        if response.status_code != 200 or response.text == '':
            quit(f'获取目标信息请求失败, url: {self.url}')
        # 目标信息
        if self.type in ['search', 'user', 'live']:
            pattern = r'<script id="RENDER_DATA" type="application/json">([\s\S]*?)</script>'
            match = re.search(pattern, response.text)
            if match:
                render_data = unquote(match.group(1))
            else:
                quit(f'获取目标信息失败, type: {self.type}')
        else:
            # self\.__pace_f\.push\(\[1,"\d:([\s\S]*?)(\\n")?\]\)</script>
            pattern = r'self\.__pace_f\.push\(\[1,"\d:\[\S+?({[\s\S]*?)\]\\n"\]\)</script>'
            render_data: str = re.findall(pattern, response.text)[-1]
        if render_data:
            render_data = render_data.replace('\\"', '"').replace('\\\\', '\\')
            self.render_data = json.loads(render_data)
            if self.render_data:
                if self.type in ['search', 'user', 'live']:
                    self.info = self.render_data['app']['defaultSearchParams']
                    self.title = self.id
                elif self.type == 'collection':
                    self.info = self.render_data['aweme']['detail']['mixInfo']
                    self.title = self.info['mixName']
                elif self.type == 'music':
                    self.info = self.render_data['musicDetail']
                    self.title = self.info['title']
                elif self.type == 'hashtag':
                    self.info = self.render_data['topicDetail']
                    self.title = self.info['chaName']
                elif self.type in ['video', 'note']:
                    self.info = self.render_data['aweme']['detail']
                    self.title = self.id
                elif self.type in ['post', 'like', 'favorite', 'follow', 'fans']:
                    self.info = self.render_data['user']['user']
                    self.title = self.info['nickname']
                else:  # 其他情况
                    quit(f'获取目标信息请求失败, type: {self.type}')

                self.down_path = os.path.join(
                    self.down_path, str_to_path(f'{self.type}_{self.title}'))
                self.aria2_conf = f'{self.down_path}.txt'
                # 增量采集，先取回旧数据
                # if self.type in ['post', 'like', 'favorite']:
                if self.type == 'post':
                    if os.path.exists(f'{self.down_path}.json') and not self.results_old:
                        with open(f'{self.down_path}.json', 'r', encoding='utf-8') as f:
                            self.results_old = json.load(f)
        else:
            quit(f'提取目标信息失败, url: {self.url}')

    def __get_self_uid(self):
        url = 'https://www.douyin.com/user/self'
        response = self.http.get(url)
        if response.status_code != 200 or response.text == '':
            quit(f'获取UID请求失败, url: {url}')
        pattern = r'secUid\\":\\"([-\w]+)\\"'
        match = re.search(pattern, response.text)
        if match:
            return match.group(1)
        else:
            quit(f'获取UID请求失败, url: {url}')

    def get_aweme(self):
        if self.render_data.get('aweme', None):
            render_data_ls = [self.render_data['aweme']['detail']]
            self.__append_awemes(render_data_ls)
            self.save()
        else:
            quit('作品详情获取失败，未获取到页面数据')

    def get_aweme_detail(self) -> tuple[dict, bool]:
        params = {"aweme_id": self.id}
        uri = '/aweme/v1/web/aweme/detail/'
        resp, succ = self.request(uri, params)
        aweme_detail = resp.get('aweme_detail', {})
        if aweme_detail:
            self.__append_awemes([aweme_detail])
            self.save()
        else:
            quit('作品详情获取失败')

    def get_user(self):
        params = {"publish_video_strategy_type": 2,
                  "sec_user_id": self.id, "personal_center_strategy": 1}
        resp, succ = self.request('/aweme/v1/web/user/profile/other/', params)
        # print(succ, resp)
        if succ:
            self.info = resp.get('user', {})
            # 下载路径
            self.down_path = os.path.join(self.down_path, str_to_path(
                f"{self.info['nickname']}_{self.id}"))
            self.aria2_conf = f'{self.down_path}.txt'
            if os.path.exists(f'{self.down_path}.json') and not self.results_old:
                with open(f'{self.down_path}.json', 'r', encoding='utf-8') as f:
                    self.results_old = json.load(f)
        else:
            quit('cookie可能失效，目标信息解析失败，退出程序。')

    def get_user_v2(self):
        url = f'https://www.douyin.com/web/api/v2/user/info/?sec_uid={self.id}'
        try:
            res = self.http.get(url).json()
            self.info = res['user_info']
            # 下载路径
            self.down_path = os.path.join(self.down_path, str_to_path(
                f"{self.info['nickname']}_{self.id}"))
            self.aria2_conf = f'{self.down_path}.txt'
            if os.path.exists(f'{self.down_path}.json') and not self.results_old:
                with open(f'{self.down_path}.json', 'r', encoding='utf-8') as f:
                    self.results_old = json.load(f)
        except:
            quit('cookie可能失效，目标信息解析失败，退出程序。')

    def get_awemes_list(self):
        max_cursor = 0
        logid = ''
        retry = 0
        max_retry = 10
        data = {}
        while self.has_more:
            try:
                # ['post', 'like', 'favorite', 'search', 'music','hashtag', 'collection']
                if self.type == 'post':
                    uri = '/aweme/v1/web/aweme/post/'
                    params = {"publish_video_strategy_type": 2, "max_cursor": max_cursor, "locate_query": False,
                              'show_live_replay_strategy': 1, 'need_time_list': 0, 'time_list_query': 0, 'whale_cut_token': '', 'count': 18, "sec_user_id": self.id
                              }
                elif self.type == 'like':
                    uri = '/aweme/v1/web/aweme/favorite/'
                    params = {"publish_video_strategy_type": 2, "max_cursor": max_cursor,
                              'cut_version': 1, 'count': 18, "sec_user_id": self.id}
                elif self.type == 'favorite':
                    uri = '/aweme/v1/web/aweme/listcollection/'
                    params = {"publish_video_strategy_type": 2}
                    data = {"cursor": max_cursor, 'count': 18}
                elif self.type == 'music':
                    uri = '/aweme/v1/web/music/aweme/'
                    params = {"cursor": max_cursor,
                              'count': 18, "music_id": self.id}
                elif self.type == 'hashtag':
                    uri = '/aweme/v1/web/challenge/aweme/'
                    params = {"cursor": max_cursor, "sort_type": 1,  # 0综合 1最热 2最新
                              'count': 18, "ch_id": self.id}
                elif self.type == 'collection':
                    uri = '/aweme/v1/web/mix/aweme/'
                    params = {"cursor": max_cursor,
                              'count': 18, "mix_id": self.id}
                elif self.type == 'search':
                    uri = '/aweme/v1/web/search/item/'  # 视频
                    # uri = '/aweme/v1/web/search/single/'  # 综合
                    # uri = '/aweme/v1/web/live/search/'  # 直播
                    params = {
                        "search_id": logid,
                        "search_channel": "aweme_video_web",
                        "search_source": "tab_search",
                        "query_correct_type": 1,
                        "from_group_id": "",
                        "is_filter_search": 1,
                        "list_type": "single",
                        "need_filter_settings": 1,
                        "offset": max_cursor,
                        "sort_type": 1,  # 排序 综合 1最多点赞 2最新
                        "enable_history": 1,
                        "search_range": 0,  # 搜索范围  不限
                        "publish_time": 0,  # 发布时间  不限
                        "filter_duration": '',  # 时长 不限 0-1  1-5  5-10000
                        'count': 18,
                        "keyword": unquote(self.id)
                    }
                elif self.type == 'user':
                    uri = '/aweme/v1/web/discover/search/'  # 用户
                    params = {
                        'count': 10,
                        "from_group_id": "",
                        "is_filter_search": 0,
                        "keyword": unquote(self.id),
                        "list_type": "single",
                        "need_filter_settings": 0,
                        "offset": max_cursor,
                        "search_id": logid,
                        "query_correct_type": 1,
                        # "new_user_login": 0,
                        "search_channel": "aweme_user_web",
                        "search_source": "normal_search"
                    }
                elif self.type == 'live':
                    uri = '/aweme/v1/web/discover/search/'
                    params = {}
                elif self.type == 'follow':
                    uri = '/aweme/v1/web/user/following/list/'
                    params = {
                        "address_book_access": 0,
                        "count": 20,
                        "gps_access": 0,
                        "is_top": 1,
                        "max_time": max_cursor,
                        "min_time": 0,
                        "offset": 0,
                        'source_type': 1,
                        "sec_user_id": self.id
                    }
                elif self.type == 'fans':
                    uri = '/aweme/v1/web/user/follower/list/'
                    params = {
                        "address_book_access": 0,
                        "count": 20,
                        "gps_access": 0,
                        "is_top": 1,
                        "max_time": max_cursor,
                        "min_time": 0,
                        "offset": 0,
                        'source_type': 3,
                        "sec_user_id": self.id
                    }

                resp, succ = self.request(uri, params, data)
                for name in ['max_cursor', 'cursor', 'min_time']:
                    max_cursor = resp.get(name, 0)
                    if max_cursor:
                        break
                logid = resp['log_pb']['impr_id']
                self.has_more = resp.get('has_more', 0)
                for name in ['aweme_list', 'user_list', 'data', 'followings', 'followers']:
                    aweme_list = resp.get(name, [])
                    if aweme_list:
                        break
            except:
                retry += 1
                logger.error(f'采集请求出错... 进行第{retry}次重试')
                continue
            finally:
                # 重试max_retry次
                if retry >= max_retry:
                    self.has_more = False

            if aweme_list:
                retry = 0
                if self.type in ['post', 'like', 'favorite', 'search', 'music', 'hashtag', 'collection']:
                    self.__append_awemes(aweme_list)
                elif self.type in ['user', 'live', 'follow', 'fans']:
                    self.__append_users(aweme_list)
                else:
                    quit(f'类型错误，type：{self.type}')
            elif self.has_more:
                retry += 1
                logger.error(f'采集未完成，但请求结果为空... 进行第{retry}次重试')
            else:
                # logger.info('未采集到结果')
                pass
        self.save()

    def __append_awemes(self, aweme_list: List[dict]):
        with self.lock:  # 加锁避免意外冲突
            if self.limit == 0 or len(self.results) < self.limit:
                for item in aweme_list:
                    # =====兼容搜索=====
                    if item.get('aweme_info'):
                        item = item['aweme_info']
                    # =====限制数量=====
                    if self.limit > 0 and len(self.results) >= self.limit:
                        self.has_more = False
                        logger.info(f'已达到限制采集数量：{len(self.results)}')
                        return
                    # =====增量采集=====
                    _time = item.get('create_time', item.get('createTime'))
                    if self.results_old:
                        old = self.results_old[0]['time']
                        if _time <= old:  # 如果当前作品时间早于上次采集的最新作品时间，直接退出
                            _is_top = item.get(
                                'is_top', item.get('tag', {}).get('isTop'))
                            if _is_top:  # 置顶作品，不重复保存
                                continue
                            if self.has_more:
                                self.has_more = False
                            logger.success(f'增量采集完成，上次运行结果：{old}')
                            return
                    # =====保存结果=====
                    # _type = item.get('media_type', item.get('media_type'))  # 2 图集 4 视频
                    _type = item.get('aweme_type', item.get('awemeType'))
                    aweme: dict = item.get('statistics', item.get('stats', {}))
                    for i in [
                            'playCount', 'downloadCount', 'forwardCount', 'collectCount', "digest", "exposure_count",
                            "live_watch_count", "play_count", "download_count", "forward_count", "lose_count",
                            "lose_comment_count"
                    ]:
                        if not aweme.get(i):
                            aweme.pop(i, '')
                    for i in ['duration']:
                        if item.get(i):
                            aweme[i] = item[i]
                    if _type <= 66 or _type in [69, 107]:  # 视频 77西瓜视频
                        play_addr = item['video'].get(
                            'play_addr', item.get('awemeType'))
                        if play_addr:
                            download_addr = item['video']['play_addr']['url_list'][-1]
                        else:
                            # download_addr = f"https:{item['video']['playApi']}"
                            download_addr: str = item['download']['urlList'][-1]
                            download_addr = download_addr.replace(
                                'watermark=1', 'watermark=0')
                        aweme['download_addr'] = download_addr
                    elif _type == 68:  # 图文
                        aweme['download_addr'] = [images.get('url_list', images.get(
                            'urlList'))[-1] for images in item['images']]
                    elif _type == 101:  # 直播
                        continue
                    else:  # 其他类型作品
                        aweme['download_addr'] = '其他类型作品'
                        logger.info('其他类型作品：type', _type)
                        save_json(_type, item)  # 保存未区分的类型
                        continue
                    aweme.pop('aweme_id', '')
                    aweme['id'] = item.get('aweme_id', item.get('awemeId'))
                    aweme['time'] = _time
                    desc = str_to_path(item.get('desc'))
                    aweme['desc'] = desc
                    music: dict = item.get('music')
                    if music:
                        aweme['music_title'] = str_to_path(music['title'])
                        aweme['music_url'] = music.get(
                            'play_url', music.get('playUrl'))['uri']
                    cover = item['video'].get('origin_cover')
                    if cover:
                        aweme['cover'] = cover['url_list'][-1]
                    else:
                        aweme['cover'] = f"https:{item['video']['originCover']}"
                    text_extra = item.get('text_extra', item.get('textExtra'))
                    if text_extra:
                        aweme['text_extra'] = [{
                            'tag_id': hashtag.get('hashtag_id', hashtag.get('hashtagId')),
                            'tag_name': hashtag.get('hashtag_name', hashtag.get('hashtagName'))
                        } for hashtag in text_extra]
                    # video_tag = item.get('video_tag', item.get('videoTag'))
                    # if video_tag:
                    #     aweme['video_tag'] = video_tag

                    if self.type == 'collection':
                        aweme['no'] = item['mix_info']['statis']['current_episode']
                    self.results.append(aweme)  # 用于保存信息

                logger.info(f'采集中，已采集到{len(self.results)}条结果')
            else:
                self.has_more = False
                logger.info(f'已达到限制采集数量：{len(self.results)}')

    def __append_users(self, user_list: List[dict]):
        with self.lock:  # 加锁避免意外冲突
            if self.limit == 0 or len(self.results) < self.limit:
                for item in user_list:
                    # # =====兼容搜索=====
                    # if item.get('user_info'):
                    #     item = item['user_info']
                    # =====限制数量=====
                    if self.limit > 0 and len(self.results) >= self.limit:
                        self.has_more = False
                        logger.info(f'已达到限制采集数量：{len(self.results)}')
                        return
                    user_info = {}
                    user_info['nickname'] = str_to_path(item['user_info']['nickname'])
                    user_info['signature'] = str_to_path(item['user_info']['signature'])
                    user_info['avatar'] = item['user_info']['avatar_thumb']['url_list'][0]
                    user_info['sec_uid'] = str_to_path(item['user_info']['sec_uid'])
                    for i in [
                            'sec_uid', 'uid', 'short_id', 'unique_id', 'unique_id_modify_time', 'aweme_count', 'favoriting_count',
                            'follower_count', 'following_count', 'constellation', 'create_time', 'enterprise_verify_reason',
                            'is_gov_media_vip', 'live_status', 'total_favorited', 'share_qrcode_uri'
                    ]:
                        if item.get(i):
                            user_info[i] = item[i]
                    room_id = item.get('room_id')
                    if room_id:  # 直播间信息
                        user_info['live_room_id'] = room_id
                        user_info['live_room_url'] = [
                            f'http://pull-flv-f26.douyincdn.com/media/stream-{room_id}.flv',
                            f'http://pull-hls-f26.douyincdn.com/media/stream-{room_id}.m3u8'
                        ]
                    musician: dict = item.get('original_musician')
                    if musician and musician.get('music_count'):  # 原创音乐人
                        user_info['original_musician'] = item['original_musician']
                    self.results.append(user_info)  # 用于保存信息
                logger.info(f'采集中，已采集到{len(self.results)}条结果')
            else:
                self.has_more = False
                logger.info(f'已达到限制采集数量：{len(self.results)}')

    def save(self):
        if self.results:
            logger.success(f'采集完成，本次共采集到{len(self.results)}条结果')
            # 保存下载配置文件
            _ = []
            with open(self.aria2_conf, 'w', encoding='utf-8') as f:
                # 保存主页链接
                if self.type in ['user', 'follow', 'fans', 'live']:
                    f.writelines([
                        f"https://www.douyin.com/user/{line.get('sec_uid', 'None')}" for line in self.results
                        if line.get('sec_uid', None)
                    ])
                # 保存作品下载配置
                else:
                    for line in self.results:  # 只下载本次采集结果
                        filename = f'{line["id"]}_{line["desc"]}'
                        if self.type == 'collection':
                            filename = f'第{line["n"]}集_{filename}'
                        if type(line["download_addr"]) is list:
                            if self.type == 'video':
                                down_path = self.down_path.replace(
                                    line["id"], filename)
                            else:
                                down_path = os.path.join(
                                    self.down_path, filename)
                            for index, addr in enumerate(line["download_addr"]):
                                _.append(f'{addr}\n\tdir={down_path}\n\tout={line["id"]}_{index + 1}.jpeg\n')

                        elif type(line["download_addr"]) is str:
                            # 提供UA和msToken，防止下载0kb
                            _.append(
                                f'{line["download_addr"]}\n\tdir={self.down_path}\n\tout={filename}.mp4\n\tuser-agent={self.http.headers.get("User-Agent")}\n\theader="Cookie:msToken={self.http.cookies.get("msToken")}"\n'
                            )
                            # 正常下载的
                            # _.append(f'{line["download_addr"]}\n\tdir={self.down_path}\n\tout={filename}.mp4\n')
                        else:
                            logger.error("下载地址错误")
                f.writelines(_)

            if self.type == 'post':
                # 保存所有数据到文件，包括旧数据
                self.results.sort(key=lambda item: item['id'], reverse=True)
                self.results.extend(self.results_old)
            save_json(self.down_path, self.results)

        else:
            logger.info("本次采集结果为空")
