import os
import requests

OUTPUT_FILE = "cloudflare_proxies.txt"

# 固定的省份/运营商代码映射（用于将域名中的前缀动态翻译为中文）
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def fetch_all_dynamic_nodes():
    # 核心：10000cf.ip 项目真正的后端动态测速全量 JSON 数据库接口
    json_url = "https://raw.githubusercontent.com/10000get/10000cf.ip/main/data.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    results = []
    try:
        print("正在向汇聚面板的动态数据源头请求实时数据...")
        res = requests.get(json_url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            
            # 兼容处理：支持直接是列表，或者嵌套在 info/nodes 里的结构
            if isinstance(data, list):
                nodes_list = data
            elif isinstance(data, dict):
                nodes_list = data.get("nodes", data.get("info", []))
            else:
                nodes_list = []
                
            print(f"✅ 成功连接接口！当前线上一共有 {len(nodes_list)} 个动态卡片，开始洗数...")
            
            for item in nodes_list:
                if not isinstance(item, dict):
                    continue
                    
                # 1. 动态提取最新域名
                domain = item.get("domain", "").strip()
                if not domain:
                    continue
                
                # 2. 动态提取当前最新测速分配的落地机房 (例如: "东京 · NRT", "香港 · HKG")
                # 优先取 node 字段，如果没有则取当前分配的 IP
                node_geo = item.get("node", "").strip()
                if not node_geo or "未知" in node_geo:
                    node_geo = item.get("app", "Anycast · 优选")
                
                # 3. 聪明地通过二级域名切片动态解析省份和运营商
                domain_lower = domain.lower()
                parts = domain_lower.split('.')
                prefix = parts[0] if len(parts) > 0 else ""
                isp_code = parts[1] if len(parts) > 1 else ""
                
                # 匹配省份中文
                province = PROV_MAP.get(prefix, prefix.upper() if prefix else "优选")
                
                # 匹配运营商中文
                if "ct" in isp_code:
                    isp = "中国电信"
                elif "cm" in isp_code:
                    isp = "中国移动"
                elif "cu" in isp_code:
                    isp = "中国联通"
                else:
                    isp = "公共网络"
                
                # 4. 严格按照要求的标准格式组装
                # 格式示例: cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】
                formatted_line = f"{domain}:443#{node_geo}-【{province} · {isp}-优选】"
                results.append(formatted_line)
                print(f"已捕获 -> {formatted_line}")
                
        else:
            print(f"❌ 动态接口请求失败，状态码: {res.status_code}")
    except Exception as e:
        print(f"❌ 解析动态数据流时遇到错误: {e}")
        
    return results

if __name__ == "__main__":
    final_proxies = fetch_all_dynamic_nodes()
    
    if final_proxies:
        # 排序并去重
        final_proxies = sorted(list(set(final_proxies)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_proxies))
        print(f"\n🎉 完美搞定！已成功将最新的 {len(final_proxies)} 个动态节点写入到 {OUTPUT_FILE}")
    else:
        print("❌ 未抓取到任何数据，请检查网络或稍后重试。")
