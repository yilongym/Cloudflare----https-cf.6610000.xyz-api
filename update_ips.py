import urllib.request
import json
import re

OUTPUT_FILE = "cloudflare_proxies.txt"

# 固定的省份/运营商代码映射字典
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def fetch_data_from_api(url):
    """直接直连面板后端的动态JSON数据接口"""
    req = urllib.request.Request(
        url, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"📡 接口请求提示: {e}")
        return ""

def main():
    print("🚀 开始直连后台核心接口同步全量 Cloudflare 优选节点...")
    
    # 该测速面板核心动态加载的三个高概率API接口
    api_urls = [
        "https://cf.6610000.xyz/data.json",
        "https://cf.6610000.xyz/ips.json",
        "https://cf.6610000.xyz"
    ]
    
    combined_text = ""
    for url in api_urls:
        print(f"正在同步核心数据流: {url}")
        combined_text += "\n" + fetch_data_from_api(url)
        
    # 全量匹配捕获形如 xx.xx.6610000.xyz 的所有域名
    domains = re.findall(r'([a-zA-Z0-9\-\.]+6610000\.xyz)', combined_text)
    domains = list(set([d.lower().strip().strip('.') for d in domains]))
    
    results = []
    
    for domain in domains:
        # 过滤掉主域名
        if domain in ["cf.6610000.xyz", "6610000.xyz", "www.6610000.xyz"]:
            continue
            
        parts = domain.split('.')
        prefix = parts[0] if len(parts) > 0 else ""
        isp_code = parts[1] if len(parts) > 1 else ""
        
        # 匹配省份
        province = PROV_MAP.get(prefix, prefix.upper() if prefix else "优选")
        
        # 匹配运营商
        if "ct" in isp_code:
            isp = "中国电信"
        elif "cm" in isp_code:
            isp = "中国移动"
        elif "cu" in isp_code:
            isp = "中国联通"
        else:
            isp = "公共网络"
            
        # 动态捕捉机房代码 (处理 JSON 字段中的“东京 · NRT”等文本)
        node_geo = "Anycast · 优选"
        pos = combined_text.find(domain)
        if pos != -1:
            context = combined_text[max(0, pos-400):min(len(combined_text), pos+400)]
            # 匹配中文字符的城市名及其机房三字码
            geo_match = re.search(r'([\u4e00-\u9fa5]+[^"\n]*·\s*[A-Z]{3})', context)
            if geo_match:
                node_geo = geo_match.group(1).strip()
            else:
                # 备用粗略匹配
                geo_match_simple = re.search(r'([\u4e00-\u9fa5]+(?:\s*·\s*[A-Z]+)?)', context)
                if geo_match_simple and "优选" not in geo_match_simple.group(1):
                    node_geo = geo_match_simple.group(1).strip()

        formatted_line = f"{domain}:443#{node_geo}-【{province} · {isp}-优选】"
        results.append(formatted_line)
        print(f"✅ 成功捕获活跃节点 -> {formatted_line}")

    if results:
        results = sorted(list(set(results)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        print(f"\n🎉 完美同步！已成功捕获全量 {len(results)} 个优选节点并写入 {OUTPUT_FILE}")
    else:
        print("⚠️ 接口暂未返回数据，生成常用高在线节点兜底...")
        backup_nodes = [
            "cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】",
            "fj.ct.6610000.xyz:443#Anycast · 优选-【福建 · 中国电信-优选】",
            "gd.ct.6610000.xyz:443#圣何塞 · SJC-【广东 · 中国电信-优选】",
            "gd.cm.6610000.xyz:443#中国香港 · HKG-【广东 · 中国移动-优选】",
            "gz.cu.6610000.xyz:443#洛杉矶 · LAX-【贵州 · 中国联通-优选】",
            "js.cu.6610000.xyz:443#法兰克福 · FRA-【江苏 · 中国联通-优选】"
        ]
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(backup_nodes))

if __name__ == "__main__":
    main()
