import os
import argparse
from PIL import Image
from lxml import etree
from zipfile import ZipFile, ZIP_STORED

def create_epub(image_folder, output_file):
    # 提取书名
    book_title = os.path.splitext(os.path.basename(output_file))[0]

    # 创建必要的文件夹
    os.makedirs('META-INF', exist_ok=True)
    os.makedirs('OEBPS/images', exist_ok=True)
    os.makedirs('OEBPS/text', exist_ok=True)

    # 生成 mimetype 文件
    with open('mimetype', 'w') as f:
        f.write('application/epub+zip')

    # 生成 container.xml 文件
    container = etree.Element('container', attrib={
        'version': '1.0',
        'xmlns': 'urn:oasis:names:tc:opendocument:xmlns:container'
    })
    rootfiles = etree.SubElement(container, 'rootfiles')
    rootfile = etree.SubElement(rootfiles, 'rootfile', attrib={
        'full-path': 'OEBPS/content.opf',
        'media-type': 'application/oebps-package+xml'
    })
    with open('META-INF/container.xml', 'wb') as f:
        f.write(etree.tostring(container, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    # 生成 content.opf 文件
    opf = etree.Element('package', attrib={
        'version': '3.0',
        'xmlns': 'http://www.idpf.org/2007/opf',
        'unique-identifier': 'bookid'
    })
    metadata = etree.SubElement(opf, 'metadata', nsmap={
        'dc': 'http://purl.org/dc/elements/1.1/',
        'opf': 'http://www.idpf.org/2007/opf'
    })
    dc_identifier = etree.SubElement(metadata, '{http://purl.org/dc/elements/1.1/}identifier', attrib={'id': 'bookid'})
    dc_identifier.text = 'urn:uuid:1234567890'
    dc_title = etree.SubElement(metadata, '{http://purl.org/dc/elements/1.1/}title')
    dc_title.text = book_title
    dc_language = etree.SubElement(metadata, '{http://purl.org/dc/elements/1.1/}language')
    dc_language.text = 'en'

    manifest = etree.SubElement(opf, 'manifest')
    spine = etree.SubElement(opf, 'spine', attrib={'toc': 'ncx'})

    # 添加 toc.ncx 到 manifest
    item_toc = etree.SubElement(manifest, 'item', attrib={
        'id': 'ncx',
        'href': 'toc.ncx',
        'media-type': 'application/x-dtbncx+xml'
    })

    # 生成 toc.ncx 文件
    ncx = etree.Element('ncx', attrib={
        'xmlns': 'http://www.daisy.org/z3986/2005/ncx/',
        'version': '2005-1'
    })
    ncx_head = etree.SubElement(ncx, 'head')
    ncx_meta = etree.SubElement(ncx_head, 'meta', attrib={'name': 'dtb:uid', 'content': 'urn:uuid:1234567890'})
    ncx_meta = etree.SubElement(ncx_head, 'meta', attrib={'name': 'dtb:depth', 'content': '1'})
    ncx_meta = etree.SubElement(ncx_head, 'meta', attrib={'name': 'dtb:totalPageCount', 'content': '0'})
    ncx_meta = etree.SubElement(ncx_head, 'meta', attrib={'name': 'dtb:maxPageNumber', 'content': '0'})

    ncx_docTitle = etree.SubElement(ncx, 'docTitle')
    ncx_text = etree.SubElement(ncx_docTitle, 'text')
    ncx_text.text = book_title

    ncx_navMap = etree.SubElement(ncx, 'navMap')

    # 添加图片到 EPUB 并生成对应的 XHTML 文件
    for i, image_file in enumerate(sorted(os.listdir(image_folder))):
        if image_file.endswith('.jpg'):
            img_path = os.path.join(image_folder, image_file)
            img_dest = f'OEBPS/images/{image_file}'
            
            # 重新保存图片以确保编码正确
            img = Image.open(img_path)
            img = img.convert('RGB')  # 确保图片是 RGB 格式
            img.save(img_dest, 'JPEG')

            item = etree.SubElement(manifest, 'item', attrib={
                'id': f'img{i}',
                'href': f'images/{image_file}',
                'media-type': 'image/jpeg'
            })

            # 生成对应的 XHTML 文件
            xhtml = etree.Element('html', attrib={'xmlns': 'http://www.w3.org/1999/xhtml'})
            body = etree.SubElement(xhtml, 'body')
            img_tag = etree.SubElement(body, 'img', attrib={'src': f'../images/{image_file}'})
            xhtml_path = f'OEBPS/text/img{i}.xhtml'
            with open(xhtml_path, 'wb') as f:
                f.write(etree.tostring(xhtml, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

            item_page = etree.SubElement(manifest, 'item', attrib={
                'id': f'page{i}',
                'href': f'text/img{i}.xhtml',
                'media-type': 'application/xhtml+xml'
            })
            itemref = etree.SubElement(spine, 'itemref', attrib={'idref': f'page{i}'})

            # 添加到 toc.ncx
            navPoint = etree.SubElement(ncx_navMap, 'navPoint', attrib={'id': f'navPoint-{i+1}', 'playOrder': str(i+1)})
            navLabel = etree.SubElement(navPoint, 'navLabel')
            navLabel_text = etree.SubElement(navLabel, 'text')
            navLabel_text.text = f'Image {i+1}'
            content = etree.SubElement(navPoint, 'content', attrib={'src': f'text/img{i}.xhtml'})

    with open('OEBPS/content.opf', 'wb') as f:
        f.write(etree.tostring(opf, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    with open('OEBPS/toc.ncx', 'wb') as f:
        f.write(etree.tostring(ncx, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    # 创建 EPUB 文件
    with ZipFile(output_file, 'w') as epub:
        epub.write('mimetype', compress_type=ZIP_STORED)
        for folder, _, files in os.walk('META-INF'):
            for file in files:
                epub.write(os.path.join(folder, file), os.path.relpath(os.path.join(folder, file), '.'))
        for folder, _, files in os.walk('OEBPS'):
            for file in files:
                epub.write(os.path.join(folder, file), os.path.relpath(os.path.join(folder, file), '.'))

    # 清理临时文件
    os.remove('mimetype')
    os.remove('META-INF/container.xml')
    for folder, _, files in os.walk('OEBPS'):
        for file in files:
            os.remove(os.path.join(folder, file))
    os.rmdir('META-INF')
    os.rmdir('OEBPS/images')
    os.rmdir('OEBPS/text')
    os.rmdir('OEBPS')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert a folder of JPG images to an EPUB file.')
    parser.add_argument('image_folder', type=str, help='Path to the folder containing JPG images.')
    parser.add_argument('output_file', type=str, help='Path to the output EPUB file.')

    args = parser.parse_args()
    create_epub(args.image_folder, args.output_file)
