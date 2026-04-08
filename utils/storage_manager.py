import os
import json
import logging
from github import Github, GithubException

from config import DEBUG, GITHUB_TOKEN, REPO_NAME, CATALOG_FILE, IMAGES_DIR

class StorageManager:
    """
    Абстракция для управления хранилищем (локально или на GitHub).
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(StorageManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.debug = DEBUG
        self.catalog_path = CATALOG_FILE
        self.images_path = IMAGES_DIR
        self.github_client = None
        self.repo = None

        if not self.debug:
            if not GITHUB_TOKEN or not REPO_NAME:
                raise ValueError("GITHUB_TOKEN и REPO_NAME должны быть установлены для работы с GitHub.")
            self.github_client = Github(GITHUB_TOKEN)
            self.repo = self.github_client.get_repo(REPO_NAME)
            logging.info("StorageManager инициализирован в режиме GitHub.")
        else:
            logging.info("StorageManager инициализирован в локальном режиме (DEBUG).")

    def save_photo(self, file_bytes: bytes, filename: str) -> str:
        """
        Сохраняет фото локально или в репозиторий GitHub.
        Возвращает имя файла в случае успеха.
        """
        try:
            if self.debug:
                # Локальное сохранение
                if not os.path.exists(self.images_path):
                    os.makedirs(self.images_path)
                full_path = os.path.join(self.images_path, filename)
                with open(full_path, 'wb') as f:
                    f.write(file_bytes)
                logging.info(f"Фото локально сохранено: {full_path}")
            else:
                # Сохранение на GitHub
                github_path = f"{self.images_path}/{filename}"
                commit_message = f"Bot Upload: add image {filename}"
                self.repo.create_file(
                    path=github_path,
                    message=commit_message,
                    content=file_bytes,
                    branch="main"
                )
                logging.info(f"Фото загружено на GitHub: {github_path}")
            return filename
        except (GithubException, IOError) as e:
            logging.error(f"Ошибка при сохранении фото '{filename}': {e}")
            raise

    def update_catalog(self, item_data: dict):
        """
        Обновляет catalog.json локально или на GitHub, добавляя новый товар в начало.
        """
        try:
            # Шаг 1: Получение текущего каталога
            if self.debug:
                if not os.path.exists(self.catalog_path):
                    # Создаем пустой каталог, если файл не существует
                    catalog = {"items": []}
                else:
                    with open(self.catalog_path, 'r', encoding='utf-8') as f:
                        catalog = json.load(f)
                sha = None # SHA не нужен для локального режима
            else:
                try:
                    contents = self.repo.get_contents(self.catalog_path, ref="main")
                    catalog = json.loads(contents.decoded_content.decode('utf-8'))
                    sha = contents.sha
                except GithubException as e:
                    if e.status == 404:
                        catalog = {"items": []}
                        sha = None # Файла еще нет, SHA не нужен
                    else:
                        raise

            # Шаг 2: Добавление нового товара в начало
            catalog["items"].insert(0, item_data)
            new_content_str = json.dumps(catalog, indent=2, ensure_ascii=False)

            # Шаг 3: Сохранение обновленного каталога
            if self.debug:
                with open(self.catalog_path, 'w', encoding='utf-8') as f:
                    f.write(new_content_str)
                logging.info(f"Каталог локально обновлен: {self.catalog_path}")
            else:
                commit_message = f"Bot Update: add item {item_data['id']}"
                if sha: # Обновляем существующий файл
                    self.repo.update_file(
                        path=self.catalog_path,
                        message=commit_message,
                        content=new_content_str,
                        sha=sha,
                        branch="main"
                    )
                else: # Создаем новый файл
                     self.repo.create_file(
                        path=self.catalog_path,
                        message="Bot Init: create catalog.json",
                        content=new_content_str,
                        branch="main"
                    )
                logging.info(f"Каталог обновлен на GitHub: {self.catalog_path}")
        
        except (GithubException, IOError, json.JSONDecodeError) as e:
            logging.error(f"Ошибка при обновлении каталога: {e}")
            raise

