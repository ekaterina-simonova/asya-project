from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json
import requests

def extract_real_video_url_from_player(driver):
    """Функция для извлечения реального URL видео из работающего плеера"""
    print(f"\n=== ИЗВЛЕЧЕНИЕ РЕАЛЬНОГО URL ИЗ ПЛЕЕРА ===")
    
    try:
        # Получаем iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if not iframes:
            print("Iframe не найден")
            return None
            
        iframe = iframes[0]
        print("Переключаюсь в iframe...")
        
        # Переключаемся в iframe
        driver.switch_to.frame(iframe)
        
        # Ждем загрузки плеера
        print("Жду загрузки плеера (20 секунд)...")
        time.sleep(20)
        
        # Пытаемся запустить видео
        try:
            # Ищем кнопку воспроизведения
            play_buttons = driver.find_elements(By.XPATH, "//button[@aria-label='Play' or contains(@class,'play') or @title='Play']")
            if play_buttons:
                print(f"Найдено {len(play_buttons)} кнопок воспроизведения")
                play_buttons[0].click()
                print("Кнопка воспроизведения нажата")
            else:
                # Пробуем запустить через JavaScript
                driver.execute_script("""
                    var videos = document.getElementsByTagName('video');
                    if (videos.length > 0) {
                        videos[0].play().catch(function(e) {
                            console.log('Ошибка воспроизведения:', e);
                        });
                    }
                """)
                print("Попытка запуска через JavaScript")
                
        except Exception as e:
            print(f"Ошибка при запуске видео: {e}")
        
        # Ждем начала воспроизведения
        print("Жду начала воспроизведения (15 секунд)...")
        time.sleep(15)
        
        # Извлекаем реальные URL через JavaScript
        script = """
        var videoUrls = [];
        
        try {
            // Получаем информацию о сетевых запросах через performance
            if (window.performance && window.performance.getEntriesByType) {
                var resources = window.performance.getEntriesByType('resource');
                for (var i = 0; i < resources.length; i++) {
                    var resource = resources[i];
                    var url = resource.name;
                    if (url && (url.includes('.mp4') || url.includes('.m3u8') || url.includes('.webm') || 
                               url.includes('video') || url.includes('media') || url.includes('stream'))) {
                        videoUrls.push({
                            'url': url,
                            'type': resource.initiatorType,
                            'size': resource.transferSize
                        });
                    }
                }
            }
            
            // Ищем video элементы и их src
            var videos = document.getElementsByTagName('video');
            for (var i = 0; i < videos.length; i++) {
                if (videos[i].src && !videos[i].src.startsWith('blob:')) {
                    videoUrls.push({
                        'url': videos[i].src,
                        'type': 'video-element',
                        'size': 0
                    });
                }
                
                // Ищем source элементы
                var sources = videos[i].getElementsByTagName('source');
                for (var j = 0; j < sources.length; j++) {
                    if (sources[j].src && !sources[j].src.startsWith('blob:')) {
                        videoUrls.push({
                            'url': sources[j].src,
                            'type': 'source-element',
                            'size': 0
                        });
                    }
                }
            }
            
            // Ищем source элементы напрямую
            var directSources = document.getElementsByTagName('source');
            for (var i = 0; i < directSources.length; i++) {
                if (directSources[i].src && !directSources[i].src.startsWith('blob:')) {
                    videoUrls.push({
                        'url': directSources[i].src,
                        'type': 'direct-source',
                        'size': 0
                    });
                }
            }
            
        } catch (e) {
            console.log('Ошибка в скрипте:', e);
        }
        
        return videoUrls;
        """
        
        video_info = driver.execute_script(script)
        
        if video_info:
            print(f"Найдено {len(video_info)} потенциальных видео URL:")
            for i, info in enumerate(video_info):
                print(f"  {i+1}. {info['url']}")
                print(f"     Тип: {info['type']}, Размер: {info['size']} bytes")
            return video_info
        else:
            print("Видео URL не найдены в плеере")
            
    except Exception as e:
        print(f"Ошибка при извлечении URL: {e}")
        
    finally:
        try:
            driver.switch_to.default_content()
        except:
            pass
    
    return None

def test_and_download_found_urls(driver, video_info_list):
    """Функция для тестирования и скачивания найденных URL"""
    print(f"\n=== ТЕСТИРОВАНИЕ НАЙДЕННЫХ URL ===")
    
    if not video_info_list:
        print("Нет URL для тестирования")
        return False
    
    # Получаем cookies из Selenium для использования в requests
    selenium_cookies = driver.get_cookies()
    cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': driver.current_url,
        'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5'
    }
    
    for i, video_info in enumerate(video_info_list):
        url = video_info['url']
        print(f"\nПроверка URL {i+1}/{len(video_info_list)}: {url}")
        
        try:
            # Проверяем, доступен ли URL
            response = requests.head(url, headers=headers, cookies=cookies, timeout=15, allow_redirects=True)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = response.headers.get('content-length', '0')
                print(f"  Content-Type: {content_type}")
                print(f"  Content-Length: {content_length} bytes")
                
                if 'video' in content_type.lower() or any(ext in url.lower() for ext in ['.mp4', '.webm', '.m3u8']):
                    print("  🎯 Найдено видео! Скачиваю...")
                    
                    # Скачиваем видео
                    video_response = requests.get(url, headers=headers, cookies=cookies, timeout=300, stream=True)
                    if video_response.status_code == 200:
                        # Определяем имя файла
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        filename = f"downloaded_video_{i+1}.mp4"
                        if parsed_url.path:
                            path_filename = parsed_url.path.split('/')[-1]
                            if path_filename and '.' in path_filename:
                                filename = path_filename
                        
                        print(f"  Сохраняю как: {filename}")
                        
                        total_size = 0
                        with open(filename, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    total_size += len(chunk)
                                    if total_size % (1024 * 1024) == 0:
                                        print(f"    Скачано: {total_size / (1024*1024):.1f} MB")
                        
                        print(f"  ✅ Видео успешно скачано! Размер: {total_size / (1024*1024):.1f} MB")
                        return True
                    else:
                        print(f"  ❌ Ошибка скачивания: {video_response.status_code}")
                        
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            continue
    
    print("\n❌ Не удалось скачать ни одно видео")
    return False

# Основной код
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--enable-logging')
chrome_options.add_argument('--log-level=3')
chrome_options.add_argument('--mute-audio')
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=chrome_options)

try:
    print("Открываю сайт для авторизации...")
    driver.get('https://khromova-olga.ru')
    
    input("Пожалуйста, введите логин и пароль вручную и залогиньтесь, затем нажмите Enter для продолжения...")
    
    print("Переход к странице с видео...")
    driver.get('https://khromova-olga.ru/pl/teach/control/lesson/view?id=323662388')
    
    print("Ждем загрузки страницы...")
    time.sleep(10)
    
    # Извлекаем реальный URL из плеера
    video_info_list = extract_real_video_url_from_player(driver)
    
    if video_info_list:
        # Тестируем и скачиваем найденные URL
        success = test_and_download_found_urls(driver, video_info_list)
        if not success:
            print("\nПопробую альтернативный метод...")
            
            # Пробуем получить cookies и сессию
            print("Cookies из браузера:")
            cookies = driver.get_cookies()
            for cookie in cookies:
                if 'session' in cookie['name'].lower() or 'auth' in cookie['name'].lower():
                    print(f"  {cookie['name']}: {cookie['value']}")
    else:
        print("Видео не найдено в плеере")
    
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    input("Нажмите Enter для закрытия браузера...")
    driver.quit()