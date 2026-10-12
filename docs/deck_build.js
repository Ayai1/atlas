const pptx = require('pptxgenjs');
const pres = new pptx();
pres.layout='LAYOUT_WIDE';
pres.author='Syed Ayaan Ahmed, Noorullah Shaik';
pres.title='Local First AI Operating System Companion';

const INK='16212E',DEEP='1B2A41',WHITE='FFFFFF',SOFT='F1F4F7',LINE='D9E0E6';
const SAFE='1F7A5E',WARN='B4472E',MUTED='63707E',TEXT='1E2933';
const H='Cambria',B='Calibri';
const M=0.62, W=13.3-2*M;
let n=0;
function foot(s,dark){ n++;
  s.addText('Capstone Project-I  ·  Mid-Term Review',
    {x:M,y:6.95,w:8,h:0.3,fontSize:9,color:dark?'7A8899':MUTED,fontFace:B});
  s.addText(String(n),{x:12.3,y:6.95,w:0.4,h:0.3,fontSize:9,color:dark?'7A8899':MUTED,fontFace:B,align:'right'});}
function slide(title,kicker){
  const s=pres.addSlide(); s.background={color:WHITE};
  s.addText(kicker.toUpperCase(),{x:M,y:0.34,w:W,h:0.26,fontSize:11,color:SAFE,bold:true,fontFace:B,charSpacing:1.2});
  s.addText(title,{x:M,y:0.6,w:W,h:0.66,fontSize:32,bold:true,color:DEEP,fontFace:H});
  foot(s,false); return s;}
function card(s,x,y,w,h,fill){
  s.addShape(pres.ShapeType.roundRect,{x,y,w,h,fill:{color:fill||SOFT},line:{color:LINE,width:0.75},rectRadius:0.06});}

/* 1 TITLE */
{
  const s=pres.addSlide(); s.background={color:INK};
  s.addText('WOXSEN UNIVERSITY  ·  SCHOOL OF TECHNOLOGY',
    {x:M,y:0.85,w:W,h:0.3,fontSize:12,color:'8FA3B5',bold:true,fontFace:B,charSpacing:1.4});
  s.addText('Local First AI Operating\nSystem Companion',
    {x:M,y:1.45,w:W,h:1.85,fontSize:48,bold:true,color:WHITE,fontFace:H,lineSpacing:58});
  s.addText('Understand, manage and control your own computer — safely, and reversibly',
    {x:M,y:3.35,w:W,h:0.4,fontSize:16,color:'BFD4C9',fontFace:B});

  card(s,M,4.05,8.1,2.25,'1F2E3F');
  s.addText('Submitted by',{x:M+0.4,y:4.28,w:7.3,h:0.28,fontSize:11,color:'8FA3B5',bold:true,fontFace:B,charSpacing:0.8});
  s.addText([{text:'Syed Ayaan Ahmed   ·   23WU0102205',options:{breakLine:true}},
             {text:'Noorullah Shaik   ·   23WU0102144',options:{}}],
    {x:M+0.4,y:4.6,w:7.3,h:0.85,fontSize:17,color:WHITE,fontFace:B,lineSpacing:26});
  s.addText('Mentor',{x:M+0.4,y:5.58,w:7.3,h:0.26,fontSize:11,color:'8FA3B5',bold:true,fontFace:B,charSpacing:0.8});
  s.addText('Dr. Meher Gayatri Devi Tiwari',
    {x:M+0.4,y:5.85,w:7.3,h:0.34,fontSize:15,color:'BFD4C9',fontFace:B});
  foot(s,true);
  s.addNotes('Good morning. We are Syed Ayaan Ahmed and Noorullah Shaik. This is our mid-term review. Our project is a local-first AI companion that helps people safely change settings on their own computer. We will report progress against our two objectives for this semester.');
}

/* 2 INDEX */
{
  const s=slide('Index','Contents');
  const items=['Problem Statement','Literature Review','Existing Tools and Novelty','Objectives',
               'Methodology','Architecture and Flowchart','Progress and Timeline',
               'Challenges and Future Scope'];
  items.forEach((t,i)=>{
    const col=i%2,row=Math.floor(i/2);
    const x=M+col*(W/2), y=1.85+row*1.05;
    card(s,x,y,W/2-0.35,0.82);
    s.addText(String(i+1).padStart(2,'0'),{x:x+0.3,y:y+0.2,w:0.6,h:0.42,fontSize:19,bold:true,color:SAFE,fontFace:H});
    s.addText(t,{x:x+0.95,y:y+0.2,w:W/2-1.4,h:0.42,fontSize:17,color:TEXT,fontFace:B,valign:'middle'});});
  s.addNotes('Eight sections after this. Ayaan takes slides 3 to 6, Noorullah takes 7 to 10.');
}

