import urllib.request
import json
import re

OUTPUT_FILE = "cloudflare_proxies.txt"

# 固定的纯净中文映射，杜绝产生乱七八糟的“所有权”杂质
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ha": "河南", "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", 
    "he": "河北", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def main():
    print("🚀 开始通过 GitHub 后端数据流接口同步 Cloudflare 优选节点...")
    
    # 直接对接原作者最底层的测速数据源文件（绕过网页CF盾，100%可以读取成功）
    data_url = "https://raw.githubusercontent.com/10000get/10000cf.ip/main/speed.txt"
    
    req = urllib.request.Request(
        data_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"❌ 原始数据源请求失败: {e}")
        return

    # 正则精准匹配含 6610000.xyz 及其整行数据 (形如 cq.ct.6610000.xyz:443#东京 · NRT)
    # 这样可以直接把对方测速后最新的机房信息原封不动拿过来
    pattern = r'([a-zA-Z0-9\-\.]+6610000\.xyz:443#([^-\n]+))'
    matches = re.findall(pattern, content)
    
    results = []
    print(f"📋 成功连通底层数据流！发现当前线上最新的节点共 {len(matches)} 个，开始格式化备注...")

    for match in matches:
        full_node = match[0].strip()   # 形如 cq.ct.6610000.xyz:443#东京 · NRT
        domain_part = full_node.split(':')[0].lower() # 提取域名 cq.ct.6610000.xyz
        
        # 通过域名内部自带的二级代码，动态、安全地翻译地区与运营商
        parts = domain_part.split('.')
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
            isp = "中国移动" if "cm" in domain_part else "中国电信"

        # 严格组装为您要求的正确格式（末尾带上您要的 -优选】）
        formatted_line = f"{full_node}-【{province} · {isp}-优选】"
        results.append(formatted_line)
        print(f"✅ 动态跟进 -> {formatted_line}")

    if results:
        results = sorted(list(set(results)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        print(f"\n🎉 同步成功！已动态拉取最新 {len(results)} 个节点并完美写入 {OUTPUT_FILE}")
    else:
        print("⚠️ 数据解析流为空，请检查上游源文件。")

if __name__ == "__main__":
    main()
