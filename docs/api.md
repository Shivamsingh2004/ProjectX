# API Documentation

## Auth
- `POST /api/auth/register`
- `POST /api/auth/login`

## User
- `GET /api/users/profile`
- `PUT /api/users/profile`

## Activity
- `GET /api/activity`

## Messaging
- `GET /api/messages/conversations`
- `POST /api/messages/send`

## Analytics
- `GET /api/analytics`

## AI
- `POST /api/ai/reply-suggestion`
- `POST /api/ai/profile-analysis`

## Error Model
```json
{
  "error": "INVALID_REQUEST",
  "message": "User already exists",
  "status": 400
}
```
