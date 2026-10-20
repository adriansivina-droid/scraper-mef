const fs=require('fs');
const {Document,Packer,Paragraph,TextRun,AlignmentType,PageBreak}=require('docx');
const A='/home/user/scraper-mef/HIDROCARBUROS/analisis/';
const md=fs.readFileSync(A+'Loreto_petroleo_2025_texto.md','utf8').split('\n').filter(l=>l.trim());
const ch=[];
md.forEach((l,i)=>{
  if(l.trim()==='---'){ch.push(new Paragraph({children:[new PageBreak()]}));return;}
  if(i===0||l.startsWith('## ')){ch.push(new Paragraph({spacing:{after:200},children:[new TextRun({text:l.replace(/^## /,''),bold:true,font:'Arial',size:24,color:'1F4E79'})]}));return;}
  if(l.startsWith('Fuente:')){ch.push(new Paragraph({alignment:AlignmentType.JUSTIFIED,spacing:{before:120,after:200},children:[new TextRun({text:'Fuente:',bold:true,font:'Arial',size:16}),new TextRun({text:l.slice(7),font:'Arial',size:16})]}));return;}
  if(l.length<80&&!/[.:]$/.test(l)){ch.push(new Paragraph({spacing:{before:120,after:120},keepNext:true,children:[new TextRun({text:l,bold:true,font:'Arial',size:22})]}));return;}
  ch.push(new Paragraph({alignment:AlignmentType.JUSTIFIED,spacing:{after:160,line:276},children:[new TextRun({text:l,font:'Arial',size:22})]}));
});
const doc=new Document({sections:[{properties:{page:{margin:{top:1418,bottom:1418,left:1418,right:1418}}},children:ch}]});
Packer.toBuffer(doc).then(b=>fs.writeFileSync(A+'Loreto_petroleo_2025_texto.docx',b));
