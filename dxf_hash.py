import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf, layout, config
from ezdxf.enums import TextEntityAlignment
import numpy as np
import hashlib
from hashlib import blake2b
import pathlib
import csv
import re
import requests
import socket



# False - все отверстия соответствуют набору матриц
# True - есть отверстия не соответствующие набору матриц
def has_bad_diams(set_list):
    true_diameters = [11, 9 ,6.5 ,1 ,13 ,25 ,3.5 ,5, 18]
    for el in set_list:
        if float(el) in true_diameters:
            continue
        else:
            return True
    return False

# Возвращает ширину и высоту граничной рамки
def get_bounding_box(msp):
    cache = bbox.Cache()
    # get overall bounding box
    first_bbox = bbox.extents(msp, cache=cache)
    min = ezdxf.math.BoundingBox2d(first_bbox).extmin
    max = ezdxf.math.BoundingBox2d(first_bbox).extmax
    width = max[0] - min[0]
    height = max[1] - min[1]
    return (round(width, 1), round(height, 1))

# Возвращает список имен dxf файлов в каталоге
def get_dxf_files(path):
    # определение пути
    currentDirectory = pathlib.Path(path)
    #print(currentDirectory)
    dxf_files = []
    for currentFile in currentDirectory.iterdir():  
        name = str(currentFile)
        if name[-4::1].lower() == '.dxf':
            dxf_files.append(name)
    return dxf_files

# Сохранить параметры DXF в таблицу
def save_bom_to_csv(path, bom):    
    set_columns = set()
    for d in bom:
        for key in d:
            set_columns.add(key)

    for d in bom:
        for column in set_columns:
            if not column in d:
                d[column] = None

    # Получаем набор заголовков
    columns = set(i for d in bom for i in d)
    # {'active', 'color', 'cost', 'count', 'size'}

    path = path / 'out.csv'
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter=';')
        writer.writeheader() # Пишем заголовок
        for row in bom:
            writer.writerow(row) 


def color_set(set_list):
    true_diameters = [11, 9 ,6.5 ,1 ,13 ,25 ,3.5 ,5, 18]
    string = ''
    for el in set_list:
        if float(el) in true_diameters:
            string = string + str(el)
        else:
            #el = f" {el} "
            #string = string + "\033[1m\033[30m\033[47m{}\033[0m".format(str(el))
            string = string + str(el)
        string = string + ", "
    return string[:-2]

def print_diams(dic):
    data = []
    for el, d in dic.items():
        circles = set()
        arcs = set()
        for key, val in d.items():            
            if key == 'circles':
                circles = val
            if key == 'arcs':
                arcs = val
        data.append([el,color_set(circles),color_set(arcs)])

    columns = ['Имя файла', 'Отверстия', 'Дуги']
    # расчёт максимальной длинны колонок
    max_columns = [] # список максимальной длинны колонок
    for col in zip(*data):
        len_el = []
        [len_el.append(len(el)) for el in col]  
        max_columns.append(max(len_el))
    # вывод таблицы с колонками максимальной длинны строки каждого столбца

    # печать шапки таблицы
    for n, column in enumerate(columns):
        print(f'{column:{max_columns[n]+5}}', end='')
    print()

    # печать разделителя шапки '='
    r = f'{"="*sum(max_columns)+"="*15}'
    print(r[:-1])

    # печать тела таблицы
    for el in data:
        for n, col in enumerate(el):
            print(f'{col:{max_columns[n]+5}}', end='') # выравнвание по правому краю >
        print()

# Устанавить цвет для элемента по слою
def color(msp):
    for el in msp.query("*"):        
        el.dxf.color = -1   

# Получить сумму чисел в списке и округлить до сотых
def rounded_sum_from_list(list):
    rounded_list = np.around(list, decimals=2)
    sum = round(np.sum(rounded_list), 2)
    return float(sum)

# Получить хэш для dxf файла
def get_dxf_hash(dxf_file_name):
    if pathlib.WindowsPath(dxf_file_name).is_file() == False:
        return "НЕТ ФАЙЛА", "НЕТ ФАЙЛА", "НЕТ ФАЙЛА", False, False, 0, 0
    all_geometry = {
        "arcs" : [],
        "circles" : [],
        "lines" : []
    }
    circles = set()
    arcs = set()
    # Открываю dxf
    doc = ezdxf.readfile(dxf_file_name)
    # Меняю версию документа на AutoCAD R2000. А то почему-то цвета линий не менялись
    doc.dxfversion = "AC1015"
    # Получаю пространство модели
    msp = doc.modelspace() 
    # Прохожу циклом по каждому элементу
    for el in msp.query("*"):
        # Меняю цвет элемента на "По слою"
        el.dxf.color = -1
        # Если элемент - линия
        if el.dxftype()=="LINE":
            x1, y1, _ = el.dxf.start
            x2, y2, _ = el.dxf.end
            all_geometry["lines"].append(rounded_sum_from_list([x1, y1, x2, y2]))
        # Если элемент - круг
        if el.dxftype()=="CIRCLE":
            #Добавляю его диаметр в список
            x1, y1, _ = el.dxf.center
            r = el.dxf.radius
            all_geometry["circles"].append(rounded_sum_from_list([x1, y1, r])) 
            circles.add(round(el.dxf.radius, 2)*2)          
        # Если элемент - дуга
        if el.dxftype()=="ARC":
            #Добавляю его диаметр в список
            x1, y1, _ = el.dxf.center
            r = el.dxf.radius
            start_angle = el.dxf.start_angle
            end_angle = el.dxf.end_angle
            all_geometry["arcs"].append(rounded_sum_from_list([x1, y1, r, start_angle, end_angle]))
            arcs.add(round(el.dxf.radius, 2)*2)
    doc.save()
    sorted_list = sorted(all_geometry["arcs"]) + sorted(all_geometry["circles"]) + sorted(all_geometry["lines"])
    sorted_coordinates_string = ';'.join(str(el) for el in sorted_list)
    
    md5_hash = hashlib.md5(sorted_coordinates_string.encode()).hexdigest()
    width, height = get_bounding_box(msp)
    #print(dxf_file_name)
    #print(str(md5_hash) + str(circles) + str(arcs) + str(has_bad_diams(circles)) + str(has_bad_diams(arcs)) + str(width) + ' x ' + str(height))
    
    #export_white_bg(dxf_file_name, width, height)
    
    return (md5_hash, circles, arcs, has_bad_diams(circles), has_bad_diams(arcs), width, height)
    

def export_white_bg(dxf_file_name, width='0', height='0', quantity='_', some_text=''):
    # Открываю dxf
    doc = ezdxf.readfile(dxf_file_name)
    # Меняю версию документа на AutoCAD R2000. А то почему-то цвета линий не менялись
    doc.dxfversion = "AC1015"
    # Получаю пространство модели
    msp = doc.modelspace()
    # Добавить габариты
    # Use method set_placement() to define the TEXT alignment, because the
    # relations between the DXF attributes 'halign', 'valign', 'insert' and
    # 'align_point' are tricky.
    '''print(f"{str(width)}x{str(height)}")
    msp.add_text(f"{width}x{height}").set_placement(
        (2, 30),
        align=TextEntityAlignment.MIDDLE_RIGHT
    )'''

    added_string = f"{width}x{height}  {quantity}шт"
    if some_text != '':
        #added_string = f"{width}x{height}  {quantity}шт\n{some_text}"
        msp.add_text(
        some_text,
        height=50,
        dxfattribs={"style": "LiberationSerif"}
        ).set_placement((2, -55), align=TextEntityAlignment.LEFT)
    
    # Using a predefined text style:
    msp.add_text(
        added_string,
        height=50,
        dxfattribs={"style": "LiberationSerif"}
    ).set_placement((2, 6), align=TextEntityAlignment.LEFT)
    # 1. create the render context
    context = RenderContext(doc)
    # 2. create the backend
    backend = pymupdf.PyMuPdfBackend()
    # 3. create and configure the frontend
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
    frontend = Frontend(context, backend, config=cfg)
    # 4. draw the modelspace
    frontend.draw_layout(msp)
    # 5. create an A4 page layout
    page = layout.Page(210, 297, layout.Units.mm, margins=layout.Margins.all(20))
    
    
    # 6. get the PDF rendering as bytes
    pdf_bytes = backend.get_pdf_bytes(page)
    
    current_dir = dxf_file_name.parents[0] / 'pdf'
    pathlib.Path(current_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{current_dir}/{dxf_file_name.stem}_{quantity}шт.pdf", "wb") as fp:
        fp.write(pdf_bytes)

def main():
    print('Author: Aleksandr Podgaynyy')
    print('aleksandr@podgaynyy.ru\n\n')
    

    username = 'sibes'
    hostnsme = socket.gethostname()
    res = requests.get(f'https://api.ipify.org')
    my_ip = res.text
    res = requests.get(f'https://script.google.com/macros/s/AKfycbzTh0kfUv2dQIzAnwpYkxGdbOK6Z4TYivAOshhG0x_25jUQ2qFZ439OvfdJrkIFy9x3/exec?username={username}&hostname={hostnsme}&my_ip={my_ip}&script=dxfHashReader')
    if res.text.strip().split('_')[1] != 'ok':
        print(f'Балланс вашего аккаунта = {res.text.strip().split('_')[0]} р. Для работы со скриптом пополните балланс. aleksandr@podgaynyy.ru')
        input()
        exit()
    
    path_dir = input("Введите путь к директории с dxf файлами\n")
    files_list = get_dxf_files(path_dir)
    
    bom = []
    dict_names_len = 1
    
    for dxf_file_name in files_list:
        dxf_hash, circles, arcs, is_bad_circles, is_bad_arcs, bb_width, bb_height = get_dxf_hash(dxf_file_name)
        export_white_bg(pathlib.Path(dxf_file_name), bb_width, bb_height, '.', pathlib.Path(dxf_file_name).name[:-4])
        
        obj = {
            'Длина': re.sub(r'\.', ',', str(bb_height)),
            'Ширина': re.sub(r'\.', ',', str(bb_width)),
            'ХЭШ': dxf_hash,
            'Окружности': circles, 
            'Неверные окружности': is_bad_circles,
            'Дуги': arcs,
            'Неверные дуги': is_bad_arcs
            }

        dict_name = pathlib.Path(dxf_file_name).name[:-4].split('_')
        if len(dict_name) > dict_names_len:
            dict_names_len = len(dict_name)
        for i, el in enumerate(dict_name):
            #obj[i] = el
            if i == 0:
                obj['Обозначение'] = f"\'{el}"
            if i == 1:
                obj['Материал'] = el
            if i == 2:                     
                el = re.search(r'^[-+]?[0-9]*[.,]?[0-9]+(?:[eE][-+]?[0-9]+)?', re.sub(r'\.', ',', el))[0]
                obj['Толщина'] = el
            if i == 3:
                el = re.search(r'[0-9]+', el)[0]
                obj['Количество'] = el
        if obj['Материал'] == 'ст3' or obj['Материал'] == 'оц':
            mass = float(re.sub(r'\,', '.', obj['Толщина'])) * float(re.sub(r'\,', '.', obj['Ширина'])) * float(re.sub(r'\,', '.', obj['Длина'])) * int(obj['Количество']) * 7800 / 1000000000
            obj['Масса общая'] = re.sub(r'\.', ',', str(mass))
            
        bom.append(obj)
        
        print(dxf_hash + " is HASH of " + dxf_file_name)
        print('circles: ' + str(circles))
        print('arcs: ' + str(arcs))
        if is_bad_circles:
            print('ПРОВЕРЬ ДИАМЕТРЫ, ЧОРТ!!!')
        if is_bad_arcs:
            print('Проверьте диаметры дуг')
        print('bb_width: ' + str(bb_width))
        print('bb_height: ' + str(bb_height))
    
    save_bom_to_csv(pathlib.Path(path_dir), bom)
    input("DONE!")
           

if __name__ == "__main__":
    main()