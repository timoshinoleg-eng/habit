import requests
import json
import os

class OCRSpaceClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.ocr_url = "https://api.ocr.space/parse/image"

    def parse_receipt(self, image_path, language='rus'):
        """
        Отправляет изображение чека в OCR.space API и возвращает распознанный текст.
        """
        if not os.path.exists(image_path):
            return {"error": f"Файл не найден: {image_path}"}

        with open(image_path, 'rb') as f:
            response = requests.post(
                self.ocr_url,
                headers={'apikey': self.api_key},
                data={'language': language, 'isOverlayRequired': True},
                files={'filename': f}
            )

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка API OCR.space: {response.status_code} - {response.text}"}

    def extract_info_from_ocr_result(self, ocr_result):
        """
        Извлекает сумму и, возможно, другие данные из результата OCR.space.
        Это упрощенная версия, требующая доработки для реальных чеков.
        """
        extracted_text = ""
        if ocr_result and 'ParsedResults' in ocr_result and ocr_result['ParsedResults']:
            for result in ocr_result['ParsedResults']:
                extracted_text += result['ParsedText'] + "\n"

        # Здесь потребуется более сложная логика для извлечения суммы и категории
        # Например, поиск ключевых слов типа "ИТОГ", "СУММА", "ВСЕГО" и чисел рядом с ними.
        # Для категоризации потребуется NLP, как мы обсуждали ранее.
        total_amount = None
        # Пример очень простой логики для поиска суммы
        for line in extracted_text.split('\n'):
            if "ИТОГ" in line.upper() or "СУММА" in line.upper() or "ВСЕГО" in line.upper():
                # Попытка извлечь число после ключевого слова
                parts = line.split()
                for i, part in enumerate(parts):
                    if "ИТОГ" in part.upper() or "СУММА" in part.upper() or "ВСЕГО" in part.upper():
                        if i + 1 < len(parts):
                            try:
                                total_amount = float(parts[i+1].replace(',', '.'))
                                break
                            except ValueError:
                                continue
                if total_amount is not None:
                    break

        return {
            "raw_text": extracted_text,
            "total_amount": total_amount,
            "category": "Неизвестно" # Требуется NLP для определения категории
        }

# Пример использования (для тестирования)
if __name__ == "__main__":
    # ВАЖНО: Замените 'YOUR_OCR_SPACE_API_KEY' на ваш реальный ключ API OCR.space
    # Вы можете получить его бесплатно на https://ocr.space/ocrapi
    api_key = os.getenv("OCR_SPACE_API_KEY", "K87667637889876") # Замените на ваш ключ
    ocr_client = OCRSpaceClient(api_key)

    # Создайте тестовое изображение чека для проверки
    # Например, с помощью Pillow или просто сохраните изображение чека как 'test_receipt.png'
    # Для примера, создадим пустой файл, чтобы не было ошибки FileNotFoundError
    with open("test_receipt.png", "w") as f:
        f.write("dummy content")

    image_path = "test_receipt.png"
    print(f"Обработка изображения: {image_path}")
    ocr_result = ocr_client.parse_receipt(image_path)

    if "error" in ocr_result:
        print(f"Ошибка: {ocr_result['error']}")
    else:
        extracted_data = ocr_client.extract_info_from_ocr_result(ocr_result)
        print("Распознанный текст:")
        print(extracted_data["raw_text"])
        print(f"Предполагаемая сумма: {extracted_data['total_amount']}")
        print(f"Предполагаемая категория: {extracted_data['category']}")

