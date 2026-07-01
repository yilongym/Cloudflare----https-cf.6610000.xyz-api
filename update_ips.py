import os
import re
import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = "cloudflare_proxies.txt"

# 省份转换字典
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def get_ip_location(domain):
    """通过解析接口获取域名的落地真实数据中心和归属地"""
    try:
        # 1. 优先获取域名的真实 IP
        import socket
        ip = socket.gethostbyname(domain)
        
        # 2. 调用公开接口查询
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "未知城市")
                org = data.get("org", "")
                # 提取 Cloudflare 机房三字码（如 NRT, HKG）或运营商
                match_colo = re.search(r'([A-Z]{3})', org)
                colo = match_colo.group(1) if match_colo else "Anycast"
                
                # 特殊机房常见映射缩写
                if "Tokyo" in city or "NRT" in org:
                    return "东京 · NRT"
                elif "Hong Kong" in city or "HKG" in org:
                    return "香港 · HKG"
                elif "Singapore" in city or "SIN" in org:
                    return "新加坡 · SIN"
                elif "San Jose" in city or "SJC" in org:
                    return "圣何塞 · SJC"
                elif "Los Angeles" in city or "LAX" in org:
                    return "洛杉矶 · LAX"
                
                return f"{city} · {colo}"
    except Exception as e:
        print(f"域名 {domain} 解析失败: {e}")
    return "归属未知"

def extract_all_22_domains():
    domains = set()
    base_url = "https://cf.6610000.xyz/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("第一步：正在读取主页源码...")
        res = requests.get(base_url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        html_text = res.text
        
        # 提取主页中直接包含的域名
        for d in re.findall(r'([a-zA-Z0-9\.-]+\.6610000\.xyz)', html_text):
            domains.add(d.lower())
            
        # 第二步：提取主页里引用的所有 JS 配置文件
        soup = BeautifulSoup(html_text, 'html.parser')
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            src = script.get('src')
            if src:
                # 补全相对路径
                js_url = src if src.startswith('http') else base_url + src.lstrip('/')
                print(f"发现前端 JS 配置文件，正在深度扫描: {js_url}")
                try:
                    js_res = requests.get(js_url, headers=headers, timeout=5)
                    for d in re.findall(r'([a-zA-Z0-9\.-]+\.6610000\.xyz)', js_res.text):
                        domains.add(d.lower())
                except:
                    continue

    except Exception as e:
        print(f"抓取异常: {e}")

    results = []
    print(f"\n清洗去重完毕，共发现 {len(domains)} 个目标节点。开始智能匹配格式...")
    
    for d in domains:
        # 过滤主域名
        if d in ["6610000.xyz", "cf.6610000.xyz"]:
            continue
            
        # 拆解前缀（如 cq.ct.6610000.xyz -> cq, ct）
        parts = d.split('.')
        prefix = parts[0] if len(parts) > 0 else ""
        isp_code = parts[1] if len(parts) > 1 else ""
        
        province = PROV_MAP.get(prefix, "优选")
        # 针对无法直接识别的双拼（如 sc、yn等新节点），将其首字母大写作为备份名
        if province == "优选" and prefix:
            province = prefix.upper()
            
        if "ct" in isp_code:
            isp = "中国电信"
        elif "cm" in isp_code:
            isp = "中国移动"
        elif "cu" in isp_code:
            isp = "中国联通"
        else:
            isp = "中国电信" # 默认兜底
            
        # 线上精确解析该节点的落地机房
        node_geo = get_ip_location(d)
        
        # 组装成标准格式
        formatted_line = f"{d}:443#{node_geo}-【{province} · {isp}-优选】"
        results.append(formatted_line)
        print(f"已整理 -> {formatted_line}")

    return results

if __name__ == "__main__":
    final_list = extract_all_22_domains()
    if final_list:
        final_list = sorted(list(set(final_list)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_list))
        print(f"\n🎉 大功告成！已成功将所有 {len(final_list)} 个节点完整写入到 {OUTPUT_FILE}")
    else:
        print("未提取到域名数据。")