/* 3 PROBLEM */
{
  const s=slide('Problem Statement','01  ·  Problem');
  card(s,M,1.45,W,1.05,'E8F2EE');
  s.addText('People cannot safely change settings on computers they own, because nothing explains what a change will do — or guarantees it can be undone.',
    {x:M+0.35,y:1.6,w:W-0.7,h:0.78,fontSize:19,bold:true,color:DEEP,fontFace:H,valign:'middle'});
  const four=[['You must already know the name',
               'Describing the symptom — “my screen keeps going dark” — finds nothing.'],
              ['Nothing explains the effect',
               'Interfaces name a control. They do not say what it changes or what it costs.'],
              ['There is no way back',
               'The old value is not recorded, so a change cannot reliably be reversed.'],
              ['AI assistants act, but do not account',
               'New OS agents perform actions without showing the operation or keeping a record.']];
  const cw=(W-3*0.3)/4;
  four.forEach((c,i)=>{
    const x=M+i*(cw+0.3);
    card(s,x,2.85,cw,2.4);
    s.addText(c[0],{x:x+0.25,y:3.08,w:cw-0.5,h:0.75,fontSize:15,bold:true,color:WARN,fontFace:B});
    s.addText(c[1],{x:x+0.25,y:3.88,w:cw-0.5,h:1.2,fontSize:13,color:TEXT,fontFace:B,lineSpacing:18});});
  s.addText('Who this affects:  people who use their computer heavily, know something is wrong, but have no confidence to change it and nobody to ask.',
    {x:M,y:5.55,w:W,h:0.5,fontSize:14,color:TEXT,italic:true,fontFace:B});
  s.addNotes('Read the green box out loud, then give one concrete example - the screen going dark while reading. Keep this to 90 seconds.');
}

/* 4 LITERATURE REVIEW */
{
  const s=slide('Literature Review','02  ·  Review');
  s.addText('Five papers from 2026, all on the safety of AI agents that act on a real computer.',
    {x:M,y:1.26,w:W,h:0.28,fontSize:12.5,color:MUTED,fontFace:B});
  const rows=[[{text:'Title',options:{bold:true}},{text:'Author / Year',options:{bold:true}},
               {text:'Findings and outcomes',options:{bold:true}},{text:'Limitations',options:{bold:true}}],
   ['OSGuard: A Benchmark for Safety in Computer-Use Agents',
    'Mohammadmirzaei\nand Flanigan, 2026',
    'Tested AI agents on 45 real desktop tasks. They finished the job but did something unsafe 38% of the time. The best safety checker only cut that to 33%.',
    'It measures how often agents go wrong. It offers no way to repair the damage once it is done.'],
   ['SafePred: A Predictive Guardrail for Computer-Using Agents',
    'Chen et al., 2026',
    'Tries to predict which actions will cause trouble later, and blocks them before they run.',
    'The prediction is a guess made by another model. If it guesses wrong, the action happens and cannot be taken back.'],
   ['When Actions Go Off-Task',
    'Ning et al., 2026\n(ICML)',
    'Spots actions that drift away from what the user asked for, and rewrites them before they run.',
    'One model checking another model. It is only needed because the agent writes its own actions in the first place.'],
   ['When Benign Inputs Lead to Severe Harms',
    'Jones et al., 2026\n(ICML)',
    'Shows agents cause harm even from completely ordinary, harmless requests. Gives 117 real examples.',
    'Proves the danger is not just bad users. Still offers nothing to undo the harm it demonstrates.'],
   ['ActPlane: OS-Level Policy Enforcement for Agent Harnesses',
    'Zheng et al., 2026',
    'Puts the safety rules inside the operating system itself, so nothing slips past. Costs under 10% speed.',
    'Can block an action, but cannot reverse one it allowed. The rules must be written by an expert.']];
  s.addTable(rows,{x:M,y:1.6,w:W,colW:[2.95,1.7,3.85,3.56],
    fontSize:10.5,fontFace:B,color:TEXT,valign:'middle',rowH:0.46,
    border:{type:'solid',color:LINE,pt:0.75},fill:{color:WHITE},margin:0.085});
  card(s,M,5.72,W,0.85,'E8F2EE');
  s.addText('Every one of these tries to stop a mistake before it happens. Not one of them can undo a mistake after it happens. That is the gap we fill.',
    {x:M+0.32,y:5.85,w:W-0.64,h:0.6,fontSize:13,bold:true,color:DEEP,fontFace:B,valign:'middle'});
  s.addNotes('All five are 2026 papers. Do not read the table. Say: the whole field spent this year on prediction, detection and blocking. Quote the OSGuard number - agents did something unsafe 38 percent of the time, and the best guardrail only got that to 33. Then read the green line: none of them can undo anything.');
}

