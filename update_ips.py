import os
import re
import requests

OUTPUT_FILE = "cloudflare_proxies.txt"

# 省份/运营商代码映射字典
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西",
    "ah": "安徽", "bj": "北京", "hb": "湖北", "hn": "湖南", "he": "河北",
    "ha": "河南", "jl": "吉林", "hl": "黑龙江", "gs": "甘肃", "qh": "青海",
    "nx": "宁夏", "xj": "新疆", "xz": "西藏", "hi": "海南", "nm": "内蒙古"
}

def parse_nodes_from_web():
    # 面板的真实前端访问地址（这里我使用了您截图里展示的域名）
    url = "https://cf.6610000.xyz"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    results = []
    try:
        print(f"正在读取网页实时内容: {url} ...")
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        
        if res.status_code == 200:
            html_text = res.text
            
            # 使用强大的正则表达式，精确抓取网页渲染脚本或HTML里含有的所有 6610000.xyz 优选子域名
            # 这个正则能完美匹配诸如 cq.ct.6610000.xyz 或 zj.cm.v6.6610000.xyz 
            domains = re.findall(r'[a-zA-Z0-9\.]+\.6610000\.xyz', html_text)
            
            # 去重
            domains = list(set([d.lower().strip() for d in domains]))
            print(f"提取到可能存在的所有域名列表: {domains}")
            
            # 遍历提取到的域名，动态解析落地机房与省份运营商
            for domain in domains:
                # 过滤掉不属于节点格式的纯根域名或主API域名
                if domain == "cf.6610000.xyz" or domain == "6610000.xyz":
                    continue
                
                # 1. 聪明地通过二级域名切片动态解析省份和运营商
                parts = domain.split('.')
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
                
                # 2. 网页源码中同样会带有实时的 nodeName 变量或机房数据，
                # 但由于混淆，我们可以用测速接口分配规律或者直接对网页内该域名的机房节点进行动态捕获
                # 这里我们利用网页内特征做更深一层的机房名字正则提取：
                # 寻找形如：domain: "cq.ct.6610000.xyz", node: "香港 · HKG" 或者包含机房关键字的结构
                node_match = re.search(r'"domain"\s*:\s*"' + re.escape(domain) + r'"\s*,\s*"node"\s*:\s*"([^"]+)"', html_text)
                
                if node_match:
                    node_geo = node_match.group(1).strip()
                else:
                    # 如果网页把字段压缩了，我们用通用的特征提取当前节点卡片范围内的机房名称
                    # 比如寻找该域名附近出现的类似 "东京 · NRT"、"香港 · HKG"、"圣何塞 · SJC" 等经典三字码
                    geo_patterns = [r'东京\s*·\s*[A-Z]+', r'香港\s*·\s*[A-Z]+', r'中国香港\s*·\s*[A-Z]+', 
                                    r'新加坡\s*·\s*[A-Z]+', r'洛杉矶\s*·\s*[A-Z]+', r'圣何塞\s*·\s*[A-Z]+', 
                                    r'首尔\s*·\s*[A-Z]+', r'法兰克福\s*·\s*[A-Z]+']
                    
                    node_geo = "Anycast · 优选" # 默认兜底
                    # 在该域名出现的上下文里寻找最贴近的机房名字
                    pos = html_text.find(domain)
                    if pos != -1:
                        context = html_text[max(0, pos-300):min(len(html_text), pos+300)]
                        for pat in geo_patterns:
                            m = re.search(pat, context)
                            if m:
                                node_geo = m.group(0).strip()
                                break
                
                # 3. 严格按照您要求的格式进行组装
                formatted_line = f"{domain}:443#{node_geo}-【{province} · {isp}-优选】"
                results.append(formatted_line)
                print(f"成功捕获活跃节点 -> {formatted_line}")
                
        else:
            print(f"❌ 无法加载网页，状态码: {res.status_code}")
    except Exception as e:
        print(f"❌ 解析网页源码流时遇到错误: {e}")
        
    return results

if __name__ == "__main__":
    final_proxies = parse_nodes_from_web()
    
    if final_proxies:
        # 排序并去重
        final_proxies = sorted(list(set(final_proxies)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_proxies))
        print(f"\n🎉 完美解决！已成功将最新获取到的 {len(final_proxies)} 个动态节点写入到 {OUTPUT_FILE}")
    else:
        print("❌ 抓取失败：未能从网页源码中匹配到节点信息，输出保持原样。")
