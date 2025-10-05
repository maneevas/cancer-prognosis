import pytest
from owlready2 import get_ontology
import tempfile
import os


@pytest.fixture(scope="session")
def temp_ontology():
    onto = get_ontology("http://test.org/hemopro.owl")
    with onto:
        class Пациенты(onto.Thing):
            pass

        class Диагностика(onto.Thing):
            pass

        class постановка_диагноза(onto.Thing):
            pass

        onto.постановка_диагноза = постановка_диагноза

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, "test_ontology.owl")
    onto.save(file=temp_path)

    yield temp_path

    os.remove(temp_path)
    os.rmdir(temp_dir)