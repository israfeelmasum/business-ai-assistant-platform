"""
Custom exceptions for the AI Chatbot Service.
"""

from fastapi import HTTPException, status


class ClientNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


class InvalidAPIKeyError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


class EntityNotFoundError(HTTPException):
    def __init__(self, entity_id: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entity not found: {entity_id}")


class ProviderNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="AI provider not found")


class AIProviderError(HTTPException):
    def __init__(self, detail: str = "AI provider error"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class KnowledgeGenerationError(HTTPException):
    def __init__(self, detail: str = "Failed to generate knowledge"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class DataSourceNotFoundError(HTTPException):
    def __init__(self, source_id: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source not found: {source_id}")


class SyncAlreadyRunningError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail="A sync is already running for this data source")
