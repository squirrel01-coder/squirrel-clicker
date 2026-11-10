# 3D-модели и рендеры домов в облаке

## Фотореалистичный рендер (главное)
```bash
# 1) ассеты Poly Haven (CC0, можно в коммерческой работе), ~800 МБ, один раз за сессию
python3 3d-render/ph_get.py ~/assets hdri:evening_road_01_puresky:4k \
  tex:white_stucco:2k tex:grey_plaster:2k tex:corrugated_iron_02:2k tex:checkered_pavement_tiles:2k \
  tex:concrete_pavement:2k tex:asphalt_02:2k tex:rough_concrete:2k tex:aerial_grass_rock:2k \
  model:island_tree_01:2k model:island_tree_02:2k model:island_tree_03:2k model:tree_small_02:2k \
  model:shrub_01:2k model:shrub_02:2k model:shrub_04:2k
~/bpyenv/bin/pip install pillow numpy
# 2) рендер: test — быстрые 900×600, final — 1800×1200
SKY_ROT=-53 SUN_E=8 SUN_EL=9 SKY_STR=0.7 SAT=1.12 \
  ~/bpyenv/bin/python 3d-render/realism.py <скрипт_модели.py> <папка_с_geom.py> ~/assets <вывод> final all
# 3) PDF как в образце офиса (A4, вид на лист)
python3 3d-render/render_pdf.py <вывод>/RENDER "RENDER KO'RINISHI.pdf"
```
Уровень — по образцу офиса «Qirqizobod 22-uy» (6 видов, вечер, тёплые окна, плитка-шахматка, лаванда).
Виды: 1_ayvon, 2_old, 3_yon, 4_hovli, 5_orqa, 6_tepa. Финальный вид ≈ 5–7 мин на 4 ядрах.


Blender работает здесь без окна, как модуль Python (`bpy`, версия 5.3). Ноутбук для этого не нужен.

## Порядок работы
1. На компьютере Claude делает чертежи в AutoCAD.
2. Пользователь присылает в облачный чат:
   - **файл размеров дома** (`geom.py`; из него строятся и чертежи, и 3D) — главный файл;
   - PDF комплекта и DWG/DXF — для сверки.
3. В облаке модель собирается скриптом по этим размерам и рендерится в Cycles.
4. Обратно отдаются PNG-виды и PDF «Render ko'rinishi».

## Установка (один раз за сессию, ~1 мин)
```bash
python3 -m venv ~/bpyenv && ~/bpyenv/bin/pip install bpy
```

## Запуск
```bash
~/bpyenv/bin/python 3d-render/run_bpy.py <скрипт.py> <папка_с_geom.py> <папка_вывода> test|final [виды]
```
Пример: `... run_bpy.py 3d-render/primer_namuna/blender_uy.py 3d-render/primer_namuna /tmp/out test front,aerial`

Скорость на облачной машине (4 ядра): пробный кадр 800×500 — около 25 с.

## Пример
`primer_namuna/` — учебный дом NAMUNA 7-UY, ранняя версия скрипта из чата на компьютере
(оси ещё до исправления: позже 3-я ось стала 9000, 4-я — 11600, 5-я — 15000).

## Выгрузка для 3ds Max (главный результат для проверяющего)
```bash
~/bpyenv/bin/python 3d-render/export_max.py <скрипт_модели.py> <папка_с_geom.py> <папка_вывода> <ИмяФайла>
~/bpyenv/bin/python 3d-render/check_fbx.py <файл.fbx>   # повторно открыть FBX и сверить габариты
```
FBX: детали одного вида объединены, группы UY / HOVLI / O'SIMLIKLAR / ATROF, UV кубом (1 = 1 м),
0,0,0 = оси 1/А на ±0.000. Памятку для проверяющего (PROCHITAT.txt) класть в архив рядом с FBX.
