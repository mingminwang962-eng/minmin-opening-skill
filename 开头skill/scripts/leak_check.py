#!/usr/bin/env python3
"""开头 Skill 串词与句壳污染静态检测器。

用途：交付前或测试验收时，检查生成的候选开头里有没有混进参考文件（references/、SKILL.md）的异域词句或历史残留句壳。
用法：
  python3 leak_check.py --draft 原稿.md --output 候选.md [--media A|B|C|D] [-n 5]
  --output 可传 - 从标准输入读取。
退出码：0 = CLEAN 未发现串词；1 = FLAG 发现可疑片段；2 = 参数或文件错误。
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
HAN = re.compile(r'[\u4e00-\u9fff]+')

# 不参与比对的参考文件：设计依据日常不读；背书档案为创作者长期资料说明
SKIP_REFS = {'设计依据.md', '创作者背书档案.md'}

# 历史上真实漏进成品的句子外壳与校准卡禁抄词、以及永久封杀的主持人报幕尾巴
KNOWN_SHELLS = [
    '基于资源的匮乏', '基于我们的资源', '我想再推荐一个词', '我的建议是先别急', '先别急', '道理很简单',
    '两分钟就可以讲清楚', '用这张表', '这真不是你', '靠的真不是', '在保有一份', '全职主业的同时',
    '今天把这套不', '拆成零售件', '完整交给你', '一次拆透', '生态位的不同',
    '盒装果盘', '淡盐冰水', '动储机芯', '留两圈余量', '指针轻快起跳', '上弦硬拧到底',
    '手工皮具', '镜面收口', '五道封边', '平价随身物', '边缘收口', '镜面封边', '美缝胶', '朝北小阳台', '铸铁锅',
    '往下逐个拆', '一招一招拆给你', '从头说起',
]

# 普通口语、公理通用表达与交付 Markdown 模板栏位名（自然共现，不算串词）
ALLOW = {
    '很多人以为', '很多人都', '的从来不是', '如果你也想', '如果你不想', '如果你不能', '很多人都没意识到',
    '你有没有发现', '你是否发现', '不知道你有没有', '其实很多人', '大多数人', '我们每个人',
    '赚不到钱的', '居高临下的', '自己的真实', '而是能不能', '正在做的事', '的往往不是', '人与人之间', '真的不要再去', '其实根本不',
    '超大开口破圈版', '饱满破圈版', '正面硬牌直击版', '结果心锚版', '侧面叙事', '侧面特稿', '侧面破防', '特稿扮演版',
    '反常识破防版', '极简白话快进版', '极简两层截断版', '极简短刀', '两拍破圈版',
    '接回正文', '推荐理由', '零桥直进', '反常识幻觉分割', '主旨直给', '人群升维', '结果与背书', '借势引入', '场景共鸣', '事件与反差', '实况演示',
    '不是追求', '而是追求', '科学依据', '实操方法', '按情况对号', '对号选就行', '说透这件事', '那具体怎么做到', '具体怎么做到', '靠这套打法',
}

PRIV_BANNED_WORDS = ['刷到的朋友', '先别划走', '先点关注']


def han(text):
    return ''.join(HAN.findall(text))


def load_refs():
    texts = []
    for p in sorted(glob.glob(os.path.join(SKILL_DIR, 'references', '*.md'))):
        if os.path.basename(p) in SKIP_REFS:
            continue
        with open(p, encoding='utf-8') as f:
            texts.append(f.read())
    with open(os.path.join(SKILL_DIR, 'SKILL.md'), encoding='utf-8') as f:
        texts.append(f.read())
    return '\n'.join(texts)


def read(path):
    if path == '-':
        return sys.stdin.read()
    with open(path, encoding='utf-8') as f:
        return f.read()


def ngram_leaks(draft_h, output, refs_h, n):
    ref_grams = set(refs_h[i:i + n] for i in range(len(refs_h) - n + 1))
    hits = []
    for run in HAN.findall(output):
        i = 0
        while i <= len(run) - n:
            g = run[i:i + n]
            if g in ref_grams and g not in draft_h:
                j = i + n
                while j < len(run) and run[i:j + 1] in refs_h and run[i:j + 1] not in draft_h:
                    j += 1
                seg = run[i:j]
                if not any(seg in a or a in seg for a in ALLOW):
                    hits.append(seg)
                i = j
            else:
                i += 1
    return hits


def strip_headers(text):
    """只提取 `### 候选 1` 之后各候选的实际口播正文检测，剥离顶部原开头诊断说明、候选标题行、接回正文与推荐理由元说明行。"""
    lines = text.splitlines()
    # 跳过第一个 ### 候选 之前的原开头诊断元说明段
    start_idx = 0
    for idx, ln in enumerate(lines):
        if ln.lstrip().startswith('### '):
            start_idx = idx
            break
    out = []
    seen_cand4 = False
    for ln in lines[start_idx:]:
        s = ln.lstrip()
        if s.startswith('### 候选 4') or s.startswith('### 候选4'):
            seen_cand4 = True
        if seen_cand4 and s.startswith('---'):
            break
        if s.startswith('### ') or s.startswith('- **接回正文') or s.startswith('- **推荐理由') or s.startswith('（顺手从稿里'):
            continue
        out.append(ln)
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description='开头 Skill 口播正文串词与报幕句壳检测')
    ap.add_argument('--draft', required=True, help='原稿文本文件')
    ap.add_argument('--output', required=True, help='候选开头文本文件，- 表示标准输入')
    ap.add_argument('--media', choices=list('ABCD'), default=None, help='口播态：A 短口播 B 中长深度口播 C(或兼容D) 私域1v1交底')
    ap.add_argument('-n', type=int, default=5, help='连续汉字阈值，默认 5')
    a = ap.parse_args()
    try:
        draft, output = read(a.draft), read(a.output)
        refs_h = han(load_refs())
    except OSError as e:
        print(f'ERROR {e}')
        sys.exit(2)
    draft_h = han(draft)
    body_out = strip_headers(output)

    found = []
    for seg in dict.fromkeys(ngram_leaks(draft_h, body_out, refs_h, a.n)):
        found.append(('参考文件片段', seg))
    for s in KNOWN_SHELLS:
        if han(s) in han(body_out) and han(s) not in draft_h:
            found.append(('历史外壳或报幕禁词', s))
    if a.media in ('C', 'D'):
        for w in PRIV_BANNED_WORDS:
            if w in body_out and w not in draft:
                found.append(('私域串入公域算法词', w))

    seen, uniq = set(), []
    for kind, seg in found:
        if seg not in seen:
            seen.add(seg)
            uniq.append((kind, seg))
    if not uniq:
        print('CLEAN 未发现串词')
        sys.exit(0)
    print(f'FLAG 发现 {len(uniq)} 处可疑片段（逐条核实：属参考件词句或句壳则重写，普通口语则忽略）')
    for kind, seg in uniq:
        idx = output.find(seg)
        ctx = output[max(0, idx - 15): idx + len(seg) + 15].replace('\n', ' ') if idx >= 0 else ''
        print(f'  [{kind}] {seg}  …{ctx}…')
    sys.exit(1)


if __name__ == '__main__':
    main()
