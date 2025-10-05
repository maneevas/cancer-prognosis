from pathlib import Path
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage, Frame
from tkinter import ttk
from owlready2 import *
import ctypes
from datetime import datetime
from uuid import uuid4
import os
import logging

onto = get_ontology("D:/Univer/4kurs/diplom/hemopro1/hemopro22.owl").load()
print("Онтология успешно загружена:", onto.base_iri)


def find_patient_by_name(name):
    for patient in onto.Пациенты.instances():
        if name in patient.имеет_ФИО:
            return patient
    return None


def sanitize_name(name):
    return name.replace(" ", "_").replace(".", "").replace(",", "")

def generate_unique_patient_id(name):
    base = sanitize_name(name)
    suffix = uuid4().hex[:6]
    return f"{base}_{suffix}"

def classify_patient_with_sparql(onto, patient):
    try:
        g = onto.world.as_rdflib_graph()
        iri = patient.iri
        base = onto.base_iri

        # Риски есть
        query_risks_exist = f"""
        PREFIX : <{base}>
        SELECT ?p WHERE {{
            ?p a :Пациенты ;
               :имеет_СКФ ?skf ;
               :имеет_срок_заболевания ?srok .
            FILTER (?skf <= 76.0)
            FILTER (?p = <{iri}>)
        }}
        """

        # Рисков нет
        query_risks_none = f"""
        PREFIX : <{base}>
        SELECT ?p WHERE {{
          {{
            ?p a :Пациенты ;
               :имеет_СКФ ?skf ;
               :имеет_срок_заболевания :постановка_диагноза .
            FILTER (?skf > 76.0)
          }}
          UNION {{
            ?p a :Пациенты ;
               :имеет_СКФ ?skf ;
               :имеет_срок_заболевания :1_год .
            FILTER (?skf > 75.0)
          }}
          UNION {{
            ?p a :Пациенты ;
               :имеет_СКФ ?skf ;
               :имеет_срок_заболевания :2_года .
            FILTER (?skf > 70.0)
          }}
          UNION {{
            ?p a :Пациенты ;
               :имеет_СКФ ?skf ;
               :имеет_срок_заболевания :3_года .
            FILTER (?skf > 65.0)
          }}
          FILTER (?p = <{iri}>)
        }}
        """

        results_exist = list(g.query(query_risks_exist))
        if results_exist:
            return "в зоне риска"

        results_none = list(g.query(query_risks_none))
        if results_none:
            return "рисков нет"

        return "Не удалось определить группу риска"

    except Exception as e:
        print(f"Ошибка при выполнении SPARQL-запроса: {e}")
        return "Ошибка анализа риска"

def get_disease_stage_with_sparql(onto, patient):
    try:
        g = onto.world.as_rdflib_graph()
        iri = patient.iri
        base = onto.base_iri

        stage_queries = {
            "A": f"""
                PREFIX : <{base}>
                SELECT ?p WHERE {{
                    ?p a :Пациенты ;
                       :имеет_гемоглобин ?h ;
                       :имеет_тромбоциты ?t ;
                       :имеет_пораженные_лимфоузлы :1_или_2_узла .
                    FILTER (?h > 100)
                    FILTER (?t >= 150 && ?t <= 390)
                    FILTER (?p = <{iri}>)
                }}
            """,
            "B": f"""
                PREFIX : <{base}>
                SELECT ?p WHERE {{
                    ?p a :Пациенты ;
                       :имеет_гемоглобин ?h ;
                       :имеет_тромбоциты ?t ;
                       :имеет_пораженные_лимфоузлы :3_и_более_узлов .
                    FILTER (?h > 100)
                    FILTER (?t >= 150 && ?t <= 390)
                    FILTER (?p = <{iri}>)
                }}
            """,
            "C": f"""
                PREFIX : <{base}>
                SELECT ?p WHERE {{
                    ?p a :Пациенты ;
                       :имеет_гемоглобин ?h ;
                       :имеет_тромбоциты ?t ;
                       :имеет_пораженные_лимфоузлы ?lymph .
                    FILTER (?h < 100)
                    FILTER (?t < 150)
                    FILTER (?p = <{iri}>)
                    FILTER (?lymph IN (:1_или_2_узла, :3_и_более_узлов))
                }}
            """
        }

        for stage, query in stage_queries.items():
            results = list(g.query(query))
            if results:
                return stage

        return "не определена - скорее всего, были некорректно введены показатели крови."

    except Exception as e:
        print(f"Ошибка при выполнении SPARQL-запроса стадии: {e}")
        return "Ошибка анализа стадии"


def calculate_age(birthdate_str):
    try:
        birthdate = datetime.strptime(birthdate_str, "%d.%m.%Y")
        today = datetime.today()
        return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    except ValueError:
        return None

def calculate_ckd_epi(age, sex, creatinine):
    creatinine = float(creatinine) / 88.4  # перевод в мг/дл
    age = float(age)

    if sex.lower() in ['мужской', 'муж', 'male', 'm']:
        k = 0.9
        a = -0.302
        sex_factor = 1
    else:
        k = 0.7
        a = -0.241
        sex_factor = 1.018

    if creatinine <= k:
        scr_k_ratio = creatinine / k
        power = a
    else:
        scr_k_ratio = creatinine / k
        power = -1.2

    skf = 141 * (scr_k_ratio ** power) * (0.993 ** age) * sex_factor
    return int(round(skf))  # округление до целого


ctypes.windll.shcore.SetProcessDpiAwareness(1) # разрешение на автоматическое масштабирование

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATHS = {
    "frame0": OUTPUT_PATH / Path(r"D:\Univer\4kurs\diplom\hemopro1\assets\frame0"),
    "frame1": OUTPUT_PATH / Path(r"D:\Univer\4kurs\diplom\hemopro1\assets\frame1")
}

def relative_to_assets(folder: str, path: str) -> Path:
    if folder in ASSETS_PATHS:
        return ASSETS_PATHS[folder] / Path(path)
    else:
        raise ValueError(f"Папка {folder} не найдена в ASSETS_PATHS")


def update_patients_tree():
    for item in patients_tree.get_children():
        patients_tree.delete(item)

    patients = onto.Пациенты.instances()

    for patient in patients:
        fio = patient.имеет_ФИО[0] if hasattr(patient, "имеет_ФИО") and patient.имеет_ФИО else "N/A"
        age = patient.имеет_возраст[0] if hasattr(patient, "имеет_возраст") and patient.имеет_возраст else "N/A"

        if hasattr(patient, "имеет_пол") and patient.имеет_пол:
            sex = "М" if "муж" in str(patient.имеет_пол[0]).lower() else "Ж"
        else:
            sex = "N/A"

        try:
            stage = get_disease_stage_with_sparql(onto, patient)
        except Exception as e:
            print(f"Ошибка при получении стадии: {e}")
            stage = "Ошибка"

        try:
            risk = classify_patient_with_sparql(onto, patient)
        except Exception as e:
            print(f"Ошибка при классификации риска: {e}")
            risk = "Ошибка"

        patients_tree.insert(
            "",
            "end",
            values=(
                fio,
                age,
                sex,
                stage,
                risk
            )
        )



