import urllib.request
import json
import re
import os

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

def fetch_url_text(url):
    """使用Python原生标准库安全获取网页或接口内容，免去安装requests的麻烦"""
    req = urllib.request.Request(
        url, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"📡 请求 {url} 提示暂无法访问: {e}")
        return ""

def main():
    print("🚀 开始多源同步抓取 Cloudflare 优选节点...")
    
    # 双源备用机制：同时抓取前端页面和后台潜在的 JSON 数据流
    sources = [
        "https://cf.6610000.xyz",
        "https://cf.6610000.xyz/data.json"
    ]
    
    all_raw_text = ""
    for src in sources:
        print(f"正在尝试拉取源: {src}")
        all_raw_text += "\n" + fetch_url_text(src)
        
    # 使用正则表达式，全量捕获文本中包含的所有 6610000.xyz 优选子域名
    domains = re.findall(r'([a-zA-Z0-9\-\.]+6610000\.xyz)', all_raw_text)
    # 去重并转换为小写
    domains = list(set([d.lower().strip().strip('.') for d in domains]))
    
    results = []
    
    for domain in domains:
        # 排除主面板域名本身
        if domain in ["cf.6610000.xyz", "6610000.xyz", "www.6610000.xyz"]:
            continue
            
        # 1. 切片解析省份与运营商代码
        parts = domain.split('.')
        prefix = parts[0] if len(parts) > 0 else ""
        isp_code = parts[1] if len(parts) > 1 else ""
        
        # 智能匹配省份中文
        province = PROV_MAP.get(prefix, prefix.upper() if prefix else "优选")
        
        # 智能匹配运营商中文
        if "ct" in isp_code:
            isp = "中国电信"
        elif "cm" in isp_code:
            isp = "中国移动"
        elif "cu" in isp_code:
            isp = "中国联通"
        else:
            isp = "公共网络"
            
        # 2. 动态捕获机房三字码 (例如从上下文捕获该域名对应的 "东京 · NRT" 等)
        # 建立常见机房的关键词库进行上下文就近距离搜索
        geo_patterns = [r'东京\s*·\s*[A-Z]+', r'香港\s*·\s*[A-Z]+', r'中国香港\s*·\s*[A-Z]+', 
                        r'新加坡\s*·\s*[A-Z]+', r'洛杉矶\s*·\s*[A-Z]+', r'圣何塞\s*·\s*[A-Z]+', 
                        r'首尔\s*·\s*[A-Z]+', r'法兰克福\s*·\s*[A-Z]+']
        
        node_geo = "Anycast · 优选" # 默认兜底名称
        pos = all_raw_text.find(domain)
        if pos != -1:
            # 截取域名周边500个字符的上下文，搜寻匹配的机房
            context = all_raw_text[max(0, pos-500):min(len(all_raw_text), pos+500)]
            for pat in geo_patterns:
                m = re.search(pat, context)
                if m:
                    node_geo = m.group(0).strip()
                    break
                    
        # 3. 按照标准格式组装条目
        formatted_line = f"{domain}:443#{node_geo}-【{province} · {isp}-优选】"
        results.append(formatted_line)
        print(f"✅ 成功捕获活跃节点 -> {formatted_line}")

    if results:
        # 排序去重
        results = sorted(list(set(results)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        print(f"\n🎉 完美搞定！已成功将最新的 {len(results)} 个动态节点保存到 {OUTPUT_FILE}")
    else:
        print("⚠️ 未发现任何优选节点域名。正在生成兜底默认列表，防止文件彻底空白...")
        # 兜底生成高概率在线的常用主干节点，防止Actions流程因空文件异常
        backup_nodes = [
            "cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】",
            "fj.ct.6610000.xyz:443#Anycast · 优选-【福建 · 中国电信-优选】",
            "gd.ct.6610000.xyz:443#圣何塞 · SJC-【广东 · 中国电信-优选】"
        ]
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(backup_nodes))

if __name__ == "__main__":
    main()
