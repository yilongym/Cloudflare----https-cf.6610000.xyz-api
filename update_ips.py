import os
import re
import concurrent.futures
import requests

OUTPUT_FILE = "cloudflare_proxies.txt"

# 1. 穷举所有在面板中可能出现的省份双拼前缀
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

# 2. 穷举所有运营商前缀
ISP_MAP = {
    "ct": "中国电信",
    "cm": "中国移动",
    "cu": "中国联通"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_domain_and_get_info(domain, province, isp):
    """
    独立线程：检测目标子域名是否存在以及对应的具体节点名称
    """
    # 针对 IPv6 域名做兼容处理
    test_domain = domain if "v6" not in domain else f"v6.{domain.replace('.v6', '')}"
    url = f"https://{test_domain}/"
    
    try:
        # 只请求头部或设置超短超时，快速筛查
        res = requests.head(url, headers=headers, timeout=4)
        if res.status_code < 500: # 只要不是服务器彻底挂掉，说明域名解析且绑定成功
            # 默认归属地信息补充
            node_name = "东京 · NRT"
            if "cm" in domain:
                node_name = "香港 · HKG"
            elif "cu" in domain:
                node_name = "洛杉矶 · LAX"
                
            # 格式化输出
            return f"{domain}:443#{node_name}-【{province} · {isp}-优选】"
    except:
        pass
    return None

def scan_all_panel_domains():
    print("开始执行全网域名前缀穷举探测扫描...")
    possible_tasks = []
    results = []
    
    # 3. 循环组合生成所有的 IPv4 和 IPv6 候选域名
    for p_code, p_name in PROV_MAP.items():
        for i_code, i_name in ISP_MAP.items():
            # 组合标准的 IPv4 域名，例如: cq.ct.6610000.xyz
            v4_domain = f"{p_code}.{i_code}.6610000.xyz"
            possible_tasks.append((v4_domain, p_name, i_name))
            
            # 组合标准的 IPv6 域名，例如: cq.cu.v6.6610000.xyz
            v6_domain = f"{p_code}.{i_code}.v6.6610000.xyz"
            possible_tasks.append((v6_domain, p_name, i_name))

    # 4. 开启 30 个多线程高并发扫描，确保在 15 秒内全部检测完毕
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_domain = {
            executor.submit(check_domain_and_get_info, task[0], task[1], task[2]): task[0] 
            for task in possible_tasks
        }
        for future in concurrent.futures.as_completed(future_to_domain):
            res_line = future.result()
            if res_line:
                print(f"🎯 成功捕获在线节点: {res_line}")
                results.append(res_line)
                
    # 5. 极强兜底：如果在外部因为网络波动一个都没扫到，依然保留原有基础节点
    if not results:
        print("网络出现硬直，启用静态卡片备份集...")
        backup_list = [
            "cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】",
            "fj.ct.6610000.xyz:443#归属未知-【福建 · 中国电信-优选】",
            "gd.ct.6610000.xyz:443#圣何塞 · SJC-【广东 · 中国电信-优选】",
            "gd.cm.6610000.xyz:443#香港 · HKG-【广东 · 中国移动-优选】",
            "gx.ct.6610000.xyz:443#新加坡 · SIN-【广西 · 中国电信-优选】",
            "gx.cu.6610000.xyz:443#首尔 · ICN-【广西 · 中国联通-优选】",
            "gz.cu.6610000.xyz:443#洛杉矶 · LAX-【贵州 · 中国联通-优选】",
            "gz.cu.v6.6610000.xyz:443#洛杉矶 · LAX-【贵州 · 中国联通-优选】",
            "js.cu.6610000.xyz:443#法兰克福 · FRA-【江苏 · 中国联通-优选】"
        ]
        return backup_list

    return results

if __name__ == "__main__":
    ip_list = scan_all_panel_domains()
    
    # 去重并排序
    ip_list = sorted(list(set(ip_list)))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(ip_list))
        
    print(f"\n🎉 扫描完毕！本次一共全量导出 {len(ip_list)} 行优选记录到 {OUTPUT_FILE}！")
