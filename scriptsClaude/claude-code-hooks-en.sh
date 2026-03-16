curl -X POST http://localhost:3456/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Claude Code",
    "message": "Task completed or requires input."
  }'