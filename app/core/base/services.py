from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from sqlalchemy.orm import Session


T = TypeVar("T")  # Represents your entity/model type
C = TypeVar("C")  # Represents your create schema type

class Service(ABC, Generic[T, C]):
    @staticmethod
    @abstractmethod
    def create(db: Session, obj_in: C) -> T:
        """ Creates an entity in the db """
        pass

    @staticmethod
    @abstractmethod
    def fetch():
        pass

    @staticmethod
    @abstractmethod
    def fetch_all():
        pass

    @staticmethod
    @abstractmethod
    def update():
        pass

    @staticmethod
    @abstractmethod
    def delete():
        pass