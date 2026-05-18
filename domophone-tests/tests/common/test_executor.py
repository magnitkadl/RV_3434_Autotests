import allure
from core import generate_correct_api_method_params
from .result_verifier import execute_api_control, execute_web_control, execute_config_control

def run_method_test(db, api_client, firmware_version, method_name, case=None, sent_values=None, expected_status=None):
    """
    Универсальный фасад для запуска теста метода.
    :param db: объект DBRepository
    :param case: объект из параметризации (тип кейса, контроль и т.д.)
    :param sent_values: если передано, отключает автогенерацию (для отладки)
    :param expected_status: если передано, перекрывает статус из БД
    """
    fw_model = db.firmware.get_by_version(firmware_version)
    if fw_model is None:
        raise ValueError(f"Прошивка {firmware_version} не найдена в базе данных")

    case_type = case.get("type", "positive") if case else "positive"
    control_backend = case.get("control", "api") if case else "api"
    
    allure.dynamic.title(f"{case_type.capitalize()} | {method_name} ({control_backend.upper()})")
    
    # 1. Подготовка данных (Arrange)
    if sent_values is None:
        method_params = db.api.get_method_params(method_name, fw_model.id)
        sent_values = generate_correct_api_method_params(db, method_params, api_client, fw_model.id, method_name)
    
    if expected_status is None:
        expected_status = db.api.get_positive_status(method_name, fw_model.id)

    # 2. Выполнение (Act)
    with allure.step(f"Вызов целевого метода {method_name}"):
        response = api_client.running_method(db, method_name, fw_model.id, sent_values)
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, но пришел {response.status_code}"

    # 3. Контроль (Control & Assert)
    if control_backend == "api":
        execute_api_control(db, api_client, fw_model.id, method_name, sent_values)
    elif control_backend == "web":
        execute_web_control(db, api_client, fw_model.id, method_name, sent_values)
    elif control_backend == "config":
        execute_config_control(db, api_client, fw_model.id, method_name, sent_values)
