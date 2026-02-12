from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"  # Управление пользователями, настройка правил ревью
    EXPERIMENTER = "experimenter"  # Создание и ведение экспериментов
    APPROVER = "approver"  # Ревью экспериментов
    VIEWER = "viewer"  # Только чтение