/* 5 EXISTING TECHNOLOGIES, GAP AND NOVELTY */
{
  const s=slide('Existing Tools and How We Differ','03  ·  Comparison and Novelty');
  const rows=[[{text:'Product / tool',options:{bold:true}},{text:'What it does',options:{bold:true}},
               {text:'Limitation',options:{bold:true}},{text:'How our approach differs',options:{bold:true}}],
   ['Windows Settings app',
    'Manual browsing of settings by category',
    'You must know the name of the setting. No explanation, no undo.',
    'Finds the setting from a description of the symptom, explains it, and can revert it.'],
   ['Windows 11 Settings AI Agent',
    'On-device AI finds and applies settings from plain language',
    'Closed source, newer builds only. No universal undo and no change history.',
    'Every change stores its previous value first, so one-step undo always exists.'],
   ['Copilot Actions / Agent Workspace',
    'Agent clicks through the interface to perform tasks',
    'Reported to misread UI elements. No auditable record of what it altered.',
    'Never drives the GUI. Calls tested functions directly and journals every change.'],
   ['Open Interpreter',
    'A language model writes and runs code on your machine',
    'Asks you to approve generated code you are not equipped to judge.',
    'The model cannot write commands. You approve a tested operation in plain English.'],
   ['Tweak scripts and optimisers\n(WinUtil, CCleaner class)',
    'Apply batches of preset registry and service changes',
    'Opaque bulk edits, little per-change explanation or reversal.',
    'One change at a time, each explained, each individually revertible.']];
  s.addTable(rows,{x:M,y:1.4,w:W,colW:[2.4,2.75,3.35,3.56],
    fontSize:11,fontFace:B,color:TEXT,valign:'middle',rowH:0.62,
    border:{type:'solid',color:LINE,pt:0.75},fill:{color:WHITE},margin:0.09});

  card(s,M,5.32,W,1.28,'E8F2EE');
  s.addText('The gap, and our novelty',{x:M+0.32,y:5.44,w:4.0,h:0.3,fontSize:13,bold:true,color:SAFE,fontFace:B});
  s.addText('Natural-language settings search already exists — we do not claim it. What no reviewed tool provides is all four of these together:',
    {x:M+0.32,y:5.72,w:W-0.64,h:0.3,fontSize:12.5,color:TEXT,fontFace:B});
  const four=['1.  The model can never write a command','2.  Every change records its old value first',
              '3.  A complete, auditable change history','4.  Fully offline, no account, modest hardware'];
  const qw=(W-0.64)/4;
  four.forEach((t,i)=>{
    s.addText(t,{x:M+0.32+i*qw,y:6.04,w:qw-0.15,h:0.44,fontSize:11.5,bold:true,color:DEEP,fontFace:B,lineSpacing:14});});
  s.addNotes('This is the most important slide for the innovation mark. Say the Microsoft point out loud yourself: search is not our novelty. Then read the four numbered items at the bottom - that combination is.');
}

