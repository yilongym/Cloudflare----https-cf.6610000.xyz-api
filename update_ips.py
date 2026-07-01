import os
import requests

OUTPUT_FILE = "cloudflare_proxies.txt"

# 固定的省份/运营商代码映射（用来将 cq.ct 动态转换为“重庆 · 中国电信”）
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def fetch_dynamic_panel_data():
    # 动态面板的核心异步数据源接口（网页上所有的22个卡片全是从这个 JSON 实时渲染出来的）
    json_url = "https://raw.githubusercontent.com/10000get/10000cf.ip/main/data.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    results = []
    try:
        print("正在请求面板动态 JSON 数据接口...")
        res = requests.get(json_url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            # 兼容有些面板的外层包裹字段，获取核心列表
            nodes_list = data if isinstance(data, list) else data.get("nodes", [])
            print(f"成功获取到动态数据！当前线上一共有 {len(nodes_list)} 个活跃节点，开始实时解析...")
            
            for item in nodes_list:
                # 动态提取接口中的核心字段
                domain = item.get("domain", "").strip()
                # 动态获取当前最新测速后分配的落地机房/路由名称（如 "东京 · NRT" 或 "香港 · HKG"）
                node_name = item.get("node", "归属未知").strip()
                
                if not domain:
                    continue
                
                # 动态解析域名内部的地区和运营商代码
                domain_lower = domain.lower()
                parts = domain_lower.split('.')
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
                
                # 严格按照您要求的格式动态拼接
                # 格式: 域名:443#动态机房-【动态省份 · 动态运营商-优选】
                formatted_line = f"{domain}:443#{node_name}-【{province} · {isp}-优选】"
                results.append(formatted_line)
                print(f"解析成功 -> {formatted_line}")
        else:
            print(f"接口请求失败，状态码: {res.status_code}")
    except Exception as e:
        print(f"读取动态接口时发生异常: {e}")
        
    return results

if __name__ == "__main__":
    dynamic_ips = fetch_dynamic_panel_data()
    
    if dynamic_ips:
        # 排序并去重
        dynamic_ips = sorted(list(set(dynamic_ips)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(dynamic_ips))
        print(f"\n🎉 完美同步！已成功动态抓取全部 {len(dynamic_ips)} 个节点并写入到 {OUTPUT_FILE}")
    else:
        print("❌ 未能获取到动态数据，请检查网络或接口地址。")
