import urllib.request
import json
import re

OUTPUT_FILE = "cloudflare_proxies.txt"

# 覆盖全国所有省份/直辖市的代码字典（智能翻译上传用户的地区）
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西", 
    "ha": "河南", "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", 
    "he": "河北", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古",
    "tw": "台湾", "hk": "香港", "mo": "澳门"
}

def get_realtime_node_geo(domain):
    """通过高级地理位置接口动态分析该节点当前的【真实落地国家地区（含国家名）及机场三字码】"""
    try:
        url = f"http://ip-api.com/json/{domain}?lang=zh-CN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("status") == "success":
                city = data.get("city", "")
                org = data.get("org", "")
                country = data.get("country", "")
                
                # --- 1. 亚太核心骨干网机场节点识别 (包含国家/地区代码前缀) ---
                if "Hong Kong" in city or "HKG" in org: return "中国香港 · HKG"
                if "Taiwan" in country or "Taipei" in city or "TPE" in org: return "中国台湾 · 台北 · TPE"
                if "Tokyo" in city or "Narita" in city or "NRT" in org or "HND" in org: return "日本 · 东京 · NRT"
                if "Singapore" in city or "SIN" in org: return "新加坡 · SIN"
                if "Seoul" in city or "ICN" in org: return "韩国 · 首尔 · ICN"
                if "Bangkok" in city or "BKK" in org: return "泰国 · 曼谷 · BKK"
                if "Manila" in city or "MNL" in org: return "菲律宾 · 马尼拉 · MNL"
                if "Kuala Lumpur" in city or "KUL" in org: return "马来西亚 · 吉隆坡 · KUL"
                
                # --- 2. 美洲（北美西海岸/东海岸）核心骨干网机场节点识别 ---
                if "San Jose" in city or "SJC" in org: return "美国 · 圣何塞 · SJC"
                if "Los Angeles" in city or "LAX" in org: return "美国 · 洛杉矶 · LAX"
                if "Seattle" in city or "SEA" in org: return "美国 · 西雅图 · SEA"
                if "San Francisco" in city or "SFO" in org: return "美国 · 旧金山 · SFO"
                if "New York" in city or "JFK" in org or "EWR" in org: return "美国 · 纽约 · JFK"
                if "Ashburn" in city or "IAD" in org: return "美国 · 阿什本 · IAD"
                if "Chicago" in city or "ORD" in org: return "美国 · 芝加哥 · ORD"
                if "Dallas" in city or "DFW" in org: return "美国 · 达拉斯 · DFW"
                if "Miami" in city or "MIA" in org: return "美国 · 迈阿密 · MIA"
                
                # --- 3. 欧洲及其他核心骨干网机场节点识别 ---
                if "Frankfurt" in city or "FRA" in org: return "德国 · 法兰克福 · FRA"
                if "London" in city or "LHR" in org: return "英国 · 伦敦 · LHR"
                if "Paris" in city or "CDG" in org: return "法国 · 巴黎 · CDG"
                if "Amsterdam" in city or "AMS" in org: return "荷兰 · 阿姆斯特丹 · AMS"
                if "Stockholm" in city or "ARN" in org: return "瑞典 · 斯德哥尔摩 · ARN"
                if "Sydney" in city or "SYD" in org: return "澳大利亚 · 悉尼 · SYD"
                
                # --- 4. 智能自适应组合：如果遇到了非高频骨干网，则自动组合国家和城市名 ---
                if country and city:
                    return f"{country} · {city}"
                elif country:
                    return f"{country}"
    except Exception:
        pass
    return "新加坡 · SIN"  # 无法联网或探测失败时的公共兜底

def main():
    print("🚀 开始全量扫描并生成带国家地区前缀的活跃优选节点...")
    
    active_domains = []
    isp_types = ["ct", "cm", "cu", "ct.v6", "cm.v6", "cu.v6"]
    
    # 动态探测全国所有可能活跃的上传子域名
    for prov_code in PROV_MAP.keys():
        for isp in isp_types:
            test_domain = f"{prov_code}.{isp}.6610000.xyz"
            try:
                req = urllib.request.Request(f"http://ip-api.com/json/{test_domain}", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=1.5) as res:
                    data = json.loads(res.read().decode('utf-8'))
                    if data.get("status") == "success" and data.get("query") != "127.0.0.1":
                        active_domains.append(test_domain)
            except Exception:
                continue

    active_domains.append("cf.6610000.xyz")
    active_domains = list(set(active_domains))
    
    results = []
    print(f"📋 线上成功提取到 {len(active_domains)} 个活跃上传端，正在重构带国家/地区前缀的备注规范...")

    for domain in active_domains:
        if domain in ["6610000.xyz", "www.6610000.xyz"]:
            continue
            
        # 1. 解析域名，识别出上传该优选 IP 的用户所在的省份和运营商代码
        parts = domain.split('.')
        prefix = parts[0]
        isp_code = parts[1] if len(parts) > 1 else ""
        
        # 翻译上传用户的省份
        user_province = PROV_MAP.get(prefix, "通用")
        
        # 翻译上传用户的运营商
        if "ct" in isp_code: user_isp = "中国电信"
        elif "cm" in isp_code: user_isp = "中国移动"
        elif "cu" in isp_code: user_isp = "中国联通"
        else: user_isp = "中国移动" if "cm" in domain else "中国电信"
            
        # 2. 联网动态探测当前该节点最新的【真实落地国家和地区机房】
        real_geo = get_realtime_node_geo(domain)
        
        # 3. 严格组装为您要求的完美格式
        # 格式：域名:443#[落地国家和地区机房]-【[上传用户省份] · [上传用户运营商]-优选】
        formatted_line = f"{domain}:443#{real_geo}-【{user_province} · {user_isp}-优选】"
        results.append(formatted_line)
        print(f"✅ 已成功转换格式 -> {formatted_line}")

    # 4. 排序并持久化写入文件
    if results:
        results = sorted(list(set(results)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        print(f"\n🎉 搞定！已成功更新 {len(results)} 个带国家前缀的节点到 {OUTPUT_FILE}。")

if __name__ == "__main__":
    main()
