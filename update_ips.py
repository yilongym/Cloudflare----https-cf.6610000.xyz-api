import urllib.request
import re
import os

OUTPUT_FILE = "cloudflare_proxies.txt"

# 省份/运营商代码映射字典 (用于将域名动态翻译为纯净的中文，杜绝第三方API产生“所有权”杂质)
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ha": "河南", "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", 
    "he": "河北", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def fetch_data_from_panel(url):
    """使用原生标准库拉取面板实时数据"""
    req = urllib.request.Request(
        url, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"📡 尝试拉取接口 {url} 提示: {e}")
        return ""

def main():
    print("🚀 开始完全动态同步众测面板网页最新数据 center...")
    
    # 汇聚面板底层核心测速结果文本流接口
    target_url = "https://cf.6610000.xyz/speed.txt"
    raw_text = fetch_data_from_panel(target_url)
    
    if not raw_text or len(raw_text.strip()) < 10:
        # 备用源：如果 speed.txt 被防爬限制，直接读取前端页面的核心文本流
        print("⚠️ 优先接口未返回充分数据，启动备用全量文本探测...")
        raw_text = fetch_data_from_panel("https://cf.6610000.xyz")

    # 1. 动态匹配所有形如 `域名:端口#机房信息` 或单独 `域名` 及其上下文的相关数据
    # 正则表达式：精准捕获所有 6610000.xyz 结尾的活跃子域名
    domains = re.findall(r'([a-zA-Z0-9\-\.]+6610000\.xyz)', raw_text)
    domains = list(set([d.lower().strip().strip('.') for d in domains]))
    
    results = []
    print(f"📋 本次运行动态探测到线上共有 {len(domains)} 个活跃节点域名，开始实时同步机房与备注...")

    for domain in domains:
        # 过滤主面板域名本身
        if domain in ["cf.6610000.xyz", "6610000.xyz", "www.6610000.xyz"]:
            continue
            
        # 2. 动态捕捉当前网页上该域名最实时的最新落地机房 (例如：从上下文抓取“东京 · NRT”、“香港 · HKG”)
        node_geo = "Anycast · 优选" # 默认兜底
        pos = raw_text.find(domain)
        if pos != -1:
            # 截取域名周边的上下文，寻找形如“城市 · 机场三字码”的网页实时渲染文本
            context = raw_text[max(0, pos-300):min(len(raw_text), pos+300)]
            geo_match = re.search(r'([\u4e00-\u9fa5]+[^"\n]*·\s*[A-Z]{3})', context)
            if geo_match:
                node_geo = geo_match.group(1).strip()
            else:
                geo_match_simple = re.search(r'([\u4e00-\u9fa5]+\s*·\s*[A-Z]+)', context)
                if geo_match_simple and "优选" not in geo_match_simple.group(1):
                    node_geo = geo_match_simple.group(1).strip()

        # 3. 通过域名内部自带的二级代码，动态、安全地翻译地区与运营商
        parts = domain.split('.')
        prefix = parts[0] if len(parts) > 0 else ""
        isp_code = parts[1] if len(parts) > 1 else ""
        
        # 精准匹配省份
        province = PROV_MAP.get(prefix, prefix.upper() if prefix else "优选")
        
        # 精准匹配运营商
        if "ct" in isp_code:
            isp = "中国电信"
        elif "cm" in isp_code:
            isp = "中国移动"
        elif "cu" in isp_code:
            isp = "中国联通"
        else:
            isp = "中国移动" if "cm" in domain else "中国电信" # 智能兜底

        # 4. 严格组装为您要求的完美正确格式，绝不掺杂任何所有权垃圾字符
        # 格式示例：cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】
        formatted_line = f"{domain}:443#{node_geo}-【{province} · {isp}-优选】"
        results.append(formatted_line)
        print(f"✅ 成功动态生成 -> {formatted_line}")

    # 5. 写入并保存
    if results:
        results = sorted(list(set(results)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        print(f"\n🎉 大功告成！已成功动态同步网页全量 {len(results)} 个活跃节点到 {OUTPUT_FILE}")
    else:
        print("❌ 未能获取到任何活跃数据，请检查面板网络连接。")

if __name__ == "__main__":
    main()
