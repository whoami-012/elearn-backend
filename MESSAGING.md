# Restricted academic messaging

The API is mounted at `/api/v1/messages`. Every REST request uses the existing
Bearer JWT dependency. WebSockets accept the same Bearer header; `?token=` is
also supported for clients that cannot set WebSocket headers.

## Current relationship mapping

The current user schema contains `student`, `faculty`, and `admin`. A student
and faculty member may communicate only when the student has an active
enrolment in a non-deleted course owned by that faculty member. Admins cannot
message. The policy layer recognizes `teacher` for a future role migration, but
the existing user enum is intentionally unchanged.

## Examples

```http
POST /api/v1/messages/conversations
Authorization: Bearer <token>
Content-Type: application/json

{"receiver_id":"<user-uuid>"}
```

```http
POST /api/v1/messages/conversations/<conversation-uuid>/messages
Authorization: Bearer <token>
Content-Type: application/json

{"content":"Please review chapter 3.","client_message_id":"<client-uuid>"}
```

Uploads use multipart fields `file`, optional `content`, and required
`client_message_id`. Attachments are private and can only be downloaded through
the authorized attachment endpoint. Flutter should use the returned
`next_cursor`, never synthesize participant data, and reconnect/resubscribe to
the WebSocket after network loss.

## Deployment

Run `alembic upgrade head` before starting the API. Local attachment storage is
the default. `MESSAGE_STORAGE_BACKEND=s3` uses an S3-compatible private bucket
and five-minute authorized download URLs. Local storage must be placed on a
private persistent volume and must not be mounted by `StaticFiles`. The
in-process rate limiter and WebSocket broadcaster
are suitable for one worker; a Redis-backed deployment adapter is required
before using multiple workers. Antivirus-enabled mode fails closed until a
scanner adapter is configured.
