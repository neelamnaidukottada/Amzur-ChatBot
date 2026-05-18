# 📡 LangChain Pandas Agent - API Reference & Examples

## API Base URL
```
http://localhost:8000/api/data
```

## 🔐 Authentication
All endpoints require JWT Bearer token:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 1️⃣ Upload Spreadsheet

### Endpoint
```
POST /api/data/upload
```

### Request
```bash
curl -X POST http://localhost:8000/api/data/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data.csv"
```

### Supported Formats
- `.csv` - Comma-separated values
- `.xlsx` - Excel 2007+
- `.xls` - Excel 97-2003

### Request Validation
| Check | Requirement |
|-------|-------------|
| File Type | CSV, XLSX, XLS only |
| File Size | Max 20MB (configurable) |
| Content | Valid spreadsheet format |

### Response (200 OK)
```json
{
  "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "sales_data.xlsx",
  "source": "file",
  "rows": 1500,
  "columns": 12,
  "column_names": [
    "Date",
    "Product",
    "Region",
    "Sales",
    "Units",
    "Cost"
  ],
  "sample_data": [
    {
      "Date": "2024-01-01",
      "Product": "Widget A",
      "Region": "North",
      "Sales": 5000,
      "Units": 100,
      "Cost": 2000
    }
  ]
}
```

### Error Responses

**400 - Invalid File Type**
```json
{
  "detail": "File must be CSV or Excel (.xlsx, .xls)"
}
```

**413 - File Too Large**
```json
{
  "detail": "File size exceeds 20MB limit"
}
```

---

## 2️⃣ Connect Google Sheet

### Endpoint
```
POST /api/data/google-sheet
```

### Option A: Using Google Sheet URL
```bash
curl -X POST http://localhost:8000/api/data/google-sheet \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "google_sheet_url": "https://docs.google.com/spreadsheets/d/1rN3E...abc/edit",
    "worksheet_name": "Sheet1"
  }'
```

### Option B: Using Google Sheet ID
```bash
curl -X POST http://localhost:8000/api/data/google-sheet \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "google_sheet_id": "1rN3E...abc",
    "worksheet_name": "Sales"
  }'
```

### Pre-requisites
1. Sheet must be shared with:
   ```
   amzur-chatbot-sheets@sturdy-analyzer-495014-n7.iam.gserviceaccount.com
   ```
2. Service account credentials configured in `.env`

### Response (200 OK)
```json
{
  "dataset_id": "223f5678-f90c-23e4-b567-527625285111",
  "filename": "Google Sheet: 1rN3E...abc",
  "source": "google_sheet",
  "rows": 850,
  "columns": 8,
  "column_names": [
    "Employee",
    "Department",
    "Salary",
    "Hire Date"
  ],
  "sheet_id": "1rN3E...abc"
}
```

### Error Responses

**400 - Missing Sheet Identifier**
```json
{
  "detail": "Either google_sheet_url or google_sheet_id must be provided"
}
```

**403 - Access Denied**
```json
{
  "detail": "Failed to connect to Google Sheet: Access denied. Share the sheet with: amzur-chatbot-sheets@sturdy-analyzer-495014-n7.iam.gserviceaccount.com"
}
```

---

## 3️⃣ Query Dataset

### Endpoint
```
POST /api/data/query
```

### Request
```bash
curl -X POST http://localhost:8000/api/data/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
    "question": "What is the total sales by region?",
    "include_context": true
  }'
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dataset_id` | string | Yes | UUID from upload/connect |
| `question` | string | Yes | Natural language question |
| `include_context` | boolean | No | Use conversation history (default: true) |

### Query Examples

**Simple Aggregation**
```json
{
  "dataset_id": "...",
  "question": "What is the average sales value?"
}
```

**Filtering**
```json
{
  "dataset_id": "...",
  "question": "Show me all sales greater than $10,000"
}
```

**Grouping**
```json
{
  "dataset_id": "...",
  "question": "Calculate total sales by product"
}
```

**Trend Analysis**
```json
{
  "dataset_id": "...",
  "question": "What is the sales trend over the months?"
}
```

**Comparison**
```json
{
  "dataset_id": "...",
  "question": "Compare sales between Q1 and Q2"
}
```

**Context-Aware Follow-up**
```json
{
  "dataset_id": "...",
  "question": "What about just the North region?"
}
```

### Response (200 OK)
```json
{
  "success": true,
  "question": "What is the total sales by region?",
  "answer": "Based on the data:\n- North: $234,500\n- South: $189,300\n- East: $267,100\n- West: $156,800\nTotal across all regions: $847,700",
  "source": "sales_data.xlsx",
  "row_count": 1500,
  "column_count": 12,
  "columns": ["Date", "Product", "Region", "Sales", ...],
  "has_context": true
}
```

### Error Responses

**404 - Dataset Not Found**
```json
{
  "detail": "Dataset not found: 123e4567-e89b-12d3-a456-426614174000"
}
```

**400 - Query Failed**
```json
{
  "detail": "Query failed: Error executing dataframe operation"
}
```

---

## 4️⃣ List Active Datasets

### Endpoint
```
GET /api/data/datasets
```

