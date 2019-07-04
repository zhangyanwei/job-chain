import requests

from ..exception import EventHandlerError


def run(access_token: str, selector: str, messages: dict):
    body = messages.get(selector, messages.get('*', {}))
    if body:
        r = requests.post(f'https://oapi.dingtalk.com/robot/send?access_token={access_token}', json=body)
        r.json().get('errcode')
        if r.status_code == 200:
            if r.json().get('errcode') != 0:
                raise EventHandlerError('dingding', r.json().get('errmsg'))
        else:
            raise EventHandlerError('dingding', str(r))
    return bool(body)
