"""Local rendering only. Text, tables and lists; no URL, image or external asset retrieval."""
import io,re
from html import escape
from html.parser import HTMLParser
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import KeepTogether, HRFlowable
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.pagesizes import A4
from docx import Document
from .templates_service import render_markdown

class Blocks(HTMLParser):
    def __init__(self):super().__init__();self.blocks=[];self.text='';self.tag='p';self.rows=None;self.row=None;self.cell=None
    def flush(self):
        if self.text.strip():self.blocks.append((self.tag,self.text.strip()))
        self.text=''
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.flush();self.rows=[]
        elif tag=='tr' and self.rows is not None:self.row=[]
        elif tag in ('td','th') and self.rows is not None:self.cell=''
        elif self.rows is None and tag in ('p','h1','h2','h3','h4','li','blockquote','pre'):self.flush();self.tag=tag
        elif tag=='br':self.handle_data('\n')
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.row.append(self.cell.strip());self.cell=None
        elif tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
        elif tag=='table':self.blocks.append(('table',self.rows));self.rows=None
        elif self.rows is None and tag in ('p','h1','h2','h3','h4','li','blockquote','pre'):self.flush();self.tag='p'
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
        elif self.rows is None:self.text+=data

def blocks(markdown):
    parser=Blocks();parser.feed(render_markdown(markdown));parser.flush();return parser.blocks