/* 6 OBJECTIVES */
{
  const s=slide('Objectives for This Semester','04  ·  Objectives');
  s.addText('Two objectives, each measurable and due within the semester.',
    {x:M,y:1.3,w:W,h:0.3,fontSize:14,color:MUTED,fontFace:B});

  const objs=[
   ['01','A settings library that cannot contain an irreversible action',
    ['Tool contract: every operation declares its limits, a preview, an undo and its own explanation',
     'The registry refuses to accept any state-changing tool that has no tested undo',
     'The audit journal writes the old value before the change is applied',
     'Build out 30 operations across power, display, network, privacy and storage'],
    '30 operations  ·  100% with a tested undo  ·  90% test coverage','Week 9',
    'Framework built and tested. Library in progress.',true],
   ['02','Plain English mapped onto that library, in a window anyone can use',
    ['Keyword retrieval narrows the catalogue to about ten candidates before any model runs',
     'A local model on Ollama selects one tool and fills in typed values — it never writes commands',
     'Below a confidence threshold, the system offers choices instead of acting',
     'A window with a confirmation card and a history panel, usable without a terminal'],
    '85% correct selection on 100 phrases  ·  8 GB RAM, no GPU','Week 12',
    'Retrieval and window built. Model integration next.',false]];

  const cw=(W-0.3)/2;
  objs.forEach((o,i)=>{
    const x=M+i*(cw+0.3);
    card(s,x,1.7,cw,4.55);
    s.addText(o[0],{x:x+0.28,y:1.88,w:0.6,h:0.42,fontSize:22,bold:true,color:SAFE,fontFace:H});
    s.addText(o[1],{x:x+0.95,y:1.86,w:cw-1.25,h:0.7,fontSize:15,bold:true,color:DEEP,fontFace:H,lineSpacing:19});

    s.addText('How we are achieving it',{x:x+0.28,y:2.62,w:cw-0.56,h:0.26,
      fontSize:10.5,bold:true,color:SAFE,fontFace:B,charSpacing:0.8});
    s.addText(o[2].map((t,j)=>({text:t,options:{bullet:true,
      breakLine:j<o[2].length-1,paraSpaceAfter:7}})),
      {x:x+0.28,y:2.9,w:cw-0.56,h:2.0,fontSize:11.5,color:TEXT,fontFace:B,lineSpacing:15});

    s.addShape(pres.ShapeType.rect,{x:x+0.28,y:5.02,w:cw-0.56,h:0.012,
      fill:{color:LINE},line:{color:LINE,width:0}});
    s.addText('Measured by',{x:x+0.28,y:5.12,w:cw-0.56,h:0.24,fontSize:10,bold:true,color:MUTED,fontFace:B});
    s.addText(o[3],{x:x+0.28,y:5.34,w:cw-0.56,h:0.3,fontSize:11.5,bold:true,color:DEEP,fontFace:B});
    s.addText('Due '+o[4],{x:x+0.28,y:5.68,w:1.5,h:0.28,fontSize:11.5,bold:true,color:WARN,fontFace:B});
    s.addText(o[5],{x:x+1.85,y:5.68,w:cw-2.15,h:0.28,fontSize:11.5,
      color: o[6]?SAFE:MUTED,fontFace:B,italic:true});
  });

  s.addText('Breadth beyond settings — file search, environment repair, firmware explanation — is Capstone-II, not this semester.',
    {x:M,y:6.42,w:W,h:0.3,fontSize:12,color:MUTED,italic:true,fontFace:B});
  s.addNotes('Only two objectives, both due this semester. For each, the four bullets are how we get there. Say the status honestly: objective one framework is done and the library is in progress; objective two has retrieval and the window built, model integration is next.');
}

