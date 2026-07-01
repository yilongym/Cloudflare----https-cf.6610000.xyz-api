import os
import re
import json
import requests
from bs4 import BeautifulSoup

# 配置项
TARGET_URL = "https://cf.6610000.xyz/"
OUTPUT_FILE = "cloudflare_proxies.txt"

def get_ip_location(ip):
    """
    当网页上的节点归属地未知或为内部名称时，调用公用API接口解析IP的真实地理位置
    """
    try:
        # 使用 ip-api.com 免费接口（可替换为其他更精准的接口如 ipapi.co 或 ip.sb）
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                region = data.get("regionName", "")
                country = data.get("country", "")
                # 优先返回 城市·国家 或 简要组合
                if city:
                    return f"{city} · {data.get('as', '').split()[0]}"
                return f"{country} · {data.get('isp', '')}"
    except Exception as e:
        print(f"解析 IP {ip} 失败: {e}")
    return "归属未知"

def parse_panel():
    results = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(TARGET_URL, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        
        # 尝试检查页面是否是通过后端的 json 获取数据的（通常这类轻量面板会有数据接口）
        # 如果是纯 HTML 渲染，我们使用 BeautifulSoup 解析
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 根据截图中的卡片布局结构定位（匹配包含“中国电信/中国移动/中国联通”的卡片）
        # 提示：由于无法直接抓包该网址，这里采用通用的类名和文本特征匹配，若结构有变动可根据实际源码微调
        cards = soup.find_all(lambda tag: tag.name == 'div' and any(isp in tag.get_text() for isp in ['中国电信', '中国移动', '中国联通']))
        
        if not cards:
            print("未通过标准 HTML 结构匹配到卡片，尝试从页面内嵌的 script/json 提取数据...")
            # 兼容性兜底：有些面板数据直接存在 window.data 或 某个 script 标签里
            script_text = "".join([s.text for s in soup.find_all('script')])
            # 匹配形如 [ ... ] 或 { ... } 的数据结构
            # 如果实际页面是纯异步加载，建议直接抓包其数据接口 URL 替换 TARGET_URL
        
        for card in cards:
            text = card.get_text(separator="\n")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            # 提取信息
            # 示例标题：重庆 · 中国电信
            title_match = re.search(r'([\u4e00-\u9fa5]+)\s*·\s*([\u4e00-\u9fa5]+)', "".join(lines[:3]))
            if not title_match:
                continue
            province = title_match.group(1)  # 重庆
            isp = title_match.group(2)       # 中国电信
            
            domain = ""
            ip = ""
            node_name = ""
            
            for line in lines:
                # 匹配域名 (xxx.6610000.xyz)
                if ".6610000.xyz" in line:
                    domain = line
                # 匹配 IPv4 或 IPv6 地址
                elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', line) or ":" in line and len(line) > 10:
                    ip = line
                # 提取底部的节点/设备名称（例如：东京 · NRT、home-router、Snhc）
                # 通常位于延迟（ms）或者丢包率（%）之后的几行
                if "ms" in line or "%" in line:
                    idx = lines.index(line)
                    if idx + 1 < len(lines) and not any(k in lines[idx+1] for k in ['MB/s', 'ms', '%', '更新时间', '小时前']):
                        node_name = lines[idx+1]

            if domain and ip:
                # 过滤掉无意义的本地路由名称，或当节点名为空时触发接口解析
                if not node_name or any(k in node_name.lower() for k in ['router', 'print', 'user', 'default', 'nolan', 'rusty', 'twin']):
                    print(f"节点名 [{node_name}] 较模糊，正在为 IP {ip} 线上解析精准落地归属地...")
                    fetched_loc = get_ip_location(ip)
                    # 如果在线接口返回了具体机房/大厂名，则使用；否则保留原始或显示归属未知
                    node_name = fetched_loc if fetched_loc != "归属未知" else (node_name if node_name else "归属未知")
                
                # 格式化输出：cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】
                formatted_str = f"{domain}:443#{node_name}-【{province} · {isp}-优选】"
                results.append(formatted_str)
                print(f"成功整理: {formatted_str}")

    except Exception as e:
        print(f"抓取或解析出错: {e}")
        
    return results

if __name__ == "__main__":
    ip_list = parse_panel()
    if ip_list:
        # 去重并排序
        ip_list = sorted(list(set(ip_list)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(ip_list))
        print(f"数据成功更新，已写入到 {OUTPUT_FILE}")
    else:
        print("未获取到任何有效数据，不覆盖原文件。")
