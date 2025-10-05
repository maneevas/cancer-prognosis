import pytest
from owlready2 import get_ontology

@pytest.fixture(scope="module")
def main_ontology():
    onto_path = "D:/Univer/4kurs/diplom/hemopro1/hemopro22.owl"
    return get_ontology(f"file://{onto_path}").load()


def test_add_patient_to_ontology(main_ontology):
    from gui import add_patient_to_ontology

    result = add_patient_to_ontology(
        name="Иванов Иван",
        skf=75,
        hemoglobin=130,
        platelets=250,
        creatinine_val=90,
        age=60,
        sex="мужской",
        lymph_nodes=2,
        onto=main_ontology,
    )

    assert result is not None
    assert result.имеет_ФИО[0] == "Иванов Иван"
    assert result.имеет_возраст[0] == 60
