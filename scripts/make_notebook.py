"""Package the same tested aggregator as a standalone Colab notebook."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def code(s):return dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=s.splitlines(True))
def md(s):return dict(cell_type='markdown',metadata={},source=s.splitlines(True))
cells=[md('# Taobao → отдельный анализ событий добавления\n\nИспользует уже существующий агрегат в Drive. Полный архив обрабатывается только при отсутствии агрегата или явном REBUILD=True. Распределение Taobao НЕ задаёт размеры Корзин Ozon и охват H1. Уникальные добавления не являются остатками списков; покупки за окно не являются дневной CR Ozon.\n'),
       code('from google.colab import drive\ndrive.mount("/content/drive")\n'),
       code('from pathlib import Path\nARCHIVE=Path("/content/drive/MyDrive/UserBehavior.csv (1).zip")\nUSERS=Path("/content/drive/MyDrive/taobao_users.csv")\nOUT=Path("/content/drive/MyDrive/ozon-taobao-results")\nREBUILD=False\nOUT.mkdir(exist_ok=True)\n'),
       md('## Тот же код, что в src/taobao.py\n\nSQLite удаляет повторы между чанками, включая повторное добавление одного SKU. Временная база размещается на диске Colab, не в Drive. Полный прогон фиксирует timestamp-границы и выбросы; автоматической фильтрации дат нет, чтобы не менять прежнюю выборку молча.\n'),
       code((ROOT/'src/taobao.py').read_text(encoding='utf-8')),
       code('if REBUILD or not USERS.exists():\n    if not ARCHIVE.exists():\n        raise FileNotFoundError("Архив не найден по указанному пути Drive")\n    metadata=aggregate_events(ARCHIVE,USERS)\n    print(metadata)\nelse:\n    print("Используем уже рассчитанный агрегат:",USERS)\nsummary=summarize(USERS)\n(OUT/"taobao_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")\ndisplay(pd.DataFrame(summary["cohorts"]))\n'),
       code('rows=[]\nfor t in summary["thresholds"]:\n    for c in t["cohorts"]:\n        rows.append({"quantile":t["quantile"],"cart_threshold":t["cart_threshold"],"fav_threshold":t["fav_threshold"],**c})\npd.DataFrame(rows).to_csv(OUT/"taobao_cohorts.csv",index=False)\nprint("Сводки сохранены:",OUT)\n'),
       md('## Обновление GitHub и Excel\n\nСкачайте из ozon-taobao-results только taobao_summary.json и taobao_cohorts.csv. Это обновляет только анализ событий Taobao, а не когорты или охваты Ozon. Замените соответствующие файлы data/ в репозитории и запустите `python scripts/run.py`, затем `python -m unittest discover -s tests -v`. Исходный архив и taobao_users.csv загружать в GitHub не нужно. Если Codex читает ваш Drive, достаточно сообщить, что сводки обновлены: архив повторно передавать не требуется.\n')]
notebook=dict(cells=cells,metadata={'colab':{'name':'taobao_reproducible.ipynb'},'kernelspec':{'name':'python3','display_name':'Python 3'}},nbformat=4,nbformat_minor=5)
(ROOT/'notebooks/taobao_reproducible.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
print('Standalone Colab notebook saved')
