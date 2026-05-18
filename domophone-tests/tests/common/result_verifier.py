import allure
from deepdiff import DeepDiff

def execute_api_control(db, api_client, fw_id, method_name, sent_values):
    """Логика проверки через API (контрольный метод)."""
    method_info = db.api.get_method(method_name, fw_id)
    control_method = method_info.control_method_name
    
    with allure.step(f"Контрольная проверка через API метод: {control_method}"):
        actual_values_response = api_client.running_method(db, control_method, fw_id)
        actual_values = actual_values_response.json()
        
        diff = DeepDiff(actual_values, sent_values, ignore_order=True)
        
        allure.attach(str(sent_values), "Отправленные значения", allure.attachment_type.TEXT)
        allure.attach(str(actual_values), "Полученные значения (API)", allure.attachment_type.TEXT)
        
        assert not diff, f"Данные в API не совпали с отправленными: {diff}"

def execute_web_control(db, api_client, fw_id, method_name, sent_values):
    """Заглушка для будущей проверки через WEB."""
    with allure.step(f"Контрольная проверка через WEB (в разработке)"):
        allure.attach("WEB control is not implemented yet", "Info")
        # Здесь будет логика Playwright
        pass

def execute_config_control(db, api_client, fw_id, method_name, sent_values):
    """Заглушка для будущей проверки через CONFIG файл."""
    with allure.step(f"Контрольная проверка через CONFIG (в разработке)"):
        allure.attach("CONFIG control is not implemented yet", "Info")
        # Здесь будет чтение YAML/JSON с устройства
        pass