def create_patients_tab():
    global patients_tree

    canvas_patients = Canvas(
        frame_patients,
        bg="#FFFFFF",
        height=1080,
        width=1920,
        bd=0,
        highlightthickness=0,
        relief="ridge"
    )
    canvas_patients.place(x=0, y=0)

    canvas_patients.create_rectangle(
        0.0,
        0.0,
        429.0,
        1080.0,
        fill="#F1E4F8",
        outline="")

    canvas_patients.create_text(
        30.0,
        41.0,
        anchor="nw",
        text="Меню",
        fill="#49454F",
        font=("Roboto Medium", 40 * -1)
    )

    # кнопки меню
    button_image_p1 = PhotoImage(
        file=relative_to_assets("frame1", "button_2.png"))
    button_p1 = Button(
        frame_patients,
        image=button_image_p1,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: notebook.select(frame_patients),
        relief="flat"
    )
    button_p1.place(
        x=0.0,
        y=85.0,
        width=429.0,
        height=59.0
    )

    button_image_p2 = PhotoImage(
        file=relative_to_assets("frame1", "button_3.png"))
    button_p2 = Button(
        frame_patients,
        image=button_image_p2,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: notebook.select(frame_diagnosis),
        relief="flat"
    )
    button_p2.place(
        x=0.0,
        y=144.0,
        width=429.0,
        height=59.0
    )

    button_image_p3 = PhotoImage(
        file=relative_to_assets("frame1", "button_4.png"))
    button_p3 = Button(
        frame_patients,
        image=button_image_p3,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: notebook.select(frame_rediagnosis),
        relief="flat"
    )
    button_p3.place(
        x=0.0,
        y=203.0,
        width=429.0,
        height=59.0
    )


    # Treeview

    style = ttk.Style()

    style.configure("Custom.Treeview",
                    background="#FFFFFF",
                    fieldbackground="#FFFFFF",
                    foreground="#000000",
                    font=("Roboto", 12),
                    borderwidth=0,
                    relief="flat",
                    rowheight=30)

    style.configure("Custom.Treeview.Heading",
                    background="#F1E4F8",
                    foreground="#000000",
                    font=("Roboto Medium", 12),
                    relief="flat")


    style.map("Custom.Treeview.Heading",
              background=[('active', '#EAD9F3')])

    style.layout("Custom.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

    style.map("Custom.Treeview",
              background=[('selected', '#ddf1d9')],
              foreground=[('selected', '#000000')])

    columns = ("fio", "age", "sex", "stage", "risk")
    patients_tree = ttk.Treeview(
        frame_patients,
        columns=columns,
        show="headings",
        selectmode="browse",
        style="Custom.Treeview"
    )

    patients_tree.heading("fio", text="ФИО")
    patients_tree.heading("age", text="Возраст")
    patients_tree.heading("sex", text="Пол")
    patients_tree.heading("stage", text="Стадия")
    patients_tree.heading("risk", text="Группа риска")

    patients_tree.column("fio", width=250)
    patients_tree.column("age", width=80, anchor="center")
    patients_tree.column("sex", width=80, anchor="center")
    patients_tree.column("stage", width=100, anchor="center")
    patients_tree.column("risk", width=120, anchor="center")

    scrollbar = ttk.Scrollbar(frame_patients, orient="vertical", command=patients_tree.yview)
    patients_tree.configure(yscrollcommand=scrollbar.set)

    patients_tree.place(
        x=450,
        y=45,
        width=1400,
        height=960
    )
    scrollbar.place(
        x=1850,
        y=45,
        height=960
    )

    update_patients_tree()

window = Tk()
window.title("HemaPro")
window.geometry("1920x1080")
window.configure(bg="#FFFFFF")

style = ttk.Style()
style.theme_use('default')
style.layout("TNotebook.Tab", [])

main_frame = Frame(window)
main_frame.pack(fill="both", expand=True)

notebook = ttk.Notebook(main_frame)
notebook.pack(fill="both", expand=True)

frame_patients = Frame(notebook, bg="#FFFFFF")
frame_diagnosis = Frame(notebook, bg="#FFFFFF")
frame_rediagnosis = Frame(notebook, bg="#FFFFFF")

notebook.add(frame_patients)
notebook.add(frame_diagnosis)
notebook.add(frame_rediagnosis)

create_patients_tab()


# diagnosis
canvas_diagnosis = Canvas(
    frame_diagnosis,
    bg = "#FFFFFF",
    height = 1080,
    width = 1920,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas_diagnosis.place(x = 0, y = 0)
canvas_diagnosis.create_rectangle(
    0.0,
    0.0,
    429.0,
    1080.0,
    fill="#F1E4F8",
    outline="")

canvas_diagnosis.create_text(
    30.0,
    41.0,
    anchor="nw",
    text="Меню",
    fill="#49454F",
    font=("Roboto Medium", 40 * -1)
)

button_image_diag = PhotoImage(
    file=relative_to_assets("frame0","button_2.png"))
button_diag = Button(
    frame_diagnosis,
    image=button_image_diag,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: notebook.select(frame_patients),
    relief="flat"
)
button_diag.place(
    x=0.0,
    y=85.0,
    width=429.0,
    height=59.0
)

button_image_3 = PhotoImage(
    file=relative_to_assets("frame0","button_3.png"))
button_3 = Button(
    frame_diagnosis,
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: notebook.select(frame_diagnosis),
    relief="flat"
)
button_3.place(
    x=0.0,
    y=144.0,
    width=429.0,
    height=59.0
)

button_image_4 = PhotoImage(
    file=relative_to_assets("frame0","button_4.png"))
button_4 = Button(
    frame_diagnosis,
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: notebook.select(frame_rediagnosis),
    relief="flat"
)
button_4.place(
    x=0.0,
    y=203.0,
    width=429.0,
    height=59.0
)

canvas_diagnosis.create_text(
    1394.0,
    41.0,
    anchor="nw",
    text="Результат диагностики",
    fill="#49454F",
    font=("Roboto Medium", 40 * -1)
)

canvas_diagnosis.create_text(
    664.0,
    41.0,
    anchor="nw",
    text="Постановка диагноза\n",
    fill="#49454F",
    font=("Roboto Medium", 40 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    115.0,
    anchor="nw",
    text="ФИО пациента",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    252.0,
    anchor="nw",
    text="Пол",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    180.0,
    anchor="nw",
    text="Дата рождения",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    474.0,
    anchor="nw",
    text="Гемоглобин",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    407.0,
    anchor="nw",
    text="Тромбоциты",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    542.0,
    anchor="nw",
    text="Креатинин",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_diagnosis.create_text(
    474.0,
    338.0,
    anchor="nw",
    text="Кол-во пораженных лимфоузлов",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

entry_image_1 = PhotoImage(
    file=relative_to_assets("frame0","entry_1.png"))
entry_bg_1 = canvas_diagnosis.create_image(
    959.5,
    134.5,
    image=entry_image_1
)
entry_1 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_1.place(
    x=714.0,
    y=114.0,
    width=491.0,
    height=39.0
)

entry_image_2 = PhotoImage(
    file=relative_to_assets("frame0","entry_2.png"))
entry_bg_2 = canvas_diagnosis.create_image(
    814.5,
    198.5,
    image=entry_image_2
)
entry_2 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_2.place(
    x=733.0,
    y=178.0,
    width=163.0,
    height=39.0
)

entry_image_3 = PhotoImage(
    file=relative_to_assets("frame0","entry_3.png"))
entry_bg_3 = canvas_diagnosis.create_image(
    608.0,
    270.5,
    image=entry_image_3
)
entry_3 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_3.place(
    x=560.0,
    y=250.0,
    width=96.0,
    height=39.0
)

entry_image_4 = PhotoImage(
    file=relative_to_assets("frame0","entry_4.png"))
entry_bg_4 = canvas_diagnosis.create_image(
    1012.5,
    356.5,
    image=entry_image_4
)
entry_4 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_4.place(
    x=980.0,
    y=336.0,
    width=65.0,
    height=39.0
)

entry_image_5 = PhotoImage(
    file=relative_to_assets("frame0","entry_5.png"))
entry_bg_5 = canvas_diagnosis.create_image(
    720.5,
    425.5,
    image=entry_image_5
)
entry_5 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_5.place(
    x=688.0,
    y=405.0,
    width=65.0,
    height=39.0
)

entry_image_6 = PhotoImage(
    file=relative_to_assets("frame0","entry_6.png"))
entry_bg_6 = canvas_diagnosis.create_image(
    704.5,
    492.5,
    image=entry_image_6
)
entry_6 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_6.place(
    x=672.0,
    y=472.0,
    width=65.0,
    height=39.0
)

entry_image_7 = PhotoImage(
    file=relative_to_assets("frame0","entry_7.png"))
entry_bg_7 = canvas_diagnosis.create_image(
    689.5,
    560.5,
    image=entry_image_7
)
entry_7 = Entry(
    frame_diagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_7.place(
    x=657.0,
    y=540.0,
    width=65.0,
    height=39.0
)

button_image_5 = PhotoImage(
    file=relative_to_assets("frame0","button_5.png"))

# логирование
logging.basicConfig(filename='ontology_app.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def log_error(message):
    print(message)
    logging.error(message)

# обертка для добавления числовых значений
def safe_append_integer(property_obj, value, field_name):
    try:
        property_obj.append(int(value))
    except ValueError:
        log_error(f"Ошибка: поле '{field_name}' должно быть целым числом.")
    except Exception as e:
        log_error(f"Неожиданная ошибка при добавлении '{field_name}': {e}")

# обертка для добавления вещественных значений
def safe_append_float(property_obj, value, field_name):
    try:
        property_obj.append(float(value))
    except ValueError:
        log_error(f"Ошибка: поле '{field_name}' должно быть числом.")
    except Exception as e:
        log_error(f"Неожиданная ошибка при добавлении '{field_name}': {e}")

def add_patient_to_ontology(name, skf, hemoglobin, platelets, creatinine_val, age, sex, lymph_nodes):
    try:
        patient_class = onto.Пациенты
        unique_id = generate_unique_patient_id(name)
        patient = patient_class(unique_id)
    except Exception as e:
        log_error(f"Ошибка создания пациента: {e}")
        return None

    try:
        patient.имеет_ФИО.append(name)
    except AttributeError:
        log_error("Ошибка: свойство 'имеет_ФИО' не определено в онтологии.")

    safe_append_float(patient.имеет_СКФ, skf, "СКФ")


    if hasattr(onto, 'постановка_диагноза'):
        try:
            patient.имеет_срок_заболевания.append(onto.постановка_диагноза)
        except Exception as e:
            log_error(f"Ошибка при добавлении срока заболевания: {e}")
    else:
        log_error("Ошибка: не найден класс 'постановка_диагноза' в онтологии.")
        return None

    safe_append_integer(patient.имеет_возраст, age, "возраст")

    # Пол
    try:
        sex_lower = sex.lower()
        if sex_lower in ['мужской', 'муж', 'male', 'm', 'м']:
            gender_individual = getattr(onto, 'мужской', None)
        elif sex_lower in ['женский', 'жен', 'female', 'f', 'ж']:
            gender_individual = getattr(onto, 'женский', None)
        else:
            log_error(f"Ошибка: Некорректно указан пол: '{sex}'")
            return None

        if gender_individual:
            patient.имеет_пол.append(gender_individual)
        else:
            log_error("Ошибка: Индивидуал пола не найден в онтологии.")
            return None
    except Exception as e:
        log_error(f"Ошибка при добавлении пола: {e}")
        return None

    # Лабораторные данные
    safe_append_integer(patient.имеет_гемоглобин, hemoglobin, "гемоглобин")
    safe_append_integer(patient.имеет_тромбоциты, platelets, "тромбоциты")
    safe_append_integer(patient.имеет_креатинин, creatinine_val, "креатинин")

    # Лимфоузлы
    try:
        num_nodes = int(lymph_nodes)
        if num_nodes < 0:
            log_error("Ошибка: Количество лимфоузлов не может быть отрицательным.")
            return None

        if num_nodes == 0:
            node_class = getattr(onto, '0_узлов', None)
        elif num_nodes in [1, 2]:
            node_class = getattr(onto, '1_или_2_узла', None)
        else:
            node_class = getattr(onto, '3_и_более_узлов', None)

        if not node_class:
            log_error("Ошибка: Класс для указанного количества лимфоузлов не найден в онтологии.")
            return None

        if node_class is None:
            log_error("Ошибка: Класс для указанного количества лимфоузлов не найден в онтологии.")
            return None

        patient.имеет_пораженные_лимфоузлы.append(node_class)

        # Диагностика
        try:
            diagnosis_class = getattr(onto, 'Диагностика', None)
            if not diagnosis_class:
                log_error("Ошибка: Класс 'Диагностика' не найден в онтологии.")
                return None

            first_diag = diagnosis_class(f"Диагностика_{uuid4().hex[:6]}")
            first_diag.имеет_номер_диагностики.append(1)
            first_diag.имеет_СКФ.append(float(skf))
            first_diag.имеет_креатинин.append(int(creatinine_val))
            first_diag.имеет_возраст.append(int(age))
            first_diag.имеет_дату_диагностики.append(datetime.now())

            if hasattr(onto, 'постановка_диагноза'):
                first_diag.имеет_срок_заболевания.append(onto.постановка_диагноза)
            else:
                log_error("Ошибка: 'постановка_диагноза' отсутствует в онтологии.")

            patient.имеет_диагностику.append(first_diag)

        except Exception as e:
            log_error(f"Ошибка при создании диагностики: {e}")
            return None

    except ValueError:
        log_error("Ошибка: Введите корректное количество лимфоузлов (целое число).")
        return None
    except Exception as e:
        log_error(f"Ошибка при добавлении лимфоузлов: {e}")
        return None

    # Сохранение онтологии
    save_path = "D:/Univer/4kurs/diplom/hemopro1/hemopro22.owl"
    if not os.path.isdir(os.path.dirname(save_path)):
        log_error(f"Ошибка: Директория для сохранения не существует: {os.path.dirname(save_path)}")
        return None

    try:
        onto.save(file=save_path, format="rdfxml")
    except Exception as e:
        log_error(f"Ошибка при сохранении онтологии: {e}")
        return None

    return patient



def validate_name(name):
    return bool(re.match(r"^[А-Яа-яA-Za-z\s\-]+$", name.strip()))

def validate_positive_integer(value):
    try:
        number = int(value)
        return number > 0
    except ValueError:
        return False

def show_result(text):
    entry_8.delete("1.0", "end")
    entry_8.insert("1.0", text)

def validate_sex(sex):
    sex_lower = sex.strip().lower()
    if sex_lower in ['мужской', 'муж', 'male', 'm', 'м', 'женский', 'жен', 'female', 'f', 'ж']:
        return True
    return False


def on_calculate_click():
    name = entry_1.get()
    birthdate_str = entry_2.get()
    sex = entry_3.get()
    lymph_nodes = entry_4.get()
    platelets = entry_5.get()
    hemoglobin = entry_6.get()
    creatinine = entry_7.get()

    if not all([name, birthdate_str, sex, lymph_nodes, platelets, hemoglobin, creatinine]):
        show_result("Ошибка: заполните все поля.")
        return

    # Валидация ФИО
    if not validate_name(name):
        show_result("Ошибка: В поле 'ФИО' допускаются только буквы, пробелы и дефисы.")
        return

    # Валидация пола
    if not validate_sex(sex):
        show_result("Ошибка: В поле 'Пол' введите 'мужской' или 'женский'.")
        return

    # Валидация числовых полей
    if not validate_positive_integer(platelets):
        show_result("Ошибка: В поле 'Тромбоциты' введите положительное целое число.")
        return

    if not validate_positive_integer(hemoglobin):
        show_result("Ошибка: В поле 'Гемоглобин' введите положительное целое число.")
        return

    if not validate_positive_integer(creatinine):
        show_result("Ошибка: В поле 'Креатинин' введите положительное целое число.")
        return

    if not validate_positive_integer(lymph_nodes) and lymph_nodes != "0":
        show_result("Ошибка: В поле 'Лимфоузлы' введите 0 или положительное целое число.")
        return

    age = calculate_age(birthdate_str)
    if age is None:
        show_result("Ошибка: некорректная дата рождения. Используйте формат ДД.ММ.ГГГГ.")
        return

    skf = calculate_ckd_epi(age, sex, creatinine)
    if skf is None:
        show_result("Ошибка: введите корректные значения для пола и креатинина.")
        return

    patient = add_patient_to_ontology(name, skf, hemoglobin, platelets, creatinine, age, sex, lymph_nodes)

    if patient:
        print(f"Пациент {patient} имеет классы: {patient.is_a}")
        print(f"СКФ пациента: {patient.имеет_СКФ}")
        print(f"Срок заболевания пациента: {patient.имеет_срок_заболевания}")

        risk_status = classify_patient_with_sparql(onto, patient)
        stage_info = get_disease_stage_with_sparql(onto, patient)
    else:
        risk_status = "Ошибка добавления пациента в онтологию."
        stage_info = "Стадия заболевания не определена - скорее всего, были некорректно введены показатели крови."

    result_text = (
        f"Пациент: {name}\n"
        f"Возраст: {age} лет\n"
        f"Пол: {sex}\n"
        f"Кол-во пораженных лимфоузлов: {lymph_nodes}\n"
        f"Тромбоциты: {platelets}\n"
        f"Гемоглобин: {hemoglobin}\n"
        f"Креатинин: {creatinine} мкмоль/л\n"
        f"СКФ: {skf} мл/мин/1.73м²\n"
        f"Группа риска: {risk_status}\n"
        f"Стадия заболевания: {stage_info}\n"
    )

    show_result(result_text)


button_5 = Button(
    frame_diagnosis,
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=on_calculate_click,
    relief="flat"
)

button_5.place(
    x=674.0,
    y=755.0,
    width=392.0,
    height=81.0
)

entry_image_8 = PhotoImage(
    file=relative_to_assets("frame0","entry_8.png"))
entry_bg_8 = canvas_diagnosis.create_image(
    1614.5,
    576.0,
    image=entry_image_8
)
entry_8 = Text(
    frame_diagnosis,
    bd=0,
    bg="#DDF1D9",
    fg="#49454F",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_8.place(
    x=1373.0,
    y=103.0,
    width=483.0,
    height=944.0
)

#rediagnosis

canvas_rediagnosis = Canvas(
    frame_rediagnosis,
    bg = "#FFFFFF",
    height = 1080,
    width = 1920,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas_rediagnosis.place(x = 0, y = 0)
canvas_rediagnosis.create_rectangle(
    0.0,
    0.0,
    429.0,
    1080.0,
    fill="#F1E4F8",
    outline="")

canvas_rediagnosis.create_text(
    1394.0,
    41.0,
    anchor="nw",
    text="Результат диагностики",
    fill="#49454F",
    font=("Roboto Medium", 40 * -1)
)

canvas_rediagnosis.create_text(
    642.0,
    41.0,
    anchor="nw",
    text="Повторная диагностика",
    fill="#49454F",
    font=("Roboto Medium", 40 * -1)
)

canvas_rediagnosis.create_text(
    30.0,
    41.0,
    anchor="nw",
    text="Меню",
    fill="#49454F",
    font=("Roboto Medium", 40 * -1)
)

button_image_22 = PhotoImage(
    file=relative_to_assets("frame1","button_2.png"))
button_22 = Button(
    frame_rediagnosis,
    image=button_image_22,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: notebook.select(frame_patients),
    relief="flat"
)
button_22.place(
    x=0.0,
    y=85.0,
    width=429.0,
    height=59.0
)

button_image_33 = PhotoImage(
    file=relative_to_assets("frame1","button_3.png"))
button_33 = Button(
    frame_rediagnosis,
    image=button_image_33,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: notebook.select(frame_diagnosis),
    relief="flat"
)
button_33.place(
    x=0.0,
    y=144.0,
    width=429.0,
    height=59.0
)

button_image_44 = PhotoImage(
    file=relative_to_assets("frame1","button_4.png"))
button_44 = Button(
    frame_rediagnosis,
    image=button_image_44,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: notebook.select(frame_rediagnosis),
    relief="flat"
)

button_44.place(
    x=0.0,
    y=203.0,
    width=429.0,
    height=59.0
)

canvas_rediagnosis.create_text(
    474.0,
    115.0,
    anchor="nw",
    text="ФИО пациента",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_rediagnosis.create_text(
    474.0,
    186.0,
    anchor="nw",
    text="Возраст",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_rediagnosis.create_text(
    474.0,
    315.0,
    anchor="nw",
    text="Срок болезни",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

canvas_rediagnosis.create_text(
    474.0,
    253.0,
    anchor="nw",
    text="Креатинин",
    fill="#49454F",
    font=("Roboto Medium", 30 * -1)
)

entry_image_11 = PhotoImage(
    file=relative_to_assets("frame1","entry_1.png"))
entry_bg_11 = canvas_rediagnosis.create_image(
    959.5,
    134.5,
    image=entry_image_11
)
entry_111 = Entry(
    frame_rediagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#000716",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_111.place(
    x=714.0,
    y=114.0,
    width=491.0,
    height=39.0
)

entry_image_22 = PhotoImage(
    file=relative_to_assets("frame1","entry_2.png"))
entry_bg_10 = canvas_rediagnosis.create_image(
    643.5,
    204.5,
    image=entry_image_22
)
entry_222 = Entry(
    frame_rediagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#000716",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_222.place(
    x=626.0,
    y=184.0,
    width=35.0,
    height=39.0
)

entry_image_33 = PhotoImage(
    file=relative_to_assets("frame1","entry_3.png"))
entry_bg_111 = canvas_rediagnosis.create_image(
    733.5,
    330.5,
    image=entry_image_33
)
entry_33 = Entry(
    frame_rediagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#000716",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_33.place(
    x=701.0,
    y=310.0,
    width=65.0,
    height=39.0
)

entry_image_44 = PhotoImage(
    file=relative_to_assets("frame1","entry_4.png"))
entry_bg_12 = canvas_rediagnosis.create_image(
    699.0,
    267.5,
    image=entry_image_44
)
entry_444 = Entry(
    frame_rediagnosis,
    bd=0,
    bg="#F1E4F9",
    fg="#000716",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_444.place(
    x=661.0,
    y=247.0,
    width=76.0,
    height=39.0
)

def map_disease_duration(user_input):
    user_input = user_input.strip()
    if user_input == "1":
        return "1_год"
    elif user_input == "2":
        return "2_года"
    elif user_input == "3":
        return "3_года"
    else:
        return None


def add_new_diagnosis_to_patient(patient, diagnosis_date, skf, creatinine, age, disease_duration):
    try:
        if not (0 < skf <= 150):
            raise ValueError(f"Некорректное значение СКФ: {skf}")
        if not (0 < creatinine <= 2000):
            raise ValueError(f"Некорректное значение креатинина: {creatinine}")
        if not (0 < age <= 120):
            raise ValueError(f"Некорректное значение возраста: {age}")

        disease_term_name = map_disease_duration(disease_duration)
        if not disease_term_name:
            raise ValueError(f"Некорректный срок болезни '{disease_duration}'. Используйте '1', '2' или '3'.")

        disease_term = getattr(onto, disease_term_name, None)
        if not disease_term:
            raise AttributeError(f"Срок болезни '{disease_term_name}' не найден в онтологии.")

        diagnosis_class = onto.Диагностика
        new_diag = diagnosis_class(f"Диагностика_{uuid4().hex[:6]}")

        diagnosis_numbers = [d.имеет_номер_диагностики[0] for d in patient.имеет_диагностику]
        new_number = max(diagnosis_numbers) + 1 if diagnosis_numbers else 1

        new_diag.имеет_номер_диагностики.append(new_number)
        new_diag.имеет_СКФ.append(skf)
        new_diag.имеет_креатинин.append(int(creatinine))
        new_diag.имеет_возраст.append(int(age))

        if isinstance(diagnosis_date, datetime):
            new_diag.имеет_дату_диагностики.append(diagnosis_date)
        else:
            raise ValueError(f"Ожидался datetime, а получено: {type(diagnosis_date)}")

        new_diag.имеет_срок_заболевания.append(disease_term)
        patient.имеет_диагностику.append(new_diag)

        onto.save(file="D:/Univer/4kurs/diplom/hemopro1/hemopro22.owl", format="rdfxml")

        print(f"Добавлена новая диагностика {new_diag} пациенту {patient}")
        return new_diag

    except Exception as e:
        print(f"Ошибка добавления диагностики: {e}")
        return None


def perform_rediagnosis(name, age, creatinine, disease_duration):
    if not name.strip():
        return "Ошибка: имя пациента не может быть пустым."

    if not isinstance(age, int) or age <= 0 or age > 120:
        return "Ошибка: возраст должен быть положительным целым числом (1-120)."

    if not isinstance(creatinine, (int, float)) or creatinine <= 0 or creatinine > 2000:
        return "Ошибка: креатинин должен быть положительным числом (1-2000)."

    if not disease_duration.strip():
        return "Ошибка: срок болезни не указан."

    patient = find_patient_by_name(name)
    if not patient:
        return "Пациент не найден в онтологии."

    sex = patient.имеет_пол[0].name if patient.имеет_пол else 'мужской'
    skf = calculate_ckd_epi(age, sex, creatinine)

    today_date = datetime.now()
    diagnosis = add_new_diagnosis_to_patient(patient, today_date, skf, creatinine, age, disease_duration)

    if not diagnosis:
        return "Ошибка добавления новой диагностики."

    risk_status = classify_patient_with_sparql(onto, patient)
    stage_info = get_disease_stage_with_sparql(onto, patient)

    result_text = (
        f"Пациент: {name}\n"
        f"Возраст: {age}\n"
        f"Креатинин: {creatinine} мкмоль/л\n"
        f"СКФ: {skf} мл/мин/1.73м²\n"
        f"Срок болезни: {disease_duration}\n"
        f"Группа риска: {risk_status}\n"
        f"Стадия заболевания: {stage_info}\n"
        f"Диагностика проведена: {today_date.isoformat()}"
    )
    return result_text


def on_rediagnosis_click():
    name = entry_111.get()
    age = entry_222.get()
    creatinine = entry_444.get()
    disease_duration = entry_33.get()

    if not all([name, age, creatinine, disease_duration]):
        result = "Ошибка: заполните все поля."
    else:
        try:
            result = perform_rediagnosis(name, int(age), float(creatinine), disease_duration)
        except Exception as e:
            result = f"Ошибка выполнения: {e}"

    entry_555.delete("1.0", "end")
    entry_555.insert("1.0", result)


button_image_55 = PhotoImage(
    file=relative_to_assets("frame1","button_5.png"))
button_55 = Button(
    frame_rediagnosis,
    image=button_image_55,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: on_rediagnosis_click(),
    relief="flat"
)
button_55.place(
    x=674.0,
    y=755.0,
    width=392.0,
    height=81.0
)

entry_image_55 = PhotoImage(
    file=relative_to_assets("frame1","entry_5.png"))
entry_bg_13 = canvas_rediagnosis.create_image(
    1614.5,
    576.0,
    image=entry_image_55
)
entry_555 = Text(
    frame_rediagnosis,
    bd=0,
    bg="#DDF1D9",
    fg="#000716",
    highlightthickness=0,
    font=("Roboto Medium", 25 * -1)
)
entry_555.place(
    x=1373.0,
    y=103.0,
    width=483.0,
    height=944.0
)

window.resizable(True, True) # для изменения окна вручную

window.mainloop()

