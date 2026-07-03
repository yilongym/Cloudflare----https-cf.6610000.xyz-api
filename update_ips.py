import urllib.request
import json
import socket

OUTPUT_FILE = "cloudflare_proxies.txt"
DATA_URL = "https://cf.6610000.xyz/data.json"

# 精准的国家/地区映射
COUNTRY_MAP = {
    "HK": "中国香港", "TW": "中国台湾", "JP": "日本", "SG": "新加坡", 
    "KR": "韩国", "US": "美国", "DE": "德国", "GB": "英国", 
    "FR": "法国", "NL": "荷兰", "AU": "澳大利亚", "CN": "中国",
    "MO": "中国澳门", "CA": "加拿大", "FI": "芬兰", "RU": "俄罗斯"
}

# 扩容版：全球高频机场三字码 -> 干净中文地名映射
COLO_CITY_MAP = {
    "NRT": "东京", "HND": "东京", "HKG": "香港", "SIN": "新加坡",
    "ICN": "首尔", "GMP": "首尔", "TPE": "台北", "TSA": "台北",
    "SJC": "圣何塞", "LAX": "洛杉矶", "SEA": "西雅图", "SFO": "旧金山",
    "JFK": "纽约", "EWR": "纽约", "IAD": "阿什本", "ORD": "芝加哥",
    "DFW": "达拉斯", "MIA": "迈阿密", "SNA": "圣安娜", "PDX": "波特兰",
    "FRA": "法兰克福", "LHR": "伦敦", "CDG": "巴黎", "AMS": "阿姆斯特丹",
    "ARN": "斯德哥尔摩", "SYD": "悉尼", "KUL": "吉隆坡", "BKK": "曼谷",
    "MNL": "马尼拉", "MFM": "澳门"
}

# 省份代码映射字典
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西", 
    "ha": "河南", "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", 
    "he": "河北", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def get_accurate_ip_geo(ip_address):
    """穿透 Anycast：直接拿具体解析出来的 IP 强制查询真实的物理落地"""
    try:
        # 使用官方无防爬、支持直查具体IP的公开地理库（带中文参数）
        url = f"http://ip-api.com/json/{ip_address}?lang=zh-CN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("status") == "success":
                country_code = data.get("countryCode", "SG")
                city = data.get("city", "")
                org = data.get("org", "").upper()
                
                # 提取组织或城市信息中的三字码特征
                found_colo = "Anycast"
                for code in COLO_CITY_MAP.keys():
                    if code in org or code in city.upper():
                        found_colo = code
                        break
                
                # 特殊逻辑高优先级纠正
                if "Hong Kong" in city or "HKG" in org:
                    return "中国香港 · HKG"
                if "Taiwan" in data.get("country", "") or "Taipei" in city:
                    return "中国台湾 · 台北 · TPE"
                if "Tokyo" in city or "Narita" in city or "NRT" in org:
                    return "日本 · 东京 · NRT"
                
                # 组合最终规范的名称
                country_name = COUNTRY_MAP.get(country_code, data.get("country", "海外地区"))
                city_chinese = COLO_CITY_MAP.get(found_colo, city)
                
                if found_colo != "Anycast":
                    return f"{country_name} · {city_chinese} · {found_colo}"
                else:
                    return f"{country_name} · {city_chinese}" if city_chinese else f"{country_name}"
    except Exception:
        pass
    return None

def main():
    print("🚀 启动全量智能多源混合探测引擎...")
    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = json.loads(response.read().decode('utf-8'))
            info_list = raw_data.get("info", []) if isinstance(raw_data, dict) else raw_data
            
            if not info_list:
                print("❌ 数据源中未发现活跃节点。")
                return
                
            results = []
            for item in info_list:
                domain = item.get("domain", "").strip()
                if not domain or domain in ["6610000.xyz", "www.6610000.xyz"]:
                    continue
                
                # 1. 动态解析该域名当前在网络上被分配的真实目标IP
                try:
                    real_ip = socket.gethostbyname(domain)
                except Exception:
                    continue  # 解析失败说明该节点暂时不可用，跳过
                
                # 2. 穿透 Anycast 强制获取这个 IP 真正的归属地
                geo_str = get_accurate_ip_geo(real_ip)
                
                # 3. 如果穿透查询失败，再读取 JSON 的字段作为第二防线兜底
                if not geo_str:
                    colo = item.get("colo", "Anycast").upper()
                    country_code = item.get("country", "SG").upper()
                    country_name = COUNTRY_MAP.get(country_code, "海外地区")
                    city_name = COLO_CITY_MAP.get(colo, colo)
                    
                    if colo in ["HKG", "HK"]: geo_str = "中国香港 · HKG"
                    elif colo in ["TPE", "TW"]: geo_str = "中国台湾 · 台北 · TPE"
                    else: geo_str = f"{country_name} · {city_name} · {colo}" if city_name != colo else f"{country_name} · {colo}"
                
                # 4. 切割域名提取上传用户的省份和运营商
                parts = domain.split('.')
                prefix = parts[0]
                isp_code = parts[1] if len(parts) > 1 else ""
                
                user_province = PROV_MAP.get(prefix, "通用")
                if "ct" in isp_code: user_isp = "中国电信"
                elif "cm" in isp_code: user_isp = "中国移动"
                elif "cu" in isp_code: user_isp = "中国联通"
                else: user_isp = "中国移动" if "cm" in domain else "中国电信"
                
                # 5. 生成极其纯净完美的格式
                formatted_line = f"{domain:443}#{geo_str}-【{user_province} · {user_isp}-优选】"
                results.append(formatted_line)
                print(f"✅ 成功穿透判定 -> {formatted_line}")
                
            # 排序去重并保存
            if results:
                results = sorted(list(set(results)))
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(results))
                print(f"\n🎉 大功告成！已成功穿透生成 {len(results)} 个真实物理机房节点至 {OUTPUT_FILE}！")
                
    except Exception as e:
        print(f"❌ 运行中出现未预料的错误: {e}")

if __name__ == "__main__":
    main()
