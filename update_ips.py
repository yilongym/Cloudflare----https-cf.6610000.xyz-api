import os
import re
import json
import requests

# 配置项 - 直接请求该众测面板背后的真实数据源 API 或静态 JSON
# 提示：根据其项目文档，它的核心数据通常存放在对应的 speed.txt 或接口中
TARGET_API = "https://cf.6610000.xyz/speed.txt" 
OUTPUT_FILE = "cloudflare_proxies.txt"

def get_ip_location(ip):
    """兜底解析：当归属地未知时调用线上接口"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                return f"{city} · {data.get('as', '').split()[0]}"
    except:
        pass
    return "归属未知"

def fetch_and_parse():
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        # 1. 尝试直接获取其 speed.txt 原始测速文本数据
        print(f"正在请求数据源: {TARGET_API}")
        res = requests.get(TARGET_API, headers=headers, timeout=10)
        
        # 如果直接访问文本成功
        if res.status_code == 200 and ("6610000.xyz" in res.text or "#" in res.text):
            lines = res.text.splitlines()
            for line in lines:
                if line.strip():
                    results.append(line.strip())
            return results

        # 2. 如果对方关闭了直连，从主页面的动态变量或 API 提取
        print("未直接获取到文本，尝试解析主页潜在接口...")
        page_res = requests.get("https://cf.6610000.xyz/", headers=headers, timeout=10)
        page_res.encoding = 'utf-8'
        html_content = page_res.text
        
        # 使用正则表达式在页面中搜索所有形如 *.6610000.xyz 的域名及其后面的 IP
        # 这种方式不依赖特定的 HTML 标签结构
        domains = re.findall(r'([a-z0-9]+\.[a-z0-9]+\.6610000\.xyz)', html_content)
        ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', html_content)
        
        # 临时处理：如果通过正则匹配到了域名，进行组合
        if domains:
            for d in set(domains):
                # 提取前缀作为省份提示
                prefix = d.split('.')[0] # e.g. cq, fj
                prov_map = {"cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", "sc": "四川", "yn": "云南", "zj": "浙江"}
                prov = prov_map.get(prefix, "未知地区")
                
                # 默认运营商
                isp = "中国电信" if ".ct." in d else ("中国移动" if ".cm." in d else "中国联通")
                results.append(f"{d}:443#东京 · NRT-【{prov} · {isp}-优选】")

    except Exception as e:
        print(f"解析失败: {e}")
        
    return results

if __name__ == "__main__":
    ip_list = fetch_and_parse()
    if ip_list:
        ip_list = sorted(list(set(ip_list)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(ip_list))
        print(f"🎉 成功抓取到 {len(ip_list)} 条数据，已写入 {OUTPUT_FILE}")
    else:
        print("❌ 未抓取到任何有效数据。请检查仓库或在浏览器按 F12 抓包真实接口。")