/* 7 METHODOLOGY */
{
  const s=slide('Methodology','05  ·  Methodology');
  s.addText('Five phases, ordered so the safety layer is built and tested before any AI is added.',
    {x:M,y:1.3,w:W,h:0.3,fontSize:14,color:MUTED,fontFace:B});
  const ph=[['0','Foundation','Tool contract, journal, first reversible operation','Wk 3–5'],
            ['1','Operation library','Breadth across five setting categories, with tests','Wk 5–9'],
            ['2','Local model','Ollama; intent mapped to a shortlist of tools','Wk 9–11'],
            ['3','Interface','Window, confirmation card, history and undo','Wk 11–12'],
            ['4','Validation','Accuracy, revert correctness, low-spec benchmark','Wk 12']];
  const cw=(W-4*0.22)/5;
  ph.forEach((p,i)=>{
    const x=M+i*(cw+0.22);
    card(s,x,1.75,cw,2.5, i===2?'FBEEE9':SOFT);
    s.addText('PHASE '+p[0],{x:x+0.2,y:1.92,w:cw-0.4,h:0.26,fontSize:10.5,bold:true,color:SAFE,fontFace:B,charSpacing:0.8});
    s.addText(p[1],{x:x+0.2,y:2.2,w:cw-0.4,h:0.62,fontSize:16,bold:true,color:DEEP,fontFace:H});
    s.addText(p[2],{x:x+0.2,y:2.85,w:cw-0.4,h:1.05,fontSize:12,color:TEXT,fontFace:B,lineSpacing:15});
    s.addText(p[3],{x:x+0.2,y:3.92,w:cw-0.4,h:0.28,fontSize:11.5,bold:true,color:WARN,fontFace:B});});

  card(s,M,4.5,W*0.55,1.55);
  s.addText('Tools and technologies',{x:M+0.3,y:4.68,w:6.5,h:0.3,fontSize:13,bold:true,color:DEEP,fontFace:B});
  s.addText('Python 3.10+  ·  psutil  ·  pytest  ·  Tkinter\npowercfg / PowerShell / WMI  ·  Ollama  ·  Git\nIncremental, test-first development',
    {x:M+0.3,y:5.0,w:W*0.55-0.6,h:0.95,fontSize:13,color:TEXT,fontFace:B,lineSpacing:19});
  card(s,M+W*0.57,4.5,W*0.43,1.55,'E8F2EE');
  s.addText('Why the AI comes last',{x:M+W*0.57+0.3,y:4.68,w:W*0.43-0.6,h:0.3,fontSize:13,bold:true,color:SAFE,fontFace:B});
  s.addText('The library of operations is fully testable with no model present. Building it first means a weak local model cannot sink the project — it simply degrades to a working, menu-driven tool.',
    {x:M+W*0.57+0.3,y:5.0,w:W*0.43-0.6,h:1.0,fontSize:12.5,color:TEXT,fontFace:B,lineSpacing:16});
  s.addNotes('The green box is the answer to "where is the AI". Say it before they ask.');
}

/* 8 ARCHITECTURE + FLOWCHART */
{
  const s=slide('How It Works','06  ·  Flowchart');

  const NW=3.35, cx=M+2.0, nx=cx-NW/2;
  const arrow=(x,y,h)=>s.addShape(pres.ShapeType.line,{x,y,w:0,h,
    line:{color:'8C99A6',width:1.5,endArrowType:'triangle'}});
  const node=(txt,y,h,fill,border,fs)=>s.addText(txt,{
    shape:pres.ShapeType.roundRect,x:nx,y,w:NW,h,rectRadius:0.05,
    fill:{color:fill},line:{color:border,width:1.25},
    align:'center',valign:'middle',fontSize:fs||11.5,color:TEXT,fontFace:B,margin:0});
  const diamond=(txt,y,h)=>s.addText(txt,{
    shape:pres.ShapeType.diamond,x:nx,y,w:NW,h,
    fill:{color:'FFFFFF'},line:{color:DEEP,width:1.25},
    align:'center',valign:'middle',fontSize:11.5,bold:true,color:DEEP,fontFace:B,margin:0});
  const stop=(txt,y)=>s.addText(txt,{
    shape:pres.ShapeType.roundRect,x:M+4.85,y,w:2.85,h:0.5,rectRadius:0.05,
    fill:{color:'FBEEE9'},line:{color:WARN,width:1.25},
    align:'center',valign:'middle',fontSize:11,bold:true,color:WARN,fontFace:B,margin:0});
  const branch=(y)=>{
    s.addShape(pres.ShapeType.line,{x:nx+NW,y,w:0.85,h:0,
      line:{color:WARN,width:1.5,endArrowType:'triangle'}});
    s.addText('No',{x:nx+NW+0.16,y:y-0.28,w:0.5,h:0.24,fontSize:10,bold:true,
      color:WARN,fontFace:B,margin:0});
  };
  const yes=(y)=>s.addText('Yes',{x:cx+0.09,y,w:0.5,h:0.2,fontSize:9.5,bold:true,
    color:SAFE,fontFace:B,margin:0,valign:'middle'});

  node('User describes the problem',1.40,0.45,'E8F2EE',SAFE,12);
  arrow(cx,1.85,0.16);
  node('Find the matching setting',2.01,0.45,'FFFFFF',LINE);
  arrow(cx,2.46,0.16);
  diamond('Value within limits?',2.62,0.80);
  branch(3.02); stop('Rejected. Nothing changed.',2.77);
  arrow(cx,3.42,0.30); yes(3.48);
  node('Show the exact command',3.72,0.45,'FFFFFF',LINE);
  arrow(cx,4.17,0.16);
  diamond('User approves?',4.33,0.80);
  branch(4.73); stop('Cancelled. Nothing changed.',4.48);
  arrow(cx,5.13,0.30); yes(5.19);
  node('Save the old value, then apply',5.43,0.45,'FFFFFF',LINE);
  arrow(cx,5.88,0.16);
  node('Explain it — undo available',6.04,0.45,'E8F2EE',SAFE,12);

  // ---- architecture, kept deliberately brief ----
  s.addText('Layers',{x:M+8.15,y:1.42,w:3.9,h:0.26,fontSize:11,bold:true,
    color:MUTED,fontFace:B,charSpacing:0.8,margin:0});
  const layers=[['Window',SOFT],['Local model  (optional)','FBEEE9'],
                ['Tool library',SOFT],['OS adapter',SOFT],['Audit journal',SOFT]];
  layers.forEach((l,i)=>{
    const y=1.78+i*0.62;
    card(s,M+8.15,y,W-8.15,0.5,l[1]);
    s.addText(l[0],{x:M+8.4,y:y+0.05,w:W-8.6,h:0.4,fontSize:12.5,bold:true,
      color:DEEP,fontFace:B,valign:'middle',margin:0});
    if(i<4) s.addShape(pres.ShapeType.line,{x:M+8.15+(W-8.15)/2,y:y+0.5,w:0,h:0.12,
      line:{color:'8C99A6',width:1.25,endArrowType:'triangle'}});
  });
  card(s,M+8.15,4.92,W-8.15,1.4,'E8F2EE');
  s.addText('The model only picks a tool from the library. It never writes a command.',
    {x:M+8.4,y:5.08,w:W-8.6,h:1.1,fontSize:12.5,bold:true,color:DEEP,fontFace:B,lineSpacing:17});
  s.addNotes('Trace the flowchart top to bottom in one pass. The two diamonds are the point - the system stops rather than guesses. Then the layers on the right, and finish on the green box.');
}

