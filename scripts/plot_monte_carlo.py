"""Export standalone presentation figures from saved Monte Carlo summaries."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
NAMES={'H1':'H1  Поиск в корзине','H2':'H2  Сохранение SKU','H3':'H3  Купить сейчас / На потом',
       'H4':'H4  Сквозной поиск','H5':'H5  Покупка из избранного','H6.1':'H6  Три альтернативы'}
BLUE='#3568D4';PURPLE='#8B5DB5';ORANGE='#DB9242';INK='#172B45';MUTED='#596D83';GRID='#E4EAF1'
PROFILE_NAMES={'triangular':'Треугольные','uniform':'Равномерные','low_effect':'Низкая мода эффекта'}


def csv_rows(path):
    with path.open(encoding='utf-8-sig') as stream:return list(csv.DictReader(stream))


def frame(title,subtitle):
    fig,ax=plt.subplots(figsize=(16,9),dpi=120)
    fig.patch.set_facecolor('white');ax.set_facecolor('white')
    fig.suptitle(title,x=.075,y=.955,ha='left',fontsize=23,fontweight='bold',color=INK)
    fig.text(.075,.895,subtitle,fontsize=12,color=MUTED)
    fig.text(.075,.035,'Сценарные допущения, не результаты A/B-теста. Диапазоны симуляций — не доверительные интервалы.',fontsize=10,color=MUTED)
    for spine in ax.spines.values():spine.set_visible(False)
    ax.tick_params(colors=INK,labelsize=12,length=0)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=.29,right=.85,top=.79,bottom=.16)
    return fig,ax


def save(fig,path):
    fig.savefig(path.with_suffix('.png'),dpi=150,facecolor='white')
    fig.savefig(path.with_suffix('.svg'),facecolor='white')
    plt.close(fig)


def label_factor(name):
    common={'large_share':'Доля больших корзин','fav_large_share':'Доля большого избранного',
            'global_cr':'Базовая CR','overlap':'Пересечение посещений','h1_need':'Потребность в H1'}
    if name in common:return common[name]
    hid,key=name.rsplit('.',1)
    labels={'uplift':'Сила эффекта','reach_multiplier':'Охват','behavior_penalty':'Поведенческий штраф',
            'product_penalty':'Продуктовый штраф','loss_c':'Потери CR корзины','loss_f':'Потери CR избранного','income_delta':'Изменение дохода'}
    return labels[key]+' · '+hid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results/monte_carlo')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/monte_carlo')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    runs=json.loads((args.input/'profiles.json').read_text(encoding='utf8'))
    base=next(r for r in runs if r['profile']=='triangular');n=base['draws']
    rows=sorted(base['hypotheses'],key=lambda x:-x['median_delta_pp'])
    y=np.arange(len(rows))
    count=f'{n:,}'.replace(',',' ')
    fig,ax=frame('H4 и H2 лидируют, но их сценарные диапазоны широки',
        f'{count} допустимых комбинаций входов · треугольные распределения · точки — медианы, отрезки — P2,5–P97,5')
    lo=np.array([r['p025_delta_pp'] for r in rows]);hi=np.array([r['p975_delta_pp'] for r in rows]);mid=np.array([r['median_delta_pp'] for r in rows])
    ax.hlines(y,lo,hi,color=BLUE,lw=6,alpha=.28)
    ax.scatter(mid,y,color=BLUE,s=90,zorder=3)
    ax.axvline(0,color=MUTED,lw=1,ls='--')
    ax.set_yticks(y,[NAMES[r['hypothesis']] for r in rows]);ax.invert_yaxis()
    ax.set_xlabel('Изменение глобальной конверсии, процентные пункты',fontsize=12,labelpad=16,color=INK)
    ax.grid(axis='x',color=GRID)
    for k,r in enumerate(rows):
        ax.annotate(f"{r['median_delta_pp']:+.3f}",(mid[k],k),xytext=(0,13),textcoords='offset points',ha='center',fontsize=11,color=INK)
        share='<0,1%' if 0<r['top_share']<.001 else f"{r['top_share']:.1%}"
        ax.text(1.03,k,share,transform=ax.get_yaxis_transform(),va='center',fontsize=13,color=INK)
    ax.text(1.03,1.08,'Первое место\nв симуляциях',transform=ax.transAxes,fontsize=11,color=MUTED)
    save(fig,args.output/'01_effect_ranges')

    margin=csv_rows(args.input/'triangular/sensitivity_margin.csv')
    margin=sorted(margin,key=lambda r:-abs(float(r['spearman_rho'])))[:10]
    fig,ax=frame('Что сильнее всего меняет преимущество H4 над H2',
        'Скрининг чувствительности: ранговая корреляция Спирмена с разницей эффектов H4 − H2')
    fig.subplots_adjust(bottom=.22)
    rho=np.array([float(r['spearman_rho']) for r in margin]);yy=np.arange(len(margin))
    ax.barh(yy,rho,color=[BLUE if v>=0 else ORANGE for v in rho],height=.62)
    ax.axvline(0,color=MUTED,lw=1);ax.set_yticks(yy,[label_factor(r['factor']) for r in margin]);ax.invert_yaxis()
    ax.set_xlim(-1,1);ax.grid(axis='x',color=GRID)
    ax.set_xlabel('ρ Спирмена · слева усиливается H2, справа — H4',fontsize=12,labelpad=16,color=INK)
    for i,v in enumerate(rho):ax.text(v+(.025 if v>=0 else -.025),i,f'{v:+.2f}',va='center',ha='left' if v>=0 else 'right',fontsize=11,color=INK)
    fig.text(.29,.095,'Ассоциации внутри выбранной модели; не причинные эффекты и не индексы Соболя.',fontsize=10,color=MUTED)
    save(fig,args.output/'02_sensitivity_margin')

    fig,ax=frame('Первое место зависит от выбранных распределений',
        f'Три профиля предположений · {n:,} допустимых комбинаций в каждом · одинаковые ограничения кейса'.replace(',',' '))
    order=[r['hypothesis'] for r in rows];yy=np.arange(len(order));colors=[BLUE,PURPLE,ORANGE]
    for i,run in enumerate(runs):
        by_id={r['hypothesis']:r for r in run['hypotheses']}
        values=np.array([by_id[h]['top_share']*100 for h in order]);pos=yy+(i-1)*.23
        ax.barh(pos,values,height=.20,color=colors[i],label=PROFILE_NAMES[run['profile']])
        for p,v in zip(pos,values):
            if v>=1:ax.text(v+.6,p,f'{v:.1f}%',va='center',fontsize=10,color=INK)
    ax.set_yticks(yy,[NAMES[h] for h in order]);ax.invert_yaxis();ax.grid(axis='x',color=GRID)
    ax.set_xlim(0,max(r['top_share']*100 for run in runs for r in run['hypotheses'])*1.18)
    ax.set_xlabel('Доля симуляций с первым местом, % — не вероятность успеха в продукте',fontsize=12,labelpad=16,color=INK)
    ax.legend(loc='lower right',frameon=False,fontsize=10)
    save(fig,args.output/'03_prior_robustness')

    convergence=csv_rows(args.input/'triangular/convergence.csv')
    fig,ax=frame('Проверка численной устойчивости симуляции',
        'Частота первого места H4 и H2 при увеличении числа допустимых комбинаций входов')
    fig.subplots_adjust(left=.12,right=.90,bottom=.22)
    for hid,color in [('H4',BLUE),('H2',PURPLE)]:
        rr=[r for r in convergence if r['hypothesis']==hid]
        ax.plot([int(r['draws']) for r in rr],[100*float(r['top_share']) for r in rr],marker='o',lw=2.5,color=color,label=hid)
    ax.set_xscale('log');ax.grid(color=GRID);ax.legend(frameon=False,fontsize=13)
    ax.set_xlabel('Количество симуляций',fontsize=12,labelpad=16,color=INK);ax.set_ylabel('Первое место, %',fontsize=12,color=INK)
    fig.text(.12,.095,'Сходимость подтверждает точность интегрирования при заданных допущениях, а не истинность самих допущений.',fontsize=10,color=MUTED)
    save(fig,args.output/'04_convergence')

    report=['# Монте-Карло для защиты кейса Ozon','',
        f'Выполнено {n:,} допустимых симуляций на каждый из {len(runs)} профилей; всего {n*len(runs):,}. Seed {base["seed"]}.',
        '', 'Все распределения входов — открыто заданные экспертные допущения. Это анализ устойчивости решения, не оценка причинного эффекта по эксперименту.',
        '', '| H | Медиана ΔCR, п.п. | P2,5–P97,5 | Первое место | Положительный эффект и все прокси защитных метрик |',
        '|---|---:|---:|---:|---:|']
    for r in rows:report.append(f"| {r['hypothesis']} | {r['median_delta_pp']:+.4f} | {r['p025_delta_pp']:+.4f}…{r['p975_delta_pp']:+.4f} | {r['top_share']:.2%} | {r['positive_and_safe_share']:.2%} |")
    report+=['','## Что сказать за 40 секунд','',
        'Мы расширили детерминированный расчёт анализом Монте-Карло. Для неизвестных охватов, силы эффекта и рисков задали явные диапазоны и распределения. В каждой симуляции все гипотезы сравниваются на одной и той же аудитории, с сохранением ограничений кейса. Мы проверили три семейства допущений, диапазоны эффекта, частоту лидерства и нарушения защитных метрик. Ранговая чувствительность показывает, какие неизвестные сильнее всего меняют выбор. Полученные доли и интервалы относятся к симуляциям: это не экспериментальные вероятности и не доверительные интервалы реального эффекта.',
        '', '## Выводы по рассчитанным профилям','']
    for run in runs:
        best=sorted(run['hypotheses'],key=lambda r:-r['top_share'])[:2]
        report.append(f"- {PROFILE_NAMES[run['profile']]}: {best[0]['hypothesis']} {best[0]['top_share']:.2%}, {best[1]['hypothesis']} {best[1]['top_share']:.2%} первых мест. Принято {run['sampling']['acceptance_rate']:.3%} сгенерированных комбинаций.")
    report+=['','## Ответы на возможные вопросы','',
        '- Почему 100 000? Проверяем сходимость на 1 000/10 000/50 000/100 000 и сохраняем численную стандартную ошибку частоты лидерства. Большое число прогонов не создаёт новых наблюдений.',
        '- Откуда распределения? Из открыто указанных диапазонов и экспертных допущений. Они не восстановлены по Ozon и должны уточняться данными или консультацией.',
        '- Это доверительные интервалы? Нет, это центральные 95%-е диапазоны условного распределения результатов симуляции.',
        '- Можно гарантировать защитные метрики? Нет. Мы показываем частоту нарушений в модели. Определения атрибуции локальных конверсий ещё требуют согласования с Ozon.',
        '- Почему не Хольт—Уинтерс? Нет временного ряда с сезонностью; наша задача — сравнить продуктовые изменения.',
        '- Почему не считаем H6 три раза? В исходной модели у вариантов одинаковые входы. Три копии искусственно изменили бы частоты лидерства.',
        '', '## Воспроизведение','',
        'python -m pip install -r requirements-plots.txt\npython scripts/run_monte_carlo.py\npython scripts/plot_monte_carlo.py',
        '', 'JSON/CSV с seed, контрольными суммами входов, принятыми распределениями, попарным сравнением и сходимостью: results/monte_carlo/. Исходная Excel-модель не изменялась.']
    (args.output/'presentation-notes.md').write_text('\n'.join(report)+'\n',encoding='utf8')
    print(args.output)


if __name__=='__main__':main()
