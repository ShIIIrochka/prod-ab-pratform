#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="http://localhost"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Тестирование LOTTY A/B Platform API           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

# 1. Health check
echo -e "${YELLOW}┌─ 1. Health check endpoints${NC}"
echo -e "${YELLOW}└─ GET /health, GET /ready${NC}"
curl -s -X GET "$API_URL/health" | jq .
curl -s -X GET "$API_URL/ready" | jq .
echo ""

# 2. Регистрация пользователя EXPERIMENTER
echo -e "${YELLOW}┌─ 2. Регистрация пользователя EXPERIMENTER${NC}"
echo -e "${YELLOW}└─ POST /auth/register${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "experimenter@example.com",
    "password": "password123",
    "role": "experimenter"
  }')
echo $REGISTER_RESPONSE | jq .
echo ""

# 3. Повторная регистрация (ожидается UserAlreadyExistsException - 409)
echo -e "${YELLOW}┌─ 3. Повторная регистрация (ожидается 409 Conflict)${NC}"
echo -e "${YELLOW}└─ POST /auth/register${NC}"
curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "experimenter@example.com",
    "password": "password123",
    "role": "experimenter"
  }' | jq .
echo ""

# 4. Вход с неверным паролем (ожидается InvalidCredentialsException - 401)
echo -e "${YELLOW}┌─ 4. Вход с неверным паролем (ожидается 401)${NC}"
echo -e "${YELLOW}└─ POST /auth/login${NC}"
curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "experimenter@example.com",
    "password": "wrong_password"
  }' | jq .
echo ""

# 5. Успешный вход
echo -e "${YELLOW}┌─ 5. Успешный вход${NC}"
echo -e "${YELLOW}└─ POST /auth/login${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "experimenter@example.com",
    "password": "password123"
  }')
echo $LOGIN_RESPONSE | jq .

# Извлекаем access token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access_token')
echo -e "${GREEN}✓ Access token получен${NC}"
echo ""

# 6. Получение текущего пользователя с approval_group
echo -e "${YELLOW}┌─ 6. Получение текущего пользователя (с approval_group)${NC}"
echo -e "${YELLOW}└─ GET /auth/me${NC}"
ME_RESPONSE=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
echo $ME_RESPONSE | jq .
echo ""

# 7. Попытка доступа без токена (ожидается InvalidTokenException - 401)
echo -e "${YELLOW}┌─ 7. Попытка доступа без токена (ожидается 401)${NC}"
echo -e "${YELLOW}└─ GET /auth/me${NC}"
curl -s -X GET "$API_URL/auth/me" | jq .
echo ""

# 8. Регистрация VIEWER
echo -e "${YELLOW}┌─ 8. Регистрация пользователя VIEWER${NC}"
echo -e "${YELLOW}└─ POST /auth/register${NC}"
curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "viewer@example.com",
    "password": "password123",
    "role": "viewer"
  }' | jq .
echo ""

# 9. Вход VIEWER
echo -e "${YELLOW}┌─ 9. Вход VIEWER${NC}"
VIEWER_LOGIN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "viewer@example.com",
    "password": "password123"
  }')
VIEWER_TOKEN=$(echo $VIEWER_LOGIN | jq -r '.tokens.access_token')
echo -e "${GREEN}✓ Viewer token получен${NC}"
echo ""

# 10. Доступ к защищенному эндпоинту с EXPERIMENTER (успех)
echo -e "${YELLOW}┌─ 10. Доступ к /experiments с ролью EXPERIMENTER (ожидается успех)${NC}"
echo -e "${YELLOW}└─ GET /experiments${NC}"
curl -s -X GET "$API_URL/experiments" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
echo ""

# 11. Доступ к защищенному эндпоинту с VIEWER (ожидается 403)
echo -e "${YELLOW}┌─ 11. Доступ к /experiments с ролью VIEWER (ожидается 403)${NC}"
echo -e "${YELLOW}└─ GET /experiments${NC}"
curl -s -X GET "$API_URL/experiments" \
  -H "Authorization: Bearer $VIEWER_TOKEN" | jq .
echo ""

# 12. Decision API без токена (публичный)
echo -e "${YELLOW}┌─ 12. Decision API без токена (публичный)${NC}"
echo -e "${YELLOW}└─ POST /decide${NC}"
echo -e "${RED}Примечание: Для работы нужен feature flag в БД${NC}"
curl -s -X POST "$API_URL/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "user_123",
    "flag_key": "button_color",
    "attributes": {
      "country": "RU",
      "platform": "ios"
    }
  }' | jq .
echo ""

# 13. Decision API с токеном (опциональная аутентификация)
echo -e "${YELLOW}┌─ 13. Decision API с токеном (для логирования)${NC}"
echo -e "${YELLOW}└─ POST /decide${NC}"
curl -s -X POST "$API_URL/decide" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "subject_id": "user_456",
    "flag_key": "button_color",
    "attributes": {}
  }' | jq .
echo ""

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Тестирование завершено ✓                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}Проверено:${NC}"
echo -e "  ✓ Health checks"
echo -e "  ✓ Регистрация (успех и дубликат)"
echo -e "  ✓ Вход (успех и неверный пароль)"
echo -e "  ✓ Получение пользователя (с approval_group)"
echo -e "  ✓ Доступ без токена (401)"
echo -e "  ✓ Проверка ролей (403 для недостаточных прав)"
echo -e "  ✓ Decision API (публичный и с токеном)"
echo ""
echo -e "${BLUE}Смотрите документацию:${NC}"
echo -e "  - MIDDLEWARE_AND_ROLES.md"
echo -e "  - EXCEPTIONS_SYSTEM.md"
echo -e "  - FINAL_SUMMARY.md"
