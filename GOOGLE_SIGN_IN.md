# Flutter Google Sign-In contract

Configure the backend with the same OAuth client ID Flutter uses to request the ID token:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Send the Google **ID token** (not an access token) to:

```http
POST /api/auth/google-login/
Content-Type: application/json

{"id_token":"GOOGLE_ID_TOKEN_FROM_FLUTTER"}
```

The versioned alias `POST /api/v1/auth/google-login/` behaves identically.

Successful response:

```json
{
  "success": true,
  "message": "Google login successful",
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid",
    "name": "Student Name",
    "email": "student@gmail.com",
    "role": "student",
    "profile_image": "https://..."
  }
}
```

Store and use `access_token` and `refresh_token` exactly as with email/password login. Error responses use FastAPI's standard `{"detail":"..."}` body.
