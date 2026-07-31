import zipfile
import xml.etree.ElementTree as ET
import sys
import io

def get_docx_text(path):
    try:
        with zipfile.ZipFile(path) as docx:
            tree = ET.XML(docx.read('word/document.xml'))
        
        # Namespaces
        WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        PARA = WORD_NAMESPACE + 'p'
        TEXT = WORD_NAMESPACE + 't'
        
        paragraphs = []
        for paragraph in tree.iter(PARA):
            texts = [node.text
                     for node in paragraph.iter(TEXT)
                     if node.text]
            if texts:
                paragraphs.append(''.join(texts))
                
        return '\n\n'.join(paragraphs)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    with open('d:/Downloads/AskBase/project_docs.txt', 'w', encoding='utf-8') as f:
        f.write(get_docx_text(sys.argv[1]))
    print("Done")