def export(title,markdown,format='pdf',subtitle='',metadata=None,organization_id=None):
    from .models import PortalConfiguration
    brand=PortalConfiguration.objects.filter(organization_id=organization_id).first() if organization_id else None
    brand_name=brand.title if brand else 'Beschlussmanufaktur'
    brand_color=brand.color if brand and re.fullmatch(r'#[0-9a-fA-F]{6}',brand.color) else '#245846'
    parts=blocks(markdown)
    if format=='docx':
        doc=Document()
        from docx.shared import RGBColor
        doc.sections[0].header.paragraphs[0].text=brand_name
        doc.sections[0].footer.paragraphs[0].text=brand_name
        for name in ('Title','Heading 1','Heading 2','Heading 3','Heading 4'):doc.styles[name].font.color.rgb=RGBColor.from_string(brand_color[1:])
        doc.add_heading(title,0)
        if subtitle:doc.add_paragraph(subtitle)
        for tag,text in parts:
            if tag=='table':
                if not text:continue
                table=doc.add_table(rows=len(text),cols=max(len(row) for row in text));table.style='Table Grid'
                for i,row in enumerate(text):
                    for j,cell in enumerate(row):table.cell(i,j).text=cell
            elif tag.startswith('h'):doc.add_heading(text,min(int(tag[1]),4))
            else:doc.add_paragraph(text,style='List Bullet' if tag=='li' else None)
        if metadata:
            doc.add_heading('Anlagen / Stand',1)
            for line in metadata:doc.add_paragraph(line)
        buffer=io.BytesIO();doc.save(buffer);return buffer.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if format!='pdf':raise ValueError('Unbekanntes Exportformat')
    # Deliberately use local ReportLab assets: no untrusted HTML, URL or font loading.
    ink=HexColor('#172A35')
    muted=HexColor('#536673')
    accent=HexColor(brand_color)
    pale=HexColor('#F1F5F7')
    rule=HexColor('#DCE5E9')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BMTitle',parent=styles['Title'],fontName='Helvetica-Bold',
        fontSize=21,leading=26,textColor=ink,spaceAfter=11,alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='BMSubtitle',parent=styles['Normal'],fontSize=10.5,
        leading=16,textColor=muted,spaceAfter=9))
    styles.add(ParagraphStyle(name='BMBody',parent=styles['Normal'],fontSize=10,
        leading=15.5,textColor=ink,spaceAfter=8,allowWidows=0,allowOrphans=0))
    styles.add(ParagraphStyle(name='BMH1',parent=styles['BMBody'],fontName='Helvetica-Bold',
        fontSize=15,leading=19,textColor=ink,spaceBefore=18,spaceAfter=9,keepWithNext=True))
    styles.add(ParagraphStyle(name='BMH2',parent=styles['BMBody'],fontName='Helvetica-Bold',
        fontSize=12.5,leading=17,textColor=ink,spaceBefore=14,spaceAfter=7,keepWithNext=True))
    styles.add(ParagraphStyle(name='BMH3',parent=styles['BMBody'],fontName='Helvetica-Bold',
        fontSize=11,leading=15,textColor=accent,spaceBefore=10,spaceAfter=5,keepWithNext=True))
    styles.add(ParagraphStyle(name='BMTableHead',parent=styles['BMBody'],fontName='Helvetica-Bold',
        fontSize=9,leading=13,spaceAfter=0))
    styles.add(ParagraphStyle(name='BMTableCell',parent=styles['BMBody'],
        fontSize=9,leading=13,spaceAfter=0))
    styles.add(ParagraphStyle(name='BMLabel',parent=styles['BMBody'],fontName='Helvetica-Bold',
        fontSize=8.5,leading=12,textColor=accent,spaceAfter=6))
    elements=[
        Paragraph(escape(brand_name),styles['BMLabel']),
        HRFlowable(width='100%',thickness=2,color=accent,spaceAfter=18),
        Paragraph(escape(title),styles['BMTitle']),
    ]
    if subtitle:elements.append(Paragraph(escape(subtitle),styles['BMSubtitle']))
    elements.append(Spacer(1,13))
    usable=A4[0]-100
    for tag,text in parts:
        if tag=='table':
            if not text:continue
            cols=max(len(row) for row in text)
            # Avoid unusably narrow cells for unusually wide source tables.
            if cols>8:
                for row in text:
                    elements.append(Paragraph(escape(' | '.join(row)),styles['BMBody']))
                continue
            rows=[]
            for index,row in enumerate(text):
                style=styles['BMTableHead'] if index==0 else styles['BMTableCell']
                rows.append([Paragraph(escape(cell),style) for cell in row]+['']*(cols-len(row)))
            table=Table(rows,colWidths=[usable/cols]*cols,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),pale),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,HexColor('#F8FAFB')]),
                ('LINEBELOW',(0,0),(-1,0),1,accent),
                ('LINEBELOW',(0,1),(-1,-2),.3,rule),
                ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
                ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
            ]))
            elements.extend([table,Spacer(1,12)])
        else:
            style=styles['BMH'+str(min(int(tag[1]),3))] if tag.startswith('h') else styles['BMBody']
            if tag=='li':
                content='&#8226;  '+escape(text)
            else:
                content=escape(text)
            content=content.replace('\n','<br/>')
            elements.append(Paragraph(content,style))
    if metadata:
        elements.extend([Spacer(1,16),HRFlowable(width='100%',thickness=.6,color=rule,spaceAfter=12),
            Paragraph('Anlagen / Stand',styles['BMH2'])])
        for line in metadata:elements.append(Paragraph(escape(line),styles['BMBody']))
    buffer=io.BytesIO()
    def furniture(canvas,doc):
        canvas.saveState()
        width,height=A4
        # A reserved top band and bottom footer never overlap the Platypus frame.
        canvas.setStrokeColor(rule)
        canvas.setLineWidth(.6)
        canvas.line(50,48,width-50,48)
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(muted)
        # Long tenant names are clipped to the available footer width.
        footer_name=brand_name
        while len(footer_name)>1 and canvas.stringWidth(footer_name,'Helvetica',8)>usable-90:
            footer_name=footer_name[:-1]
        if footer_name!=brand_name:footer_name=footer_name.rstrip()+'…'
        canvas.drawString(50,34,footer_name)
        canvas.drawRightString(width-50,34,f'Seite {doc.page}')
        canvas.restoreState()
    SimpleDocTemplate(buffer,pagesize=A4,leftMargin=50,rightMargin=50,
        topMargin=54,bottomMargin=66,title=title,author=brand_name,
        pageCompression=1).build(elements,onFirstPage=furniture,onLaterPages=furniture)
    return buffer.getvalue(),'application/pdf'
