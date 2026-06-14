# CyberCafe Management System - API Documentation

## Overview

This document describes the API endpoints for the CyberCafe Management System. The API is built with FastAPI and provides both REST endpoints and WebSocket connections for real-time updates.

**Base URL:** `http://localhost:8000`

**Authentication:** Bearer token (JWT) in Authorization header

---

## Authentication

### POST /api/auth/login

Login and receive an access token.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### POST /api/auth/create

Create a new admin user.

**Request:**
```json
{
  "username": "newadmin",
  "email": "admin@example.com",
  "full_name": "New Admin",
  "password": "securepassword",
  "role": "branch_admin",
  "branch_id": 1
}
```

---

## PC Management

### GET /api/pcs/

Get all PCs.

**Query Parameters:**
- `branch_id` (optional): Filter by branch

**Response:**
```json
[
  {
    "id": 1,
    "name": "PC-01",
    "pc_number": 1,
    "branch_id": 1,
    "ip_address": "192.168.1.100",
    "status": "online",
    "is_active": true,
    "last_heartbeat_at": "2026-06-05T10:30:00"
  }
]
```

### POST /api/pcs/

Create a new PC.

**Request:**
```json
{
  "name": "PC-01",
  "pc_number": 1,
  "branch_id": 1,
  "ip_address": "192.168.1.100",
  "mac_address": "AA:BB:CC:DD:EE:FF"
}
```

### PUT /api/pcs/{pc_id}

Update a PC.

### DELETE /api/pcs/{pc_id}

Delete a PC.

### GET /api/pcs/{pc_id}/status

Get PC status with time remaining.

**Response:**
```json
{
  "pc_id": 1,
  "status": "in_use",
  "time_left": 1800,
  "is_active": true
}
```

---

## Session Management

### GET /api/sessions/

Get all sessions.

**Query Parameters:**
- `branch_id` (optional): Filter by branch
- `status` (optional): Filter by status (active, paused, completed, expired)

### POST /api/sessions/start

Start a new session.

**Request:**
```json
{
  "pc_id": 1,
  "branch_id": 1,
  "duration_minutes": 60,
  "code": "ABCD1234"
}
```

### POST /api/sessions/stop

Stop a session.

**Query Parameters:**
- `session_id`: ID of the session to stop

### POST /api/sessions/pause

Pause an active session.

**Query Parameters:**
- `session_id`: ID of the session to pause

**Note:** Session must have at least 5 minutes remaining.

### POST /api/sessions/resume

Resume a paused session.

**Query Parameters:**
- `session_id`: ID of the session to resume

### GET /api/sessions/heartbeat/{pc_id}

Heartbeat endpoint for clients.

**Response:**
```json
{
  "status": "active",
  "time_left": 1800,
  "is_active": true,
  "session_id": 1
}
```

### POST /api/sessions/redeem-code

Redeem a code and start a session.

**Request:**
```json
{
  "code": "ABCD1234",
  "pc_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Code redeemed successfully",
  "session_id": 1,
  "duration_minutes": 60,
  "end_time": "2026-06-05T11:30:00"
}
```

---

## Code Management

### GET /api/codes/batches

Get all code batches.

### POST /api/codes/batches

Create a new code batch.

**Request:**
```json
{
  "branch_id": 1,
  "duration_minutes": 60,
  "count": 50,
  "value_per_code": 100,
  "batch_name": "Morning Batch"
}
```

### GET /api/codes/batches/{batch_id}/codes

Get all codes in a batch.

### POST /api/codes/batches/{batch_id}/print

Mark a batch as printed.

### GET /api/codes/validate/{code}

Validate a code without using it.

**Response:**
```json
{
  "valid": true,
  "duration_minutes": 60,
  "value": 100
}
```

---

## Dashboard

### GET /api/dashboard/overview

Get dashboard overview stats.

**Response:**
```json
{
  "total_pcs": 20,
  "online_pcs": 15,
  "active_sessions": 8,
  "total_revenue_today": 50000,
  "total_sessions_today": 45,
  "codes_sold_today": 30
}
```

### GET /api/dashboard/revenue

Get revenue reports.

**Query Parameters:**
- `branch_id` (optional): Filter by branch
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

### POST /api/dashboard/revenue/generate

Generate a daily revenue report.

**Query Parameters:**
- `branch_id`: Branch ID
- `report_date` (optional): Date (YYYY-MM-DD)

---

## Filter Rules

### GET /api/filters/

Get all filter rules.

### POST /api/filters/

Create a new filter rule.

**Request:**
```json
{
  "branch_id": 1,
  "rule_type": "dns",
  "pattern": "*.facebook.com",
  "action": "block",
  "priority": 10,
  "description": "Block Facebook"
}
```

### PUT /api/filters/{rule_id}

Update a filter rule.

### DELETE /api/filters/{rule_id}

Delete a filter rule.

---

## Payments

### POST /api/payments/initialize

Initialize a payment.

**Request:**
```json
{
  "method": "paystack",
  "amount": 500,
  "email": "user@example.com",
  "session_id": 1,
  "branch_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment initialized",
  "payment_url": "https://checkout.paystack.com/...",
  "reference": "CC_ABC123456789"
}
```

### POST /api/payments/verify

Verify a payment.

**Request:**
```json
{
  "method": "paystack",
  "reference": "CC_ABC123456789"
}
```

### GET /api/payments/{reference}

Get payment status.

---

## WebSocket

### Connection

Connect to `ws://localhost:8000/ws`

### Client Messages

**Subscribe to PC updates:**
```json
{
  "type": "subscribe_pc",
  "pc_id": 1
}
```

**Heartbeat:**
```json
{
  "type": "ping"
}
```

### Server Messages

**PC status update:**
```json
{
  "type": "pc_status",
  "pc_id": 1,
  "data": {
    "status": "active",
    "time_left": 1800
  }
}
```

**Session update:**
```json
{
  "type": "session_update",
  "data": {
    "session_id": 1,
    "status": "active",
    "pc_id": 1
  }
}
```

**Stats update:**
```json
{
  "type": "stats_update",
  "data": {
    "active_sessions": 8,
    "online_pcs": 15
  }
}
```

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

**Error response format:**
```json
{
  "detail": "Error message"
}
```

---

## Rate Limiting

The API does not currently implement rate limiting. For production use, consider adding rate limiting middleware.

## CORS

CORS is enabled for the following origins:
- `http://localhost:7842`
- `http://localhost:8080`

Configure additional origins in the `CORS_ORIGINS` environment variable.
