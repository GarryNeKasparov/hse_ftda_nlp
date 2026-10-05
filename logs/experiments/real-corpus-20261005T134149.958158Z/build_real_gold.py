import html,json,re,hashlib,shutil
from datetime import datetime,timezone
from pathlib import Path
root=Path.cwd();sources=root/'data/sources';sources.mkdir(parents=True,exist_ok=True)
log=root/'logs/experiments'/('real-corpus-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));log.mkdir(parents=True)
documents={
 '14913':('https://www.vsrf.ru/files/14913/','Постановление Пленума Верховного Суда РФ №25 от 23.06.2015','2015-06-23'),
 '13345':('https://www.vsrf.ru/files/13345/','Постановление Пленумов ВС РФ и ВАС РФ №10/22 от 29.04.2010','2010-04-29'),
 '12452':('https://www.vsrf.ru/files/12452/','Постановление Пленума ВС РФ №63 от 28.12.2006: новая редакция постановления №2 от 17.03.2004','2006-12-28'),
}
# Manually chosen citation surfaces and target values, never model predictions.
annotations={
 '14913':{
  2:[('статья 3 ГК РФ',5,'3',None,None),('статье 1 ГК РФ',5,'1',None,None)],
  3:[('пункту 3 статьи 1 ГК РФ',5,'1','3',None),('пункта 4 статьи 1 ГК РФ',5,'1','4',None)],
  4:[('пункта 5 статьи 10 ГК РФ',5,'10','5',None)],
  5:[('статья 56 Гражданского процессуального кодекса Российской Федерации',6,'56',None,None),('статья 65 Арбитражного процессуального кодекса Российской Федерации',0,'65',None,None)],
  6:[('пункт 2 статьи 10 ГК РФ',5,'10','2',None),('пункт 3 статьи 157 ГК РФ',5,'157','3',None),('пункт 5 статьи 166 ГК РФ',5,'166','5',None)],
  8:[('статья 56 ГПК РФ',6,'56',None,None),('статья 65 АПК РФ',0,'65',None,None)],
  9:[('пункту 2 статьи 5 ГК РФ',5,'5','2',None)],
 },
 '13345':{
  3:[('статьей 212 Гражданского кодекса Российской Федерации',5,'212',None,None)],
  4:[('статьи 55 Конституции Российской Федерации',None,'55',None,None),('пункта 2 статьи 1 ГК РФ',5,'1','2',None)],
  6:[('части 1 статьи 30 ГПК РФ',6,'30','1',None),('части 1 статьи 38 АПК РФ',0,'38','1',None)],
  7:[],
  9:[('статьей 148 ГПК РФ',6,'148',None,None),('статьей 133 АПК РФ',0,'133',None,None)],
  12:[('пунктами 1, 2 статьи 299 ГК РФ',5,'299',['1','2'],None)],
  15:[('пункта 4 статьи 216 ГК РФ',5,'216','4',None),('статьей 305 ГК РФ',5,'305',None,None)],
  16:[],
 },
 '12452':{
  19:[('статья 15 ТК РФ',10,'15',None,None)],
  33:[],
  36:[('части 3 статьи 152 ГПК РФ',6,'152','3',None)],
  37:[('статьей 11 ТК РФ',10,'11',None,None)],
 }
}
review_annotations={
 '14913':{10:'Published article 8-1: determine whether output preserves the hyphen or restores superscript/dotted typography; do not interpret it as an article range.'},
 '13345':{10:'пункт 3 части 4 статьи 170 requires simultaneous point and part, which LawLink cannot preserve; adjudicate mapping for the whole passage.',13:'абзац пятый introduces a paragraph level absent from LawLink; adjudicate projection before gold.'},
 '12452':{18:'пункт 1 части 1 статьи 22 contains point and part together; adjudicate output mapping.',22:'часть первая requires an explicit decision on ordinal serialization.',28:'Article 33336 loses superscript typography in plain HTML text; also части второй modifies the code volume, not an article part. Adjudicate both.',40:'частей 1 и 4 статьи 15, статьи 120 Конституции РФ has a shared law tail; adjudicate branch boundaries and law attachment.'}
}
manifest=[];gold=[];review=[]
for key,(url,title,date) in documents.items():
 raw=Path('/tmp/legal-source-'+key+'.html');raw_bytes=raw.read_bytes();content=raw_bytes.decode('utf-8')
 m=re.search(r'<pre[^>]*>(.*?)</pre>',content,re.S|re.I);assert m
 decoded=html.unescape(re.sub('<[^>]*>','',m.group(1)))
 normalized=re.sub(r'\s+',' ',decoded).strip()
 dest=sources/('vsrf-'+key+'.txt');dest.write_text(normalized+'\n')
 rawdest=log/('vsrf-'+key+'.html');shutil.copy2(raw,rawdest)
 manifest.append(dict(id='vsrf-'+key,url=url,title=title,document_date=date,retrieved_at_utc=datetime.now(timezone.utc).isoformat(),source_kind='official_judicial_document',normalized_snapshot=str(dest.relative_to(root)),normalized_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),raw_snapshot=str(rawdest.relative_to(root)),raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),transformation='Decode UTF-8, extract PRE text, remove HTML tags, decode entities, collapse whitespace. No spelling or provision-number corrections. Superscript layout is not reconstructed.'))
 parts=re.split(r'\n(?= {5}\S)',decoded)
 for index,refs in annotations[key].items():
  text=re.sub(r'\s+',' ',parts[index]).strip();offset=normalized.index(text)
  row=dict(id=f'web-vsrf-{key}-paragraph-{index:03}',status='gold',test_type='extraction',origin='web',source=url,source_id='vsrf-'+key,source_span={'start':offset,'end':offset+len(text),'coordinate_system':'normalized_source_snapshot'},text=text,references=[],annotation_status='agent_reviewed',document_group='vsrf-'+key)
  previous=0
  for surface,law,article,point,sub in refs:
   start=text.index(surface,previous);end=start+len(surface);previous=end
   points=point if isinstance(point,list) else [point]
   links=[dict(law_id=law,article=article,point_article=p,subpoint_article=sub) for p in points]
   row['references'].append(dict(start=start,end=end,text=surface,links=links,law_evidence='Unique whole code alias in law_aliases.json.' if law is not None else 'The standalone Constitution name is absent from law_aliases.json; no inference from embedded titles of other acts.'))
  gold.append(row)
 for index,question in review_annotations[key].items():
  text=re.sub(r'\s+',' ',parts[index]).strip();offset=normalized.index(text)
  review.append(dict(id=f'web-vsrf-{key}-paragraph-{index:03}',status='needs_review',test_type='extraction',origin='web',source=url,source_id='vsrf-'+key,source_span={'start':offset,'end':offset+len(text),'coordinate_system':'normalized_source_snapshot'},text=text,expected_links=None,question=question,document_group='vsrf-'+key))
