import os
import re
import requests

OUTPUT_FILE = "cloudflare_proxies.txt"

# 核心数据映射字典（用于标准化输出格式）
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def fetch_and_standardize():
    # 结合项目文档，直接读取最底层的 speed.txt 数据源接口
    source_url = "https://raw.githubusercontent.com/10000get/10000cf.ip/main/speed.txt"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    results = []
    try:
        print("开始向源头数据接口发起请求...")
        res = requests.get(source_url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            lines = res.text.splitlines()
            print(f"成功获取到原始测速文本，共 {len(lines)} 行，开始标准化格式...")
            
            for line in lines:
                line = line.strip()
                if not line or "#" not in line:
                    continue
                
                # 原始格式通常为：cq.ct.6610000.xyz:443#东京 · NRT
                # 或者：cq.ct.6610000.xyz:443#归属未知
                parts = line.split('#')
                domain_part = parts[0].strip()
                node_name = parts[1].strip() if len(parts) > 1 else "归属未知"
                
                # 提取省份和运营商代码 (如 cq.ct.6610000.xyz -> cq, ct)
                domain_lower = domain_part.lower()
                domain_pieces = domain_lower.split('.')
                
                prefix = domain_pieces[0] if len(domain_pieces) > 0 else ""
                isp_code = domain_pieces[1] if len(domain_pieces) > 1 else ""
                
                # 1. 匹配省份中文
                province = PROV_MAP.get(prefix, prefix.upper() if prefix else "未知地区")
                
                # 2. 匹配运营商中文
                if "ct" in isp_code:
                    isp = "中国电信"
                elif "cm" in isp_code:
                    isp = "中国移动"
                elif "cu" in isp_code:
                    isp = "中国联通"
                else:
                    isp = "公共网络"
                
                # 3. 按照您的标准要求重新组装
                # 示例格式: cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】
                formatted_line = f"{domain_part}#{node_name}-【{province} · {isp}-优选】"
                results.append(formatted_line)
                
    except Exception as e:
        print(f"请求接口时发生错误: {e}")
        
    return results

if __name__ == "__main__":
    final_ips = fetch_and_standardize()
    
    if final_ips:
        # 去重并排序
        final_ips = sorted(list(set(final_ips)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_ips))
        print(f"🎉 转换完成！已完整导出 {len(final_ips)} 条优选记录至 {OUTPUT_FILE}")
    else:
        print("❌ 未能成功提取到任何数据。")
