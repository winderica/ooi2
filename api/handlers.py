import os

from tornado.gen import coroutine
from tornado.web import RequestHandler
from tornado.escape import json_decode

from session.session import OoiSession
from utils.httpclient import AsyncHTTPClient
from utils.convert import to_str
from config import proxy_host, proxy_port, api_start2_path

Session = OoiSession()


class ApiHandler(RequestHandler):
    @coroutine
    def post(self, action):
        world_ip = to_str(self.get_secure_cookie('world_ip'))
        if world_ip:
            if action == 'api_start2' and os.path.exists(api_start2_path):
                self.set_header('Content-Type', 'text/plain')
                f = open(api_start2_path, 'rb')
                self.write(f.read())
                f.close()
            else:
                referer = self.request.headers.get('Referer')
                referer = referer.replace(self.request.headers.get('Host'), world_ip)
                referer = referer.replace('https', 'http')
                url = 'http://' + world_ip + self.request.uri
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                    'Origin': 'http://' + world_ip + '/',
                    'Referer': referer,
                    'X-Requested-With': 'ShockwaveFlash/18.0.0.232'
                }
                http_client = AsyncHTTPClient()
                response = yield http_client.fetch(url, method='POST', headers=headers, body=self.request.body,
                                                   connect_timeout=60, request_timeout=120,
                                                   proxy_host=proxy_host, proxy_port=proxy_port)
                self.set_header('Content-Type', response.headers['Content-Type'])
                self.write(response.body)
                if action == 'api_get_member/basic':
                    svdata = json_decode(response.body[7:])
                    if svdata['api_result'] == 1:
                        owner = to_str(self.get_secure_cookie('owner'))
                        token = to_str(self.get_secure_cookie('token'))
                        starttime = to_str(self.get_secure_cookie('starttime'))
                        user = Session.get_user(owner, token, starttime)
                        if user:
                            Session.update_user(owner, svdata['api_data']['api_member_id'],
                                                svdata['api_data']['api_nickname'])
        else:
            self.send_error(403)


class MainSwfHandler(RequestHandler):
    def get(self):
        token = to_str(self.get_argument('api_token'))
        starttime = to_str(self.get_argument('api_starttime'))
        owner = to_str(self.get_argument('owner'))
        if owner and token and starttime:
            user = Session.get_user(owner, token, starttime)
            if user:
                world_ip = to_str(user.get(b'world_ip'))
                self.set_secure_cookie('owner', owner, expires_days=None)
                self.set_secure_cookie('token', token, expires_days=None)
                self.set_secure_cookie('starttime', starttime, expires_days=None)
                self.set_secure_cookie('world_ip', world_ip, expires_days=None)
                self.set_header('Cache-Control', 'no-cache')
                self.set_header('Content-Type', 'application/x-shockwave-flash')
                self.set_header('X-Accel-Redirect', '/_kcs/mainD2.swf')
                return
        self.send_error(403)


class WorldImageHandler(RequestHandler):
    def get(self, size):
        world_ip = to_str(self.get_secure_cookie('world_ip'))
        if world_ip:
            ip_sections = map(int, world_ip.split('.'))
            formatted_ip = '_'.join([format(x, '03') for x in ip_sections])
            real_path = '/_kcs/%s_%s.png' % (formatted_ip, size)
            self.set_header('Cache-Control', 'no-cache')
            self.set_header('Content-Type', 'image/png')
            self.set_header('X-Accel-Redirect', real_path)
        else:
            self.send_error(403)