interpretation=[]
for row in gold:
 for n,ref in enumerate(row['references'],1):
  interpretation.append(dict(id=row['id']+f'-reference-{n}',status='gold',test_type='interpretation',origin='web',source=row['source'],source_id=row['source_id'],parent_id=row['id'],parent_reference_span={'start':ref['start'],'end':ref['end']},document_group=row['document_group'],text=ref['text'],references=[dict(ref,start=0,end=len(ref['text']))],annotation_status='agent_reviewed'))
for name,items in [('golden_real_extraction',gold),('golden_real_interpretation',interpretation),('real_review_queue',review)]:
 p=root/'data'/(name+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items));shutil.copy2(p,log/p.name)
(sources/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');shutil.copy2(sources/'manifest.json',log/'manifest.json')
summary=dict(extraction_samples=len(gold),negative_passages=sum(not r['references'] for r in gold),references=sum(len(r['references']) for r in gold),links=sum(len(ref['links']) for r in gold for ref in r['references']),interpretation_samples=len(interpretation),review_passages=len(review),sources=len(manifest),log=str(log.relative_to(root)))
(log/'collection-summary.json').write_text(json.dumps(summary,indent=2)+'\n');shutil.copy2('/tmp/build_real_gold.py',log/'build_real_gold.py')
print(json.dumps(summary,indent=2))
