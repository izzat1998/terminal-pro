# File Deletion API Documentation

## Endpoint

```
DELETE /api/terminal/entries/{entry_id}/remove_file/{attachment_id}/
```

## Authentication

Bearer token required in Authorization header.

## Parameters

- `entry_id` (path): The container entry ID
- `attachment_id` (path): The attachment ID to remove

## Response

### Success (200)
```json
{
  "message": "File removed successfully"
}
```

### Error (404)
```json
{
  "error": "Attachment not found"
}
```

## Behavior

1. Removes the attachment from the container entry
2. If the file is not used by any other attachments, it will be soft-deleted (sets `is_active=false`)
3. If the file is still attached to other records, only the attachment is removed

## Example Usage

### JavaScript/Fetch
```javascript
async function removeFile(entryId, attachmentId) {
  const response = await fetch(`/api/terminal/entries/${entryId}/remove_file/${attachmentId}/`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to remove file');
  }

  return response.json();
}

// Usage
await removeFile(123, 42);
console.log('File removed successfully');
```

### Axios
```javascript
async function removeFile(entryId, attachmentId) {
  const response = await axios.delete(
    `/api/terminal/entries/${entryId}/remove_file/${attachmentId}/`,
    {
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`
      }
    }
  );
  return response.data;
}
```

### cURL
```bash
curl -X DELETE \
  "http://localhost:8000/api/terminal/entries/123/remove_file/42/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
