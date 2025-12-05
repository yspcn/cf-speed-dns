import requests
import traceback
import time
import os
import json

CF_API_TOKEN = os.environ["CF_API_TOKEN"]
CF_ZONE_ID = os.environ["CF_ZONE_ID"]
CF_DNS_NAME = os.environ["CF_DNS_NAME"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]

try:
    CF_DNS_NAME = json.loads(CF_DNS_NAME)
except:
    CF_DNS_NAME = [CF_DNS_NAME]

headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}

# 获取优选 IP
def get_cf_speed_test_ip(timeout=10):
    try:
        response = requests.get('https://ip.164746.xyz/ipTop.html', timeout=timeout)
        if response.status_code == 200:
            return response.text.split(',')
    except:
        traceback.print_exc()
    return None

# 获取 DNS 记录
def get_dns_records(name):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records?name={name}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["result"]
    return []

# 更新 DNS 记录
def update_dns_record(record, ip):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record["id"]}'
    data = {
        "type": record["type"],
        "name": record["name"],
        "content": ip,
        "proxied": record.get("proxied", False)
    }
    response = requests.put(url, headers=headers, json=data)
    return response.status_code == 200

# 推送
def push_plus(content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "IP优选DNS更新通知",
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }
    requests.post(url, json=data)

def main():
    ip_list = get_cf_speed_test_ip()
    if not ip_list:
        push_plus("⚠️ 无法获取优选 IP，已停止执行")
        return

    ip_index = 0
    result_table = "| 域名 | 原IP | 新IP | 状态 |\n|-----|-----|-----|-----|"

    for domain in CF_DNS_NAME:
        records = get_dns_records(domain)
        if not records:
            result_table += f"\n| {domain} | — | — | ❌ 未找到记录 |"
            continue

        for record in records:
            if ip_index >= len(ip_list):
                result_table += f"\n| {domain} | — | — | ⚠️ IP数量不足未继续更新 |"
                break

            old_ip = record["content"]
            new_ip = ip_list[ip_index]

            # 不变则跳过更新
            if old_ip == new_ip:
                result_table += f"\n| {domain} | {old_ip} | {new_ip} | ⏳ 无需更新 |"
            else:
                ok = update_dns_record(record, new_ip)
                if ok:
                    result_table += f"\n| {domain} | {old_ip} | {new_ip} | ✅ 更新成功 |"
                else:
                    result_table += f"\n| {domain} | {old_ip} | {new_ip} | ❌ 更新失败 |"

            ip_index += 1
            time.sleep(0.8)  # 防 API 封锁

    push_plus(result_table)

if __name__ == '__main__':
    main()
