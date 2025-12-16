import pytest
from src.utils.text_utils import load_pronunciation_dict, replace_terms

def test_pronunciation():
    # Загружаем словарь из config
    dictionary = load_pronunciation_dict("config/pronunciation_dictionary.yaml")
    
    # Проверяем, что "Mik-Izol" преобразуется в "Ми-ки-зол"
    assert dictionary["Mik-Izol"] == "Ми-ки-зол"
    
    # Проверяем, что текст преобразуется правильно
    text = "Здравствуйте, вы связались с компанией Mik-Izol"
    transformed = replace_terms(text, dictionary)
    assert transformed == "Здравствуйте, вы связались с компанией Ми-ки-зол"