# Project 8: Natural Language SQL over Connected Database

This feature lets you connect to a SQL database and ask questions in natural language.

## What was added

- Backend endpoint: `POST /api/chat/database-question`
- Read-only SQL generation and execution (SELECT/CTE only)
- SQL safety checks blocking write or DDL statements
- Frontend chat command support:
  - `/db <database-url> | <natural-language question>`

## Supported databases

- PostgreSQL (`postgresql://...`)
- SQLite (`sqlite:///...`)

## How to use in chat

In the chat input box, type:

```text
/db postgresql://username:password@localhost:5432/chatbot_db | Which 10 users signed up most recently?
```

Example for SQLite:

```text
/db sqlite:///D:/Experiment-Chat-Bot/backend/chroma_db/chroma.sqlite3 | Show top 5 collections by row count
```

## API request example

```http
POST /api/chat/database-question
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "database_url": "postgresql://username:password@localhost:5432/chatbot_db",
  "question": "What are the top 5 conversations by message count?",
  "conversation_id": 123
}
```

## API response example

```json
{
  "user_message": "What are the top 5 conversations by message count?",
  "assistant_response": "The top 5 conversations by message count are ...\nSQL Used: SELECT ...",
  "generated_sql": "SELECT ..."
}
```

## Safety behavior

- Only one SQL statement is allowed.
- Query must start with `SELECT` or `WITH`.
- The system blocks dangerous operations like `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, and others.
- A result limit is enforced when the model does not include one.

## Notes

- Keep credentials secure when sharing command examples.
- For production, prefer secrets management over plain text URLs.
