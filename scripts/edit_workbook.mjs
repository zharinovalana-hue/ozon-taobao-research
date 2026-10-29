// Author a working copy of the existing model. Never calls Workbook.create().
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
import {legacy45} from '../tests/legacy45.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const input=JSON.parse(await fs.readFile(root+'/data/model_inputs.json','utf8'));
const bundle=JSON.parse(await fs.readFile(root+'/results/model_results.json','utf8'));
const sources=JSON.parse(await fs.readFile(root+'/data/sources.json','utf8'));
const taobao=JSON.parse(await fs.readFile(root+'/data/taobao_summary.json','utf8'));
const cases=bundle.cases,results=bundle.results,N=cases.length;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'/models/Ozon_модель_кейса.xlsx'));
const oldNames=['Итоги','Параметры','Когорты','Гипотезы','Воздействие','Штрафы','Расчёт','Исходные','Внешние','Методика'];
const ss=Object.fromEntries(oldNames.map(n=>[n,wb.worksheets.getItem(n)]));
for(const n of ['Сценарии','Входы H','Сравнение','Taobao','Источники','Масштаб','Версия срезов'])ss[n]=wb.worksheets.getItem(n);
const newSheets=[];for(const n of ['Размеры Корзин','Порог H1 H4']){try{ss[n]=wb.worksheets.getItem(n);}catch{ss[n]=wb.worksheets.add(n);newSheets.push(n);}}
ss.Сценарии.getRange('A34:AA35').unmerge();
const col=n=>{let s='';for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const v=(n,a,x)=>ss[n].getRange(a).values=[[x]];
const f=(n,a,x)=>ss[n].getRange(a).formulas=[[x]];
const row=(n,r,x)=>ss[n].getRange('A'+r+':'+col(x.length)+r).values=[x];
const read=(n,a)=>ss[n].getRange(a).values[0][0];
const pct=(n,a)=>ss[n].getRange(a).setNumberFormat('0.00%');
const head=(n,r,x)=>{row(n,r,x);ss[n].getRange('A'+r+':'+col(x.length)+r).format={fill:'#263E60',font:{bold:true,color:'#FFFFFF',size:10,name:'Arial'},wrapText:true,rowHeight:62,verticalAlignment:'center'};};
const title=(n,text,last='K',rows=50)=>{
 const s=ss[n];s.showGridLines=false;s.tabColor='#477A68';
 s.getRange('A1:'+last+rows).format={font:{name:'Arial',size:10,color:'#25364A'},columnWidth:16,rowHeight:26};
 if(newSheets.includes(n))s.getRange('A2:F2').merge();v(n,'A2',text);s.getRange('A2').format={font:{size:15,bold:true,color:'#263E60'},rowHeight:36};
 s.freezePanes.freezeRows(5);s.freezePanes.freezeColumns(2);
};
const scenarioFields=['index','name','kind','dau','mau','s1','s2','s3','s4','global_cr_input','whale_cr','anchor','owners_small','overlap','reach_scale','behavior_penalty','product_penalty','loss_c','loss_f','income_delta','revenue_per_buyer','enforce_ozon','threshold','wC','wF','wBoth','wOutside','h1_need','h4_reach_multiplier'];
title('Сценарии','Сценарии · исходные три сохранены; выбран базовый сценарий размеров Корзины','AC',N+11);
const headers=['№','Сценарий','Тип','DAU','MAU','S1','S2','S3','S4','Global CR: ввод','CR китов','Якорь 1/2','Владельцы F в малом F','P(C | F-визит)','Множитель охвата','Штраф поведения','Штраф продукта','Потеря CR C','Потеря CR F','Δ дохода / покупателя','Доход / покупателя, у.е.','Условия Ozon 1/0','Порог размеров Корзины','Вес: только C','Вес: только F','Вес: оба','Вес: вне'];
for(let t=0;t<4;t++)headers[23+t]=['Справочно: вес C S1','Справочно: вес F S1','Справочно: вес оба S1','Справочно: вес вне S1'][t];
headers.push('Потребность H1 среди 40+','Множитель охвата H4');head('Сценарии',5,headers);
const caseRows=[];
for(let i=0;i<N;i++){
 const c=cases[i],r=6+i,weights=c.weights?.[0]??input.weights[0];
 const values=[i+1,c.name,c.kind,c.dau,c.mau,...c.shares,c.global_cr_input,c.whale_cr,c.anchor,c.owners_small,c.overlap,c.reach_scale,c.behavior_penalty,c.product_penalty,c.loss_c,c.loss_f,c.income_delta,c.revenue_per_buyer,c.enforce_ozon?1:0,c.threshold,...weights,c.h1_need??.4,c.h4_reach_multiplier??1];
 row('Сценарии',r,values);caseRows.push({id:c.id,row:r});
 for(let t=0;t<4;t++)f('Сценарии',col(24+t)+r,`='Входы H'!${col(14+t)}${5+4*i}`);
 if(i<3){for(let k=0;k<4;k++)f('Сценарии',col(6+k)+r,`='Параметры'!${col(3+i)}${15+k}`);
   f('Сценарии','J'+r,`='Параметры'!${col(3+i)}20`);f('Сценарии','K'+r,`='Параметры'!${col(3+i)}19`);f('Сценарии','M'+r,`='Параметры'!${col(3+i)}21`);}
}
v('Сценарии','A3','Активный');
for(let c=2;c<=29;c++)f('Сценарии',col(c)+'3',`=CHOOSE('Параметры'!$B$3,${cases.map((_,i)=>col(c)+(6+i)).join(',')})`);
ss.Сценарии.getRange('B:B').format.columnWidth=40;ss.Сценарии.getRange('C:C').format.columnWidth=17;
ss.Сценарии.getRange('F6:U'+(N+5)).format.fill='#FFF1CC';pct('Сценарии','F6:K'+(N+5));pct('Сценарии','M6:N'+(N+5));pct('Сценарии','P6:T'+(N+5));
ss.Сценарии.getRange('D6:E'+(N+5)).setNumberFormat('#,##0');
pct('Сценарии','F3:K3');pct('Сценарии','M3:N3');pct('Сценарии','P3:T3');ss.Сценарии.getRange('D3:E3').setNumberFormat('#,##0');
v('Сценарии','A'+(N+8),'Все CR и риски сценарные. 44/84 млн: март 2026. Распределения Корзин сконструированы по среднему 60, медиане 24 и максимуму 300; это не измерения.');
ss.Сценарии.getRange('A'+(N+8)+':AA'+(N+9)).merge();ss.Сценарии.getRange('A'+(N+8)).format={wrapText:true,rowHeight:44};

v('Параметры','B3',6);f('Параметры','B4',"='Сценарии'!L3");
for(const [a,c] of [['B8','D'],['B9','E'],['B15','F'],['B16','G'],['B17','H'],['B18','I'],['B19','K'],['B20','J'],['B21','M']])f('Параметры',a,`='Сценарии'!${c}3`);
ss.Параметры.getRange('B3').dataValidation={rule:{type:'list',values:cases.map((_,i)=>String(i+1))}};
let valid=ss.Параметры.getRange('B28').formulas[0][0];
valid=valid.replace(/OR\(B3=1,B3=2,B3=3[^)]*\)/,`OR(${cases.map((_,i)=>'B3='+(i+1)).join(',')})`);f('Параметры','B28',valid);
f('Параметры','B28',valid.replace('B26>=0.18',"B26>=MAX(0,-MIN('Исходные'!B17:B19)/100)"));
v('Параметры','D3','Сценарии 1–'+N+' на листе «Сценарии»');v('Параметры','E3',null);v('Параметры','F3',null);
v('Параметры','D4','Якорь выбран сценарием; исходные CR не являются фактами Ozon');v('Параметры','E4',null);
v('Параметры','C8','Масштаб сценария');v('Параметры','D8','44 млн только для публичного масштаба марта 2026; контроли нормированы');
v('Параметры','C9','Масштаб сценария');v('Параметры','D9','84 млн, март 2026; MAU в дневной эффект не входит');
v('Параметры','A37','Сценарий: B3. Прежние три набора C:E сохранены. Новые драйверы на «Сценариях», охваты на «Входах H».');
f('Итоги','B3',"='Сценарии'!B3");v('Итоги','A20','Публичный масштаб: март 2026. Пользователи/эффекты являются условной экстраполяцией; см. «Масштаб».');
ss.Итоги.getRange('E5').setNumberFormat('#,##0');
v('Итоги','H23','ARPU0, у.е.');v('Итоги','I23','ARPU1, у.е.');
for(let k=0;k<4;k++){
 const r=k+5;for(let j=0;j<2;j++)f('Когорты',col(8+j)+r,`=CHOOSE('Параметры'!$B$3,${cases.map((_,i)=>`'Входы H'!${col(18+j)}${5+4*i+k}`).join(',')})`);f('Когорты','J'+r,"='Сценарии'!N3");f('Когорты','T'+r,"='Сценарии'!U3");
 for(let t=0;t<4;t++)f('Когорты',col(15+t)+r,`=CHOOSE('Параметры'!$B$3,${cases.map((_,i)=>`'Входы H'!${col(14+t)}${5+4*i+k}`).join(',')})`);
}
v('Когорты','T4','Доход / покупателя, у.е.');
let cohortValid=ss.Когорты.getRange('X10').formulas[0][0];
cohortValid=cohortValid.replace("W10/U10>='Исходные'!B9,W10/U10<='Исходные'!B10", "OR('Сценарии'!V3=0,AND(W10/U10>='Исходные'!B9,W10/U10<='Исходные'!B10))");
f('Когорты','X10',cohortValid);
v('Когорты','A15','S2/S3: 40+ SKU. Большое Избранное и независимость размеров — допущения; владение F проверяется отдельно (60–80%).');
title('Входы H','Охваты и исходные риски · допущения, сохранённые из прежней модели','J',43);
head('Входы H',4,['H','Когорта','Цель C','Цель F','Цель C∩F','Базовая потеря C','Базовая потеря F','Базовый Δ дохода','Статус']);
for(let h=0;h<8;h++)for(let k=0;k<4;k++){
 const r=5+4*h+k;row('Входы H',r,[input.hypotheses[h].id,'S'+(k+1),...input.hypotheses[h].reach[k],0,0,0,'Сценарное допущение']);
 for(let c=3;c<=5;c++)f('Воздействие',col(c)+r,(h===0&&[1,2].includes(k)&&c===3?`=IF('Параметры'!$B$3<=3,'Входы H'!C${r},'Сценарии'!$AB$3)*'Сценарии'!$O$3`:`='Входы H'!${col(c)}${r}*'Сценарии'!$O$3${h===3?"*'Сценарии'!$AC$3":''}`));
 for(const [c,driver] of [[6,'R'],[7,'S'],[8,'T']])f('Воздействие',col(c)+r,`='Входы H'!${col(c)}${r}+'Сценарии'!$${driver}$3`);
}
pct('Входы H','C5:H36');ss['Входы H'].getRange('C5:H36').format.fill='#FFF1CC';
ss['Входы H'].getRange('I:I').format.columnWidth=32;
ss['Входы H'].getRange('K1:Q'+(4+4*N)).format={font:{name:'Arial',size:10,color:'#25364A'},columnWidth:18,rowHeight:26};
ss['Входы H'].getRange('K4:S4').values=[['№ сценария','Сценарий','Когорта','Вес: C','Вес: F','Вес: оба','Вес: вне','P(C-визит)','P(F-визит)']];
ss['Входы H'].getRange('K4:Q4').format={fill:'#263E60',font:{bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:62};
ss['Входы H'].getRange('L:L').format.columnWidth=40;
for(let i=0;i<N;i++)for(let k=0;k<4;k++)ss['Входы H'].getRange('K'+(5+4*i+k)+':S'+(5+4*i+k)).values=[[i+1,cases[i].name,'S'+(k+1),...(cases[i].weights??input.weights)[k],...(cases[i].traffic??input.traffic)[k].slice(0,2)]];
ss['Входы H'].getRange('N5:Q'+(4+4*N)).format.fill='#FFF1CC';
for(let h=0;h<8;h++){
 let r=h+5;f('Гипотезы','D'+r,"='Сценарии'!P3");f('Гипотезы','E'+r,"='Сценарии'!Q3");
 f('Гипотезы','I'+r,`=IF(AND(ISNUMBER(D${r}),ISNUMBER(E${r}),D${r}>=0,D${r}<=1,E${r}>=0,E${r}<=1),1,0)`);
}
v('Гипотезы','K8',1);v('Гипотезы','L8','Нулевая польза');ss.Гипотезы.getRange('D5:E12').dataValidation={rule:{type:'list',formula1:'$K$5:$K$8'}};
v('Гипотезы','A16','У всех +10% до штрафов. 100% штраф означает нулевую пользу; ущерб базовой CR задаётся отдельно.');
const outrows=[8,9,10,11,12,14,15,16];
for(const r of outrows){const prior=ss.Итоги.getRange('K'+r).formulas[0][0];f('Итоги','K'+r,`=IF('Сценарии'!V3=0,"Внешний сценарий",${prior.slice(1)})`);}

title('Taobao','Taobao · проверенный агрегат 987 994 пользователей','J',42);
head('Taobao',5,['Метрика','Значение','Единица / смысл']);
const totals=[['Пользователи',taobao.users,'За всё окно'],['С cart-добавлениями',taobao.cart_users,'Не посещения Корзины'],['С fav-добавлениями',taobao.fav_users,'Не остатки Избранного'],['С обоими',taobao.both_users,'Оба типа добавлений за окно'],['Покупатели',taobao.buyers,'Любой buy в том же окне']];totals.forEach((a,i)=>row('Taobao',6+i,a));
head('Taobao',13,['Порог','C≥','F≥','Когорта','Пользователи','Доля','Покупатели','Purchase rate за окно']);
let tr=14;for(const t of taobao.thresholds)for(const c of t.cohorts)row('Taobao',tr++,['P'+Math.round(t.quantile*100),t.cart_threshold,t.fav_threshold,c.id,c.users,c.share,c.buyers,c.purchase_rate]);
pct('Taobao','F14:F29');pct('Taobao','H14:H29');ss.Taobao.getRange('A:A').format.columnWidth=28;ss.Taobao.getRange('C:C').format.columnWidth=32;
ss.Taobao.getRange('B6:B10').setNumberFormat('#,##0');ss.Taobao.getRange('E14:E29').setNumberFormat('#,##0');ss.Taobao.getRange('G14:G29').setNumberFormat('#,##0');ss.Taobao.getRange('D14:D29').format.horizontalAlignment='center';
v('Taobao','A33','События за окно ≠ остатки SKU. Purchase rate за окно ≠ дневная CR Ozon. Порог ≥P90 включает совпадения на границе.');ss.Taobao.getRange('A33:J35').merge();ss.Taobao.getRange('A33').format={wrapText:true,rowHeight:55};
v('Taobao','A37','11,17% имеют 14+ уникальных добавлений за девять дней. Это НЕ доля Корзин 40+; агрегат не используется в охвате H1 или сценариях Ozon.');ss.Taobao.getRange('A37:J39').merge();ss.Taobao.getRange('A37').format={wrapText:true,rowHeight:55};

title('Источники','Источники · назначение и пределы переноса','F',sources.length+8);
head('Источники',5,['ID / источник','Статус проверки','Проверенный факт','Использование','Ограничение','Ссылка']);
const sourceStatus={verified_primary:'Первоисточник',verified_primary_search_index:'Индекс официальной страницы',verified_publisher_search_index:'Индекс страницы издателя',verified_author_fulltext:'Полный текст от автора',verified_publisher_abstract:'Аннотация издателя',verified_publisher_abstract_search_index:'Аннотация в индексе издателя',verified_primary_and_user_aggregate:'Источник и агрегат проверены',verified_supplied_synthetic_case:'Учебный синтетический кейс'};
for(let i=0;i<sources.length;i++)row('Источники',6+i,[sources[i].title,sourceStatus[sources[i].status]??sources[i].status,sources[i].facts,sources[i].use,sources[i].limitation,sources[i].url]);
for(const c of ['A','B'])ss.Источники.getRange(c+':'+c).format.columnWidth=30;
for(const c of ['C','D','E'])ss.Источники.getRange(c+':'+c).format.columnWidth=52;
ss.Источники.getRange('F:F').format.columnWidth=60;ss.Источники.getRange('A6:F'+(sources.length+5)).format={wrapText:true,rowHeight:115,verticalAlignment:'top'};
v('Внешние','A16','Актуальные статусы и ограничения: лист «Источники». Старые внешние величины сохранены как исторический контекст.');
v('Внешние','G5','Точное старое значение отдельно не перепроверено; не DAU и не вход модели');v('Внешние','G6','Точное старое значение отдельно не перепроверено; подтверждено округлённое 1,2 млрд');
v('Внешние','G9','Заявленный рост; не раскрыты контроль/атрибуция и единица прироста; в формулы не входит');

title('Масштаб','Масштаб Ozon · факты и условные проверки интенсивности','E',30);
head('Масштаб',5,['Показатель','Значение','Единица','Статус','Ограничение']);
const p=input.public_ozon;
const scale=[['DAU, март 2026',p.dau_march_2026,'пользователей','Ozon IR','Не средний DAU квартала'],['MAU, март 2026',p.mau_march_2026,'пользователей','Ozon IR','Не использовать в дневной CR'],['Заказы, I кв. 2026',p.q1_orders,'заказов','Ozon IR','Не уникальные покупатели'],['Дней в I квартале',p.q1_days,'дней','Календарь','2026 не високосный'],['Активные покупатели, конец I кв.',p.q1_active_buyers,'пользователей','Ozon IR','Не DAU и не MAU'],['Частота, I кв.: свыше',p.trailing_orders_per_buyer,'заказов / год / покупателя','Ozon IR','Скользящая годовая метрика'],['Заказы, III кв. 2026',p.q3_orders_rounded,'заказов, округлённо','Ozon','Другая дата; мартовский DAU не переносится'],['Частота, III кв.',p.q3_frequency,'заказ / год / покупателя','Ozon','Не дневная CR']];scale.forEach((a,i)=>row('Масштаб',6+i,a));
row('Масштаб',16,['Заказов / день, I кв.',null,'заказов','Расчёт','Среднее по кварталу']);f('Масштаб','B16','=B8/B9');
row('Масштаб',17,['Заказов / условный DAU-день',null,'заказов / пользователя','Условный ориентир','Если мартовский DAU равен среднему за квартал и охваты совпадают']);f('Масштаб','B17','=B16/B6');
row('Масштаб',18,['Активная global CR',null,'доля','Допущение сценария','Не измеренный факт Ozon']);f('Масштаб','B18',"='Параметры'!B27");
row('Масштаб',19,['Заказов / покупателя-день',null,'заказов','Условный расчёт','Зависит от предположений строки 17']);f('Масштаб','B19','=B17/B18');
row('Масштаб',20,['Оговорка интенсивности',null,'','Диагностика','Не жёсткая граница: разные периоды и охваты']);f('Масштаб','B20','=IF(B19>=1,"Не противоречит ориентиру","CR выше условного ориентира заказов")');
row('Масштаб',23,['DAU Корзины при масштабе марта',null,'пользователей','Экстраполяция условия кейса','65% от 44 млн']);f('Масштаб','B23','=B6*0.65');
row('Масштаб',24,['DAU Избранного при масштабе марта',null,'пользователей','Экстраполяция условия кейса','13% от 44 млн']);f('Масштаб','B24','=B6*0.13');
row('Масштаб',25,['MAU Корзины при масштабе марта',null,'пользователей','Экстраполяция условия кейса','91% от 84 млн']);f('Масштаб','B25','=B7*0.91');
row('Масштаб',26,['MAU Избранного при масштабе марта',null,'пользователей','Экстраполяция условия кейса','20% от 84 млн']);f('Масштаб','B26','=B7*0.20');
for(const [r,den,fact] of [[23,'B6','B5'],[24,'B6','B6'],[25,'B7','B7'],[26,'B7','B8']])f('Масштаб','B'+r,`=${den}*'Исходные'!${fact}`);
ss.Масштаб.getRange('A:A').format.columnWidth=43;ss.Масштаб.getRange('B:B').format.columnWidth=36;ss.Масштаб.getRange('C:D').format.columnWidth=25;ss.Масштаб.getRange('E:E').format.columnWidth=60;
ss.Масштаб.getRange('A6:E26').format={wrapText:true,rowHeight:42};ss.Масштаб.getRange('B6:B16').setNumberFormat('#,##0');pct('Масштаб','B17:B18');ss.Масштаб.getRange('B19').setNumberFormat('0.000');ss.Масштаб.getRange('B23:B26').setNumberFormat('#,##0');
ss.Масштаб.getRange('B17').setNumberFormat('0.0000');

title('Сравнение','Сравнение H1–H6 · сохранённые результаты всех сценариев','S',26*N+30);
v('Сравнение','A3','Актуальность срезов');f('Сравнение','B3',"='Версия срезов'!G2");ss.Сравнение.getRange('B3:F3').merge();
ss.Сравнение.getRange('A4:J4').merge();v('Сравнение','A4','Эффекты ниже: процентные пункты. Это сохранённое сравнение; при изменении входов обновите scripts/run.py.');ss.Сравнение.getRange('A4').format={wrapText:true,rowHeight:36};
const topCases=['original','stock_11','ozon_stock_base','stock_49','cautious','favorable','zero','negative_combined'];
head('Сравнение',6,['H','Решение',...topCases.map(id=>cases.find(c=>c.id===id).name)]);
for(let h=0;h<8;h++)row('Сравнение',7+h,[input.hypotheses[h].id,input.hypotheses[h].name,...topCases.map(id=>results.find(r=>r.scenario===id&&r.hypothesis===input.hypotheses[h].id).delta_pp)]);
ss.Сравнение.getRange('C7:J14').setNumberFormat('0.0000');
head('Сравнение',18,['Сценарий','H','CR0','Δ CR, п.п.','Δ CR относит.','Δ покупателей','Цель, людей','CR C0','CR C1','CR F0','CR F1','ARPU0, у.е.','ARPU1, у.е.','ARPU1, индекс','Guard C','Guard F','Guard ARPU','Плюс и безопасно','Условия Ozon']);
const comparisonFields=['scenario_name','hypothesis','cr0','delta_pp','relative_cr','delta_buyers','target_users','cart_cr0','cart_cr1','fav_cr0','fav_cr1','arpu0','arpu1','arpu_index1','guard_c','guard_f','guard_arpu','positive_and_safe','ozon_calibrated'];
const compValue=(r,key)=>typeof r[key]==='boolean'?(r[key]?'Да':'Нет'):r[key];
results.forEach((x,i)=>row('Сравнение',19+i,comparisonFields.map(k=>compValue(x,k))));
ss.Сравнение.getRange('A:A').format.columnWidth=42;ss.Сравнение.getRange('B:B').format.columnWidth=32;
for(const a of ['C19:C'+(18+results.length),'E19:E'+(18+results.length),'H19:K'+(18+results.length)])pct('Сравнение',a);
ss.Сравнение.getRange('D19:D'+(18+results.length)).setNumberFormat('0.0000');ss.Сравнение.getRange('F19:G'+(18+results.length)).setNumberFormat('#,##0.0');
ss.Сравнение.getRange('L19:N'+(18+results.length)).setNumberFormat('0.0000');
ss.Сравнение.getRange('O19:R'+(18+results.length)).conditionalFormats.add('containsText',{text:'Нет',format:{fill:'#FCE0DC',font:{color:'#A1281E'}}});

const stock=JSON.parse(await fs.readFile(root+'/data/cart_stock_distributions.json','utf8'));
const crosses=(await fs.readFile(root+'/results/h1_h4_crossover.csv','utf8')).replace(/^\uFEFF/,'').trim().split(/\r?\n/).map(x=>x.split(','));
title('Размеры Корзин','Размеры Корзин · построенные примеры, не измерения','H',45);
head('Размеры Корзин',5,['Сценарий','Доля 40+','Среднее','Медиана','Максимум','Среднее среди 40+','SKU','Пользователей']);
let sr=6;for(const d of stock.distributions)for(const bin of d.histogram)row('Размеры Корзин',sr++,[d.id,d.large_share,d.mean,d.median,d.maximum,d.large_conditional_mean,bin.sku,bin.users]);
pct('Размеры Корзин','B6:B35');
row('Размеры Корзин',36,['Нижняя необходимая граница',stock.bounds.lower_necessary]);row('Размеры Корзин',37,['Верхняя необходимая граница',.5]);pct('Размеры Корзин','B36:B37');
v('Размеры Корзин','A39','E[X] ≤ 0,5×24 +(0,5−p)×39 +300p. Отсюда p≥19/174; медиана даёт p≤0,5. Не доверительный интервал.');
ss['Размеры Корзин'].getRange('A39:H41').merge();ss['Размеры Корзин'].getRange('A39').format={wrapText:true,rowHeight:60};
title('Порог H1 H4','Порог победы H1 · прочие допущения фиксированы','G',70);
f('Порог H1 H4','B3',"='Версия срезов'!G2");
head('Порог H1 H4',5,['Потребность H1 среди 40+','Global CR','Охват H4 ×','Порог доли 40+','В границах кейса','H1−H4 при 50%, п.п.']);
for(let i=1;i<crosses.length;i++){const x=crosses[i];row('Порог H1 H4',5+i,[Number(x[0]),Number(x[1]),Number(x[2]),x[3]?Number(x[3]):'Нет пересечения',x[4]==='True'?'Да':'Нет',Number(x[5])]);}
pct('Порог H1 H4','A6:B65');pct('Порог H1 H4','D6:D65');
for(const n of ['Размеры Корзин','Порог H1 H4'])ss[n].getRange('A:A').format.columnWidth=35;
// Capture control observes current driver values to warn when saved multi-case results are stale.
title('Версия срезов','Версия сохранённых сравнений · контроль обновления','G',1000);
head('Версия срезов',5,['Лист','Ячейка','Сохранённый ввод','Текущий ввод','Совпадает']);
const capture=[];
for(const [n,range] of [['Параметры','B10:B10'],['Параметры','C15:E21'],['Входы H','C5:H36'],['Входы H','N5:Q'+(4+4*N)],['Входы H','R5:S'+(4+4*N)],['Исходные','B5:B24'],['Масштаб','B6:B13'],['Сценарии','D6:AC'+(N+5)]]){
 const [a,b]=range.split(':');const startCol=a.match(/[A-Z]+/)[0];const startRow=Number(a.match(/\d+/)[0]);const vals=ss[n].getRange(range).values;
 const colnum=s=>s.split('').reduce((a,x)=>a*26+x.charCodeAt(0)-64,0);const base=colnum(startCol);
 for(let r=0;r<vals.length;r++)for(let c=0;c<vals[r].length;c++)if(typeof vals[r][c]==='number')capture.push({sheet:n,address:col(base+c)+(startRow+r),value:vals[r][c]});
}
for(let i=0;i<capture.length;i++){const r=6+i,x=capture[i];row('Версия срезов',r,[x.sheet,x.address,x.value,null,null]);f('Версия срезов','D'+r,`='${x.sheet}'!${x.address}`);f('Версия срезов','E'+r,`=IF(C${r}=D${r},1,0)`);}
v('Версия срезов','F2','Статус');f('Версия срезов','G2',`=IF(SUM(E6:E${5+capture.length})=${capture.length},"Актуально","Срезы устарели: запустите Python")`);
ss['Версия срезов'].getRange('A:A').format.columnWidth=28;ss['Версия срезов'].getRange('G:G').format.columnWidth=45;
v('Методика','A30','Обновление 2026-10-29');v('Методика','B30','Исходные 45 проверок сохранены. Сценарии размеров Корзины; Taobao — отдельные добавления за окно; масштаб DAU/MAU из Ozon IR. Сравнение сохраняет срезы и предупреждает об изменении входов. ARPU — условный индекс. +10% остаётся общим стрессом.');
ss.Методика.getRange('B30').format={wrapText:true,rowHeight:100};

// Retain and rerun the original test suite using the same workbook, then restore every input/formula.
wb.recalculate();
const mutated=[['Параметры','B3'],['Параметры','B4'],['Параметры','B5'],['Параметры','C15'],['Параметры','D15'],['Гипотезы','D5'],['Гипотезы','E5']];
for(let r=5;r<=8;r++)for(let c=3;c<=7;c++)mutated.push(['Воздействие',col(c)+r]);
const snapshots=mutated.map(([n,a])=>({n,a,formula:ss[n].getRange(a).formulas[0][0],value:read(n,a)}));
let originalTests;
try{v('Параметры','B3',2);wb.recalculate();originalTests=legacy45(wb,ss);}finally{for(const x of snapshots)if(x.formula?.startsWith('='))f(x.n,x.a,x.formula);else v(x.n,x.a,x.value);wb.recalculate();}
const parity=[];
for(let i=0;i<N;i++){
 v('Параметры','B3',i+1);wb.recalculate();
 for(let h=0;h<8;h++){
  const r=outrows[h],expected=results.find(x=>x.scenario===cases[i].id&&x.hypothesis===input.hypotheses[h].id);
  if(read('Расчёт','S'+(140+h))!==1)throw Error('Invalid workbook scenario '+cases[i].id);
  for(const [address,key,tol] of [['F'+r,'delta_pp',1e-9],['E'+r,'delta_buyers',1e-5]])if(Math.abs(read('Итоги',address)-expected[key])>tol)throw Error(`Parity failed ${cases[i].id} ${expected.hypothesis} ${key}`);
  const rr=24+h;
  for(const [c,key] of [['B','cr0'],['D','cart_cr0'],['E','cart_cr1'],['F','fav_cr0'],['G','fav_cr1'],['H','arpu0'],['I','arpu1']])if(Math.abs(read('Итоги',c+rr)-expected[key])>1e-8)throw Error(`Metric parity failed ${cases[i].id} ${key}`);
 }
 parity.push(cases[i].id);
}
v('Параметры','B3',6);wb.recalculate();
if(read('Сравнение','B3')!=='Актуально')throw Error('Saved comparison initially stale');
const reachSaved=read('Входы H','C6');v('Входы H','C6',reachSaved+.01);wb.recalculate();if(read('Сравнение','B3')==='Актуально')throw Error('Stale comparison not detected');v('Входы H','C6',reachSaved);wb.recalculate();
const errors=(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:40},maxChars:3000})).ndjson;
await fs.writeFile(root+'/results/excel_verification.json',JSON.stringify({original_tests:originalTests,scenario_parity:parity,stale_warning_verified:true,formula_error_scan:errors,engine:'Artifact Tool; not native Excel'},null,2));
await fs.writeFile(root+'/data/workbook_map.json',JSON.stringify({caseRows,scenarioFields,comparisonFields,comparisonFirstRow:19,topCases,capture:capture.map((x,i)=>({...x,row:6+i})),activeScenario:6,scenarioCount:N,weightsFirstRow:5},null,2));
await fs.mkdir(root+'/.tmp',{recursive:true});
for(const [n,range] of [['Итоги','A2:K16'],['Сценарии','A2:M12'],['Входы H','A2:I10'],['Сравнение','A2:J14'],['Taobao','A2:H19'],['Источники','A2:F9'],['Масштаб','A2:E26'],['Версия срезов','A2:G10'],['Размеры Корзин','A2:H20'],['Порог H1 H4','A2:F20']]){
 const im=await wb.render({sheetName:n,range,scale:1.2,format:'png'});await fs.writeFile(root+'/.tmp/'+n+'.png',new Uint8Array(await im.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(root+'/models/Ozon_модель_кейса.xlsx');
console.log(JSON.stringify({original_tests:originalTests.length,scenarios_verified:parity.length,errors,active:cases[5].name}));
