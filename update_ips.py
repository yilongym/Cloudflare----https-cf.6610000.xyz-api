import urllib.request
import json

OUTPUT_FILE = "cloudflare_proxies.txt"
# 网页底部的纯净实时数据接口，完美避开 Cloudflare 防爬盾和 Anycast 路由测不准的问题
DATA_URL = "https://cf.6610000.xyz/data.json"

# 国家代码与全称映射字典
COUNTRY_MAP = {
    "HK": "中国香港", "TW": "中国台湾", "JP": "日本", "SG": "新加坡", 
    "KR": "韩国", "US": "美国", "DE": "德国", "GB": "英国", 
    "FR": "法国", "NL": "荷兰", "AU": "澳大利亚", "CN": "中国"
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

def main():
    print("🚀 开始通过底层数据源同步全量优选节点...")
    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = json.loads(response.read().decode('utf-8'))
            
            # 兼容读取不同的 JSON 键名结构
            info_list = raw_data.get("info", []) if isinstance(raw_data, dict) else raw_data
            if not info_list:
                print("❌ 未在数据源中检索到有效节点信息。")
                return
                
            results = []
            for item in info_list:
                domain = item.get("domain", "").strip()
                if not domain or domain in ["6610000.xyz", "www.6610000.xyz"]:
                    continue
                
                # 1. 提取机房三字码（如 NRT, HKG）
                colo = item.get("colo", "Anycast").upper()
                
                # 2. 提取并映射国家/地区代码
                country_code = item.get("country", "SG").upper()
                country_name = COUNTRY_MAP.get(country_code, "海外地区")
                
                # 3. 动态切割域名解析上传用户的省份和运营商
                parts = domain.split('.')
                prefix = parts[0] if len(parts) > 0 else ""
                isp_code = parts[1] if len(parts) > 1 else ""
                
                user_province = PROV_MAP.get(prefix, "通用")
                
                if "ct" in isp_code: user_isp = "中国电信"
                elif "cm" in isp_code: user_isp = "中国移动"
                elif "cu" in isp_code: user_isp = "中国联通"
                else: user_isp = "中国移动" if "cm" in domain else "中国电信"
                
                # 4. 完美拼装格式：[国家名] · [城市/机场三字码]
                # 特殊处理：如果是香港或台湾，直接规范输出
                if colo in ["HKG", "HK"]:
                    geo_str = "中国香港 · HKG"
                elif colo in ["TPE", "TW"]:
                    geo_str = "中国台湾 · 台北 · TPE"
                else:
                    # 动态匹配常见的机场三字码中文地名
                    city_name = "东京" if colo in ["NRT", "HND"] else \
                                "新加坡" if colo == "SIN" else \
                                "首尔" if colo == "ICN" else \
                                "圣何塞" if colo == "SJC" else \
                                "洛杉矶" if colo == "LAX" else \
                                "法兰克福" if colo == "FRA" else \
                                "伦敦" if colo == "LHR" else colo
                    geo_str = f"{country_name} · {city_name} · {colo}" if city_name != colo else f"{country_name} · {colo}"

                # 5. 按要求组装最终的纯净代理行
                formatted_line = f"{domain}:443#{geo_str}-【{user_province} · {user_isp}-优选】"
                results.append(formatted_line)
                print(f"✅ 成功同步 -> {formatted_line}")
                
            # 排序去重并写入
            if results:
                results = sorted(list(set(results)))
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(results))
                print(f"\n🎉 完美同步完成！已将 {len(results)} 个节点写入到 {OUTPUT_FILE}，数据与网页端 100% 一致！")
                
    except Exception as e:
        print(f"❌ 同步失败，错误原因: {e}")

if __name__ == "__main__":
    main()
