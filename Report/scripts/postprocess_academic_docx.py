#!/usr/bin/env python3
import os
import re
import shutil
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape


FOOTER_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
FOOTER_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"


def read_zip_member(zip_file, name):
    return zip_file.read(name).decode("utf-8")


def next_relationship_id(rels_xml):
    used = {int(x) for x in re.findall(r'Id="rId(\d+)"', rels_xml)}
    candidate = 1
    while candidate in used:
        candidate += 1
    return f"rId{candidate}"


def add_footer_relationship(rels_xml, rel_id):
    if 'Target="footer1.xml"' in rels_xml:
        existing = re.search(r'<Relationship[^>]+Target="footer1\.xml"[^>]*/>', rels_xml)
        if existing:
            match = re.search(r'Id="([^"]+)"', existing.group(0))
            if match:
                return rels_xml, match.group(1)

    relationship = (
        f'<Relationship Id="{rel_id}" Type="{FOOTER_REL_TYPE}" '
        'Target="footer1.xml"/>'
    )
    rels_xml = rels_xml.replace("</Relationships>", relationship + "</Relationships>")
    return rels_xml, rel_id


def add_footer_content_type(content_types_xml):
    if 'PartName="/word/footer1.xml"' in content_types_xml:
        return content_types_xml

    override = (
        f'<Override PartName="/word/footer1.xml" '
        f'ContentType="{FOOTER_CONTENT_TYPE}"/>'
    )
    return content_types_xml.replace("</Types>", override + "</Types>")


def footer_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p>
    <w:pPr>
      <w:pStyle w:val="Footer"/>
      <w:jc w:val="center"/>
    </w:pPr>
    <w:r>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimSun"/>
        <w:sz w:val="20"/>
      </w:rPr>
      <w:fldChar w:fldCharType="begin"/>
    </w:r>
    <w:r>
      <w:instrText xml:space="preserve"> PAGE </w:instrText>
    </w:r>
    <w:r>
      <w:fldChar w:fldCharType="separate"/>
    </w:r>
    <w:r>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimSun"/>
        <w:sz w:val="20"/>
      </w:rPr>
      <w:t>1</w:t>
    </w:r>
    <w:r>
      <w:fldChar w:fldCharType="end"/>
    </w:r>
  </w:p>
</w:ftr>
"""


def academic_app_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties
  xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Template>Normal.dotm</Template>
  <Application>Microsoft Word</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <SharedDoc>false</SharedDoc>
  <LinksUpToDate>false</LinksUpToDate>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""


def update_settings_xml(settings_xml):
    if "<w:updateFields" in settings_xml:
        return re.sub(r'<w:updateFields\b[^>]*/>', '<w:updateFields w:val="true"/>', settings_xml)
    return re.sub(
        r"(<w:settings\b[^>]*>)",
        r'\1<w:updateFields w:val="true"/>',
        settings_xml,
        count=1,
    )


def update_section_properties(document_xml, footer_rel_id):
    sect_match = re.search(r"<w:sectPr\b[^>]*>.*?</w:sectPr>", document_xml)
    if not sect_match:
        sect_pr = (
            '<w:sectPr>'
            f'<w:footerReference w:type="default" r:id="{escape(footer_rel_id)}"/>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" '
            'w:left="1701" w:header="720" w:footer="720" w:gutter="0"/>'
            '</w:sectPr>'
        )
        return document_xml.replace("</w:body>", sect_pr + "</w:body>")

    sect_pr = sect_match.group(0)
    sect_pr = re.sub(r"<w:footerReference\b[^>]*/>", "", sect_pr)
    sect_pr = re.sub(r"<w:pgSz\b[^>]*/>", "", sect_pr)
    sect_pr = re.sub(r"<w:pgMar\b[^>]*/>", "", sect_pr)
    sect_pr = re.sub(r"<w:titlePg\b[^>]*/>", "", sect_pr)

    replacement = (
        '<w:sectPr>'
        f'<w:footerReference w:type="default" r:id="{escape(footer_rel_id)}"/>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" '
        'w:left="1701" w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:titlePg/>'
    )

    sect_pr = re.sub(r"<w:sectPr\b[^>]*>", replacement, sect_pr, count=1)
    document_xml = document_xml[: sect_match.start()] + sect_pr + document_xml[sect_match.end() :]
    return document_xml


def postprocess(docx_path):
    if not os.path.exists(docx_path):
        raise FileNotFoundError(docx_path)

    original_mode = os.stat(docx_path).st_mode & 0o777
    temp_fd, temp_path = tempfile.mkstemp(suffix=".docx")
    os.close(temp_fd)

    try:
        with zipfile.ZipFile(docx_path, "r") as zin:
            content_types = read_zip_member(zin, "[Content_Types].xml")
            rels = read_zip_member(zin, "word/_rels/document.xml.rels")
            document = read_zip_member(zin, "word/document.xml")
            settings = read_zip_member(zin, "word/settings.xml")

            rels, footer_rel_id = add_footer_relationship(rels, next_relationship_id(rels))
            content_types = add_footer_content_type(content_types)
            document = update_section_properties(document, footer_rel_id)

            replacements = {
                "[Content_Types].xml": content_types.encode("utf-8"),
                "word/_rels/document.xml.rels": rels.encode("utf-8"),
                "word/document.xml": document.encode("utf-8"),
                "word/settings.xml": update_settings_xml(settings).encode("utf-8"),
                "word/footer1.xml": footer_xml().encode("utf-8"),
                "docProps/app.xml": academic_app_xml().encode("utf-8"),
            }

            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                written = set()
                for item in zin.infolist():
                    if item.filename in replacements:
                        zout.writestr(item.filename, replacements[item.filename])
                        written.add(item.filename)
                    else:
                        zout.writestr(item, zin.read(item.filename))

                for name, data in replacements.items():
                    if name not in written:
                        zout.writestr(name, data)

        shutil.move(temp_path, docx_path)
        os.chmod(docx_path, original_mode)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def main():
    if len(sys.argv) != 2:
        print("Usage: postprocess_academic_docx.py <file.docx>", file=sys.stderr)
        return 2
    postprocess(sys.argv[1])
    print(f"Postprocessed {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