/* 9 PROGRESS + TIMELINE */
{
  const s=slide('Progress Against Our Objectives','07  ·  Where we are');

  const cols=[['01','A library that cannot contain an irreversible action',
    [['Done','Every setting declares its limits, a preview, an undo and its own explanation'],
     ['Done','The system refuses to load a setting that has no working undo'],
     ['Done','The old value is written down before the change is applied'],
     ['Done','Seven settings working: pointer size, text size, click speed, and more'],
     ['Now','Extending across the five setting categories']]],
   ['02','Plain English mapped onto that library, in a usable window',
    [['Done','Typing a problem in your own words finds the right setting'],
     ['Done','A window with a confirmation card, history and one-step undo'],
     ['Done','Every change verified against Windows itself, then reverted'],
     ['Next','Local model on Ollama selecting settings and filling in values'],
     ['Next','When unsure, offer choices instead of acting']]]];

  const cw=(W-0.3)/2;
  cols.forEach((c,i)=>{
    const x=M+i*(cw+0.3);
    card(s,x,1.38,cw,2.62);
    s.addText(c[0],{x:x+0.28,y:1.55,w:0.6,h:0.42,fontSize:21,bold:true,color:SAFE,fontFace:H});
    s.addText(c[1],{x:x+0.95,y:1.52,w:cw-1.2,h:0.5,fontSize:14,bold:true,color:DEEP,fontFace:H});
    c[2].forEach((r,j)=>{
      const y=2.12+j*0.36;
      s.addText(r[0],{x:x+0.28,y,w:0.62,h:0.28,fontSize:10,bold:true,
        color: r[0]==='Done'?SAFE:WARN,fontFace:B,margin:0});
      s.addText(r[1],{x:x+0.98,y,w:cw-1.25,h:0.32,fontSize:11,color:TEXT,fontFace:B,margin:0});
    });
  });

  // ---- plan for the rest of the semester ----
  const AX=5.28, x0=M+0.75, x1=M+W-0.75, span=x1-x0;
  const wx = w => x0 + ((w-1)/11)*span;
  s.addShape(pres.ShapeType.roundRect,{x:x0,y:AX-0.03,w:span,h:0.06,
    fill:{color:'DCE3E8'},line:{color:'DCE3E8',width:0},rectRadius:0.03});
  for(let w=1;w<=12;w++){
    s.addShape(pres.ShapeType.rect,{x:wx(w)-0.008,y:AX+0.06,w:0.016,h:0.06,
      fill:{color:'C3CDD5'},line:{color:'C3CDD5',width:0}});
    s.addText('W'+w,{x:wx(w)-0.3,y:AX+0.14,w:0.6,h:0.2,fontSize:8.5,
      color:MUTED,align:'center',fontFace:B,margin:0});
  }
  const ms=[[5,'Undo and audit working','up'],
            [10,'All five setting categories done','down'],
            [12,'Model and window complete','up']];
  ms.forEach(m=>{
    const [w,label,side]=m, cx=wx(w);
    s.addShape(pres.ShapeType.ellipse,{x:cx-0.085,y:AX-0.085,w:0.17,h:0.17,
      fill:{color:SAFE},line:{color:SAFE,width:1.5}});
    s.addShape(pres.ShapeType.rect,{x:cx-0.01,y: side==='up'?AX-0.34:AX+0.41,
      w:0.02,h:0.16,fill:{color:'C3CDD5'},line:{color:'C3CDD5',width:0}});
    let lx=cx-1.6, lw=3.2;
    if(lx<M) lx=M;
    if(lx+lw>M+W) lx=M+W-lw;
    s.addText(label,{x:lx,y: side==='up'?AX-0.68:AX+0.62,w:lw,h:0.3,
      fontSize:12.5,bold:true,color:DEEP,fontFace:B,align:'center',margin:0});
  });
  s.addNotes('Report against the two objectives, not a feature list. Objective one is essentially done - seven settings, every one reversible. Objective two has the search and the window working; the local model is next. Then the plan for the remaining weeks.');
}

