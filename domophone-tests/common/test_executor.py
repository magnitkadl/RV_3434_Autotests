import allure
from core import get_firmware_by_version, get_api_method_params, generate_correct_api_method_params, get_positive_status
from . import logic

def run_method_test(db, api_client, firmware_version, method_name, case=None, sent_values=None, expected_status=None):
    """
    Универсальный фасад для запуска теста метода.
    :param case: объект из параметризации (тип кейса, контроль и т.д.)
    :param sent_values: если передано, отключает автогенерацию (для отладки)
    :param expected_status: если передано, перекрывает статус из БД
    """
    fw_model = get_firmware_by_version(db, firmware_version)
    case_type = case.get("type", "positive") if case else "positive"
    control_backend = case.get("control", "api") if case else "api"
    
    allure.dynamic.title(f"{case_type.capitalize()} | {method_name} ({control_backend.upper()})")
    
    # 1. Подготовка данных (Arrange)
    if sent_values is None:
        method_params = get_api_method_params(db, method_name, fw_model.id)
        sent_values = generate_correct_api_method_params(db, method_params, api_client, fw_model.id, method_name)
    
    if expected_status is None:
        expected_status = get_positive_status(db, method_name, fw_model.id)

    # 2. Выполнение (Act)
    with allure.step(f"Вызов целевого метода {method_name}"):
        response = api_client.running_method(db, method_name, fw_model.id, sent_values)
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, но пришел {response.status_code}"

    # 3. Контроль (Control & Assert)
    if control_backend == "api":
        logic.execute_api_control(db, api_client, fw_model.id, method_name, sent_values)
    elif control_backend == "web":
        logic.execute_web_control(db, api_client, fw_model.id, method_name, sent_values)
    elif control_backend == "config":
        logic.execute_config_control(db, api_client, fw_model.id, method_name, sent_values)
