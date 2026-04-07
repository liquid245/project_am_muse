import logging
import json
from github import Github
from config import GITHUB_TOKEN, REPO_NAME, CATALOG_FILE

async def sync_catalog_to_github(new_data):
    """Синхронизация каталога с репозиторием GitHub."""
    if not GITHUB_TOKEN or not REPO_NAME:
        logging.info("GITHUB_TOKEN или REPO_NAME не настроены. Пропускаю синхронизацию.")
        return True

    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Получаем файл из репозитория
        contents = repo.get_contents(CATALOG_FILE)
        
        # Кодируем новые данные
        new_content_str = json.dumps(new_data, indent=2, ensure_ascii=False)
        
        # Обновляем файл в репозитории
        repo.update_file(
            path=CATALOG_FILE,
            message="Bot Update: sync catalog.json",
            content=new_content_str,
            sha=contents.sha,
            branch="main"
        )
        logging.info(f"catalog.json успешно синхронизирован с GitHub ({REPO_NAME})")
        return True
    except Exception as e:
        logging.error(f"Ошибка при синхронизации с GitHub: {e}")
        return False
