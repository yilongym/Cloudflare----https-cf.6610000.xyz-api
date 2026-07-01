import os
import re
import requests

OUTPUT_FILE = "cloudflare_proxies.txt"

# 定义省份和运营商的提取映射字典，用来把域名前缀转换成中文
PROV_MAP = {
    "cq": "重庆", "fj": "福建", "gd": "广东", "gx": "广西", "gz": "贵州", 
    "js": "江苏", "jx": "江西", "ln": "辽宁", "sd": "山东", "sh": "上海", 
    "sc": "四川", "yn": "云南", "zj": "浙江", "tj": "天津", "sx": "陕西", "sa": "陕西"
}

def fetch_all_possible_ips():
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://cf.6610000.xyz/"
    }
    
    # 策略 1：尝试直接拉取背后的测速文本接口
    urls_to_try = [
        "https://cf.6610000.xyz/speed.txt",
        "https://cf.6610000.xyz/"
    ]
    
    raw_text = ""
    for url in urls_to_try:
        try:
            print(f"正在尝试抓取源: {url}")
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            if res.status_code == 200 and len(res.text) > 100:
                raw_text += "\n" + res.text
        except Exception as e:
            print(f"抓取 {url} 失败: {e}")
            
    if not raw_text:
        print("未获取到任何网页内容")
        return results

    # 策略 2：直接用超强正则表达式从所有文本中提取域名 (如 cq.ct.6610000.xyz)
    # 不管它在 HTML、JS 还是 JSON 里，只要出现就抓出来
    found_domains = re.findall(r'([a-zA-Z0-9\.-]+\.6610000\.xyz)', raw_text)
    # 去重
    found_domains = list(set(found_domains))
    
    print(f"提取到所有可能的域名列表: {found_domains}")

    for domain in found_domains:
        # 过滤掉纯主域名
        if domain == "6610000.xyz" or domain == "cf.6610000.xyz":
            continue
            
        # 拆解域名前缀获取省份和运营商 (例如: cq.ct.6610000.xyz -> 前缀 cq, 运营商 ct)
        parts = domain.split('.')
        prefix = parts[0].lower() if len(parts) > 0 else "未知"
        isp_code = parts[1].lower() if len(parts) > 1 else "unknown"
        
        # 转换省份中文
        province = PROV_MAP.get(prefix, "其他")
        
        # 转换运营商中文
        if "ct" in isp_code:
            isp = "中国电信"
        elif "cm" in isp_code:
            isp = "中国移动"
        elif "cu" in isp_code:
            isp = "中国联通"
        else:
            isp = "公共网络"
            
        # 根据您要求的格式进行强制拼接包装
        # 格式示例: cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】
        formatted_line = f"{domain}:443#东京 · NRT-【{province} · {isp}-优选】"
        results.append(formatted_line)
        
    return results

if __name__ == "__main__":
    ip_list = fetch_all_possible_ips()
    if ip_list:
        # 去重并排序
        ip_list = sorted(list(set(ip_list)))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(ip_list))
        print(f"成功！已生成文件，共抓取到 {len(ip_list)} 条优选记录！")
    else:
        # 终极兜底：如果连正则都抓不到，强行写一个测试文件，用来测试您的 GitHub 权限是否真的开通
        print("警告：没有匹配到任何域名，开始执行写入测试，强制生成测试文本...")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("cq.ct.6610000.xyz:443#东京 · NRT-【重庆 · 中国电信-优选】\n")
            f.write("fj.ct.6610000.xyz:443#归属未知-【福建 · 中国电信-优选】\n")
        print("强行写入测试成功，请在运行完毕后查看仓库根目录。")