/* 10 CHALLENGES */
{
  const s=slide('Challenges','08  ·  Challenges');
  [['Challenge',M+0.26,2.9],['Risk',M+3.45,4.3],['How we handle it',M+8.0,W-8.25]]
    .forEach(h=>s.addText(h[0],{x:h[1],y:1.3,w:h[2],h:0.24,fontSize:10.5,bold:true,
      color:MUTED,fontFace:B,charSpacing:0.8,margin:0}));

  const ch=[
   ['Small models may pick the wrong setting',
    'A 1-3B model running on a cheap laptop may not reliably map a sentence to the right setting as the library grows.',
    'Keyword retrieval narrows the list to about ten before the model sees it. Below a confidence threshold it offers choices instead of acting.'],
   ['Windows speaks other languages',
    'Windows command output is translated, so reading English labels fails on a non-English installation.',
    'A positional fallback is implemented and tested. Moving to typed WMI values removes the problem entirely.'],
   ['Some settings need administrator rights',
    'Prompting for elevation repeatedly teaches people to approve without reading — the opposite of what we want.',
    'Every setting we have chosen so far is per-user and needs no elevation. Where it is unavoidable, explain why and ask once.'],
   ['A vendor already does part of this',
    'Windows 11 now ships an on-device AI agent that finds and applies settings from plain language.',
    'We do not claim that part. We compete on guaranteed undo, a complete audit trail, and running offline with no account.']];

  ch.forEach((c,i)=>{
    const y=1.6+i*1.24;
    card(s,M,y,W,1.1);
    s.addText(c[0],{x:M+0.26,y:y+0.14,w:2.95,h:0.82,fontSize:13.5,bold:true,
      color:WARN,fontFace:B,valign:'middle',lineSpacing:17});
    s.addText(c[1],{x:M+3.45,y:y+0.14,w:4.3,h:0.82,fontSize:11.5,color:TEXT,
      fontFace:B,valign:'middle',lineSpacing:15});
    s.addText(c[2],{x:M+8.0,y:y+0.14,w:W-8.25,h:0.82,fontSize:11.5,color:SAFE,
      fontFace:B,valign:'middle',lineSpacing:15});
  });
  s.addNotes('Four challenges, each with what we are already doing about it. Raise the last one - the Microsoft overlap - yourself rather than waiting to be asked.');
}

pres.writeFile({fileName:'Capstone_MidTermReview_LocalFirst_AI_OS_Companion.pptx'}).then(f=>console.log('WROTE',f));
