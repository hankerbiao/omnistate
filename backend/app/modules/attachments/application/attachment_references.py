from app.shared.config import get_settings
from app.shared.core.mongo_client import get_mongo_client

_REFERENCING_COLLECTIONS = (
    "test_requirements", "test_cases", "project_document_versions", "project_files",
)


async def is_attachment_referenced(file_id: str) -> bool:
    database = get_mongo_client()[get_settings().mongodb.db_name]
    query = {"attachments.file_id": file_id, "is_deleted": False}
    for collection_name in _REFERENCING_COLLECTIONS[:2]:
        if await database[collection_name].count_documents(query, limit=1):
            return True
    for collection_name in _REFERENCING_COLLECTIONS[2:]:
        if await database[collection_name].count_documents({"attachment_id": file_id, "is_deleted": False}, limit=1):
            return True
    return False
