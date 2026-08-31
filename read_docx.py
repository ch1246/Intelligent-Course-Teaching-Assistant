# -*- coding: utf-8 -*-
from docx import Document

doc = Document(r'D:\学习文件\毕业设计\论文\供参考：【范文（附格式标注）】邓园园_基于OpenCV的车牌自动识别系统的研究.docx')

for i, para in enumerate(doc.paragraphs):
    if para.text.strip():
        style = para.style.name
        text = para.text[:100]
        print(f'{i}: [{style}] {text}')