### Request
```bash
curl -X GET http://localhost:8000/api/data/datasets \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response (200 OK)
```json
{
  "datasets": [
    {
      "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "sales_data.xlsx",
      "source": "file",
      "shape": {
        "rows": 1500,
        "columns": 12
      },
      "columns": ["Date", "Product", "Region", "Sales", ...],
      "created_at": "2024-01-15T10:30:00",
      "last_accessed": "2024-01-15T12:45:30",
      "query_count": 8
    },
    {
      "dataset_id": "223f5678-f90c-23e4-b567-527625285111",
      "filename": "Google Sheet: 1rN3E...abc",
      "source": "google_sheet",
      "shape": {
        "rows": 850,
        "columns": 8
      },
      "columns": ["Employee", "Department", "Salary", ...],
      "created_at": "2024-01-15T11:00:00",
      "last_accessed": "2024-01-15T13:20:15",
      "query_count": 3
    }
  ],
  "total": 2
}
```

---

## 5️⃣ Get Dataset Information

### Endpoint
```
GET /api/data/datasets/{dataset_id}
```

### Request
```bash
curl -X GET http://localhost:8000/api/data/datasets/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response (200 OK)
```json
{
  "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "sales_data.xlsx",
  "source": "file",
  "shape": {
    "rows": 1500,
    "columns": 12
  },
  "columns": ["Date", "Product", "Region", "Sales", "Units", "Cost"],
  "created_at": "2024-01-15T10:30:00",
  "last_accessed": "2024-01-15T14:50:22",
  "query_count": 12,
  "column_info": {
    "Date": "datetime64[ns]",
    "Product": "object",
    "Region": "object",
    "Sales": "float64",
    "Units": "int64",
    "Cost": "float64"
  },
  "missing_values": {
    "Date": 0,
    "Product": 0,
    "Region": 2,
    "Sales": 0,
    "Units": 0,
    "Cost": 5
  }
}
```

### Error Response

**404 - Dataset Not Found**
```json
{
  "detail": "Dataset not found: 123e4567-e89b-12d3-a456-426614174000"
}
```

---

## 6️⃣ Delete Dataset

### Endpoint
```
DELETE /api/data/datasets/{dataset_id}
```

### Request
```bash
curl -X DELETE http://localhost:8000/api/data/datasets/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response (200 OK)
```json
{
  "success": true,
  "message": "Dataset 123e4567-e89b-12d3-a456-426614174000 deleted"
}
```

### Error Response

**404 - Dataset Not Found**
```json
{
  "detail": "Dataset not found: 123e4567-e89b-12d3-a456-426614174000"
}
```

---

## 🔄 Typical Workflow

### Step 1: Upload Data
```bash
# Upload spreadsheet
curl -X POST http://localhost:8000/api/data/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@sales.csv"
```
**Save the `dataset_id` from response**

### Step 2: Ask Questions
```bash
# Query 1: Initial question
curl -X POST http://localhost:8000/api/data/query \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "DATASET_ID",
    "question": "What is total revenue?"
  }'
```

### Step 3: Follow-up Questions
```bash
# Query 2: Context-aware follow-up
curl -X POST http://localhost:8000/api/data/query \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "DATASET_ID",
    "question": "What about just the North region?"
  }'
```

### Step 4: View Dataset Info
```bash
curl -X GET http://localhost:8000/api/data/datasets/DATASET_ID \
  -H "Authorization: Bearer TOKEN"
```

### Step 5: Clean Up
```bash
curl -X DELETE http://localhost:8000/api/data/datasets/DATASET_ID \
  -H "Authorization: Bearer TOKEN"
```

---

## 📊 Status Codes

| Code | Meaning |
|------|---------|
| **200** | Success |
| **400** | Bad Request (validation error) |
| **401** | Unauthorized (missing/invalid token) |
| **404** | Not Found (dataset doesn't exist) |
| **413** | Request Entity Too Large (file too big) |
| **500** | Server Error |

---

## 🚀 Performance Tips

1. **Large Files:** Split into smaller chunks (< 10MB)
2. **Complex Queries:** Start with simple questions, then build
3. **Multiple Datasets:** Use different `dataset_id` for each
4. **Cleanup:** Delete unused datasets after use
5. **Sessions:** Sessions auto-expire after 60 minutes

---

## 💬 Natural Language Query Best Practices

### ✅ Good Queries
- "What is the total sales?"
- "Calculate average price by category"
- "Show me the top 10 customers by revenue"
- "What is the sales trend over time?"
- "Compare Q1 vs Q2 performance"

### ❌ Avoid
- Very vague questions
- Questions about data that doesn't exist
- Extremely complex multi-step operations
- Queries expecting code output

### Tips
1. Be specific about what you want
2. Reference actual column names
3. Mention date ranges if applicable
4. Use business terminology naturally
5. Ask one question at a time

---

## 🔒 Security Considerations

- All endpoints require valid JWT token
- File uploads validated for type and size
- Google Sheets access restricted by sharing settings
- No sensitive data logged
- Session data stored in-memory only
- Auto-cleanup after inactivity

---

## 📱 Example Frontend Integration

```javascript
// React/Next.js Example
const uploadFile = async (file, token) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch('/api/data/upload', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  
  return res.json();
};

const queryData = async (datasetId, question, token) => {
  const res = await fetch('/api/data/query', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      dataset_id: datasetId,
      question: question,
      include_context: true
    })
  });
  
  return res.json();
};
```

---

**API Version:** 1.0
**Last Updated:** January 15, 2025
**Status:** ✅ Production Ready
