export function legacy45(wb,ss){
const v=(n,a,x)=>ss[n].getRange(a).values=[[x]];
const hyp=ss.Гипотезы.getRange("A5:A12").values;
const ec=[[0,.4,.4,0]];
const outrows=[8,9,10,11,12,14,15,16];
const read=(n,a)=>ss[n].getRange(a).values[0][0],tests=[];const assert=(x,msg)=>{if(!x)throw Error(msg);tests.push(msg);};const near=(a,b)=>Math.abs(a-b)<1e-7;
assert(read('Параметры','B28')===1&&read('Когорты','X10')===1,'Baseline constraints');assert(near(read('Параметры','B27'),.201),'Global CR weighted from cohort gaps');assert(near(read('Когорты','F5')-read('Когорты','F7'),.18),'18 percentage points, not relative percent');
for(let h=0;h<8;h++)assert(read('Расчёт','S'+(140+h))===1,'Valid option '+hyp[h][0]);
let baseResults=outrows.map(r=>read('Итоги','E'+r));let baseC=read('Когорты','U10');let baseF=read('Когорты','V10');assert(near(baseC,65000)&&near(baseF,13000),'Exact daily section totals');
assert(near(read('Расчёт','P140'),.5625),'Independent 25/25 penalties leave 56.25 percent');assert(near(read('Штрафы','E9'),read('Итоги','E8')),'Penalty grid reproduces active H1');
for(let h=0;h<8;h++){let a=5+h*16,z=a+15;let total=0,buy=0;for(let r=a;r<=z;r++){total+=read('Расчёт','F'+r);buy+=read('Расчёт','J'+r);}assert(near(total,100000)&&near(buy,20100),'Unique daily population and buyers conserved '+hyp[h][0]);}
let s=read('Когорты','F5');v('Параметры','B4',2);wb.recalculate();assert(near(read('Параметры','B27'),.18),'Global CR anchor respected');assert(near(read('Когорты','F5'),.279),'Whale CR reconciles global anchor');v('Параметры','B4',1);
for(let c=1;c<=3;c++){v('Параметры','B3',c);wb.recalculate();assert(read('Когорты','X10')===1&&read('Параметры','B28')===1,'Cohort scenario '+c);}
v('Параметры','B3',2);v('Параметры','B5',3);wb.recalculate();assert(near(read('Итоги','E13'),read('Итоги','E16')),'Parent H6 selects one alternative');v('Параметры','B5',1);
// Stress: both inputs target 100%, and explicit intersection removes duplication.
for(let r=5;r<=8;r++)ss.Воздействие.getRange('C'+r+':E'+r).values=[[1,1,1]];wb.recalculate();let union=100000*(.65+.13-.104);assert(near(read('Итоги','D8'),union),'Two-entry unique target equals union, not sum');
for(let r=5;r<=8;r++)ss.Воздействие.getRange('C'+r+':E'+r).values=[[0,1,0]];wb.recalculate();assert(near(read('Итоги','D8'),13000),'F-only effect reaches 13000, not C DAU');assert(near(read('Когорты','U10'),baseC),'F-only leaves C visits fixed');
for(let r=5;r<=8;r++)v('Воздействие','G'+r,.10);wb.recalculate();assert(read('Итоги','E8')<0&&read('Итоги','I8')==='Падение','Explicit baseline CR loss triggers negative effect and guardrail');
for(let r=5;r<=8;r++){let k=r-5;ss.Воздействие.getRange('C'+r+':G'+r).values=[[ec[0][k],0,0,0,0]];}
v('Параметры','D15',.3);wb.recalculate();assert(read('Параметры','B28')===0,'Invalid shares flagged');v('Параметры','D15',.2);v('Параметры','C15',null);wb.recalculate();assert(read('Параметры','B28')===1,'Blank inactive case does not block active');v('Параметры','B3',1);wb.recalculate();assert(read('Параметры','B28')===0,'Blank active case exposed');v('Параметры','C15',.1);v('Параметры','B3',2);
v('Гипотезы','D5',0);v('Гипотезы','E5',0);wb.recalculate();assert(near(read('Расчёт','AH140'),read('Расчёт','D140')),'Zero penalties preserve full 10 percent benefit');v('Гипотезы','D5',.5);v('Гипотезы','E5',.5);wb.recalculate();assert(near(read('Расчёт','AH140'),read('Расчёт','D140')*.25),'50/50 penalties retain one quarter');v('Гипотезы','D5',.25);v('Гипотезы','E5',.25);wb.recalculate();for(let h=0;h<8;h++)assert(near(read('Итоги','E'+outrows[h]),baseResults[h]),'All temporary edits restored '+hyp[h][0]);

return tests;
}
