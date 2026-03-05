import re
import html

def extract_actual_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # In Chrome/Edge view-source, the content is inside <td class="line-content">
    # Each line of the original source is in a new <tr>
    lines = re.findall(r'<td class="line-content">(.*?)</td>', content, re.DOTALL)
    
    # Join lines and unescape
    actual_html = ""
    for line in lines:
        # Remove all HTML tags added by the view-source renderer (like <span class="html-tag">)
        # But be careful not to remove the escaped HTML tags like &lt;div&gt;
        # Actually, the simplest way is to remove anything inside <...> in each line
        # then unescape the remaining entities.
        clean_line = re.sub(r'<[^>]+>', '', line)
        actual_html += html.unescape(clean_line) + "\n"
        
    return actual_html

# Test with university list
uni_html = extract_actual_html('docs/source/view-source_https___diemthi.tuyensinh247.com_diem-chuan.html')
with open('docs/source/uni_list_clean.html', 'w', encoding='utf-8') as f:
    f.write(uni_html)

# Test with benchmark scores
score_html = extract_actual_html('docs/source/view-source_https___diemthi.tuyensinh247.com_diem-chuan_dai-hoc-nong-lam-tphcm-NLS.html')
with open('docs/source/uni_score_clean.html', 'w', encoding='utf-8') as f:
    f.write(score_html)

print("Extraction complete. Check docs/source/uni_list_clean.html and docs/source/uni_score_clean.html")
