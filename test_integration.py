import pytest
from owlready2 import get_ontology
import gui


@pytest.fixture
def temp_ontology():
    path_to_ontology = "D:/Univer/4kurs/diplom/hemopro1/hemopro22.owl"
    onto = get_ontology(f"file://{path_to_ontology}").load()
    return onto


def test_on_calculate_click(monkeypatch, temp_ontology):
    monkeypatch.setattr(gui.entry_1, 'get', lambda: "Иванов Иван Иванович")
    monkeypatch.setattr(gui.entry_2, 'get', lambda: "01.01.1960")
    monkeypatch.setattr(gui.entry_3, 'get', lambda: "мужской")
    monkeypatch.setattr(gui.entry_4, 'get', lambda: "2")
    monkeypatch.setattr(gui.entry_5, 'get', lambda: "200")
    monkeypatch.setattr(gui.entry_6, 'get', lambda: "120")
    monkeypatch.setattr(gui.entry_7, 'get', lambda: "90")

    result = {"text": ""}

    def fake_insert(pos, text):
        result["text"] = text

    monkeypatch.setattr(gui.entry_8, 'delete', lambda *args: None)
    monkeypatch.setattr(gui.entry_8, 'insert', fake_insert)

    monkeypatch.setattr(gui, "onto", temp_ontology)

    gui.on_calculate_click()

    assert "Пациент: Иванов Иван Иванович" in result["text"]
    assert "Возраст:" in result["text"]
