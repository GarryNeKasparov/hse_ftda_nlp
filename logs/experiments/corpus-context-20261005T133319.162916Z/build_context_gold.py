import json,re,hashlib
from pathlib import Path
root=Path.cwd()
readme=(root/'README.md').read_text()
body=readme.split('test_text = """',1)[1].split('"""',1)[0].strip('\n')
texts=body.splitlines()
# Exact source lines: retain the multiline first paragraph as one sample.
paragraphs=[texts[0]+'\n'+texts[1]]+[t for t in texts[2:] if t.strip()]
# Manually specified references in each complete passage, independent of parser output.
annotations=[
 [('пп. 1 п. 1 ст. 374 НК РФ',15,'374','1','1'),('ст. 105 УК РФ',13,'105',None,None),('п.  10 АПК',0,None,'10',None)],
 [('статье 17 Конституции Российской Федерации',None,'17',None,None),('п. 5 ст. 105 УК РФ',13,'105','5',None),('п. 3 ст. 158 УК РФ',13,'158','3',None),('ст. 30 Гражданского кодекса Российской Федерации',5,'30',None,None)],
 [('пп. 12 п. 4 ст. 159 УК РФ',13,'159','4','12'),('п. 2 ст. 228 УК РФ',13,'228','2',None),('ст. 275 Налогового Кодекса Российской Федерации',15,'275',None,None)],
 [('ст. 90 Семейного кодекса Российской Федерации',8,'90',None,None),('ст. 70 Трудового кодекса Российской Федерации',10,'70',None,None),('п. 1 ст. 213 Гражданского процессуального кодекса Российской Федерации',6,'213','1',None)],
 [('пункта а ст. 20 АПК',0,'20','а',None),('статье 16 Закона "О защите прав потребителей"',984,'16',None,None),('п. 2 ст. 14 Закона "О персональных данных"',330,'14','2',None)],
 [('ст. 19 Федерального закона "О бухгалтерском учёте"',224,'19',None,None),('п. р ст. 9 Федерального закона "О государственной регистрации юридических лиц и индивидуальных предпринимателей"',412,'9','р',None),('п. 1 ст. 16 Закона "О защите прав юридических лиц и индивидуальных предпринимателей при осуществлении государственного контроля (надзора) и муниципального контроля"',284,'16','1',None)],
 [('подпункту 2 пунта б статьи 22 Федерального закона "О государственной гражданской службе Российской Федерации"',362,'22','б','2'),('ст. 12 Федерального закона "О защите конкуренции"',332,'12',None,None),('п. 3 статьи 20 Федерального закона "О полиции"',249,'20','3',None)],
 [('ст. 37 ФЗ №20-456',None,'37',None,None),('пп. 4, 5, 6 и 8 п. 1 ст. 14 Федерального закона "О государственной регистрации недвижимости"',174,'14','1',['4','5','6','8']),('ст. 6 Федерального закона "О банках и банковской деятельности"',None,'6',None,None)],
 [('пункте 1 статьи 34 Гражданского Кодекса',5,'34','1',None)],
 [('пп. 1 п. 2 ст. 34 рандомного кодекса',None,'34','2','1')],
 None,
 [('часть 3, ст. 30.1 КоАП РФ',17,'30.1','3',None),('ст. 211 АПК РФ',0,'211',None,None)],
]
assert len(paragraphs)==len(annotations),(len(paragraphs),len(annotations))
def link(law,article,point,sub):
 return dict(law_id=law,article=article,point_article=point,subpoint_article=sub)
rows=[]
for i,(text,refs) in enumerate(zip(paragraphs,annotations),1):
 if refs is None: continue
 offset=readme.index(text)
 row=dict(id=f'readme-passage-{i:02}',status='gold',test_type='extraction',source='README.md: verbatim complete passage from test_text',source_span={'start':offset,'end':offset+len(text),'sha256':hashlib.sha256(readme.encode()).hexdigest()},text=text,references=[])
 previous=0
 for surface,law,article,point,sub in refs:
  start=text.index(surface,previous);end=start+len(surface);previous=end
  subs=sub if isinstance(sub,list) else [sub]
  row['references'].append(dict(start=start,end=end,text=surface,links=[link(law,article,point,s) for s in subs]))
 rows.append(row)
# A verbatim complete negative sentence from the passage, explicitly an excerpt.
text='банки обязаны соблюдать банковскую тайну.';offset=readme.index(text)
rows.append(dict(id='readme-negative-sentence',status='gold',test_type='extraction',source='README.md: verbatim complete sentence clause used as a negative excerpt',source_span={'start':offset,'end':offset+len(text),'sha256':hashlib.sha256(readme.encode()).hexdigest()},text=text,references=[]))
identity=[]
for row in rows:
 for n,ref in enumerate(row['references'],1):
  identity.append(dict(id=f"{row['id']}-reference-{n}",status='gold',test_type='interpretation',source=row['source']+'; reference isolated for interpretation',parent_id=row['id'],text=ref['text'],references=[dict(ref,start=0,end=len(ref['text']))]))
# Include discussion's missing-law policy and README's explicit three-subpoint example.
legacy=[json.loads(s) for s in (root/'data/golden_references.jsonl').read_text().splitlines()]
for row in legacy:
 if row['id'] in {'article-unspecified-law','subpoint-list'}:
  ref=row['references'][0]
  identity.append(dict(id=row['id'],status='gold',test_type='interpretation',source=row['source'],text=ref['text'],references=[dict(ref,start=0,end=len(ref['text']))]))
for filename,items in [('golden_extraction.jsonl',rows),('golden_interpretation.jsonl',identity)]:
 (root/'data'/filename).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items))
 print(filename,len(items),'passages;',sum(len(r['references']) for r in items),'references;',sum(len(s['links']) for r in items for s in r['references']),'links')
