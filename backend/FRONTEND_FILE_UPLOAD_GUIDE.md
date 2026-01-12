# File Upload Implementation Guide for Frontend

## Backend API Overview

The backend provides a **one-step file upload** endpoint that handles both file storage and attachment to container entries.

### Endpoint: Upload File to Container Entry

```
POST /api/terminal/entries/{entry_id}/upload_file/
```

**Authentication**: Bearer token required
**Content-Type**: multipart/form-data

**Form Parameters**:
- `file` (required): The file to upload
- `category` (optional, default: `container_image`): File category code
  - Options: `container_image`, `invoice_pdf`, `bill_of_lading`, `general_document`
- `attachment_type` (optional, default: `container_photo`): Custom type label
  - Examples: `container_photo`, `damage_evidence`, `invoice`, `bill_of_lading`
- `description` (optional): Text description of the file
- `is_public` (optional, default: `false`): String `true` or `false`

**Success Response** (201):
```json
{
  "file": {
    "id": "uuid",
    "url": "/media/files/2025/10/02/uuid-filename.jpg",
    "original_filename": "photo.jpg",
    "file_category": {"code": "container_image", "name": "Container Image"},
    "mime_type": "image/jpeg",
    "size": 2458624,
    "width": 1920,
    "height": 1080,
    "created_at": "2025-10-02T14:30:00Z"
  },
  "attachment_id": 42,
  "attachment_type": "container_photo",
  "description": "Front view of container"
}
```

**Error Response** (400):
```json
{
  "error": "No file provided"
}
```

### Endpoint: Get All Files for Container Entry

```
GET /api/terminal/entries/{entry_id}/files/
```

**Authentication**: Bearer token required

**Success Response** (200):
```json
[
  {
    "attachment_id": 42,
    "attachment_type": "container_photo",
    "description": "Front view",
    "display_order": 0,
    "file": {
      "id": "uuid",
      "url": "/media/files/2025/10/02/uuid-filename.jpg",
      "original_filename": "photo.jpg",
      "mime_type": "image/jpeg",
      "size": 2458624,
      "width": 1920,
      "height": 1080
    }
  }
]
```

### Endpoint: Remove File from Container Entry

```
DELETE /api/terminal/entries/{entry_id}/remove_file/{attachment_id}/
```

**Authentication**: Bearer token required

**Success Response** (200):
```json
{
  "message": "File removed successfully"
}
```

**Error Response** (404):
```json
{
  "error": "Attachment not found"
}
```

**Note**: Deleting an attachment will soft-delete the underlying file (sets `is_active=false`) if it's not attached to any other records.

## Implementation Tasks

### Task 1: Create File Upload Component
Create a reusable component that allows users to:
- Select a file via input or drag-and-drop
- Specify optional description
- Choose attachment type (dropdown or predefined based on context)
- Display upload progress
- Show success/error messages

### Task 2: Implement Upload Function
Create an async function that:
- Constructs FormData with file and parameters
- Sends POST request to `/api/terminal/entries/{entry_id}/upload_file/`
- Handles loading states, errors, and success responses
- Returns the uploaded file data

### Task 3: Display Uploaded Files
Create a component that:
- Fetches files using GET `/api/terminal/entries/{entry_id}/files/`
- Displays file thumbnails (for images) or icons (for documents)
- Shows file metadata (name, size, type, description)
- Provides download/view functionality
- Allows deletion using DELETE `/api/terminal/entries/{entry_id}/remove_file/{attachment_id}/`

### Task 4: Integration Points
Integrate file upload into:
- Container entry creation/edit forms
- Container detail view
- Any other relevant screens where documentation is needed

## Technical Notes

1. **File Size Limits**: Backend validates file sizes per category (typically 5-15MB)
2. **MIME Type Validation**: Backend validates allowed file types per category
3. **Security**: All endpoints require JWT authentication
4. **File URLs**: Use `file.url` from response - they're relative paths, prepend API base URL if needed
5. **Image Dimensions**: Available in response for images (`width`, `height`)
6. **Error Handling**: Backend returns structured error responses with `{error: "message"}`

## Example: Vanilla JavaScript Implementation

```javascript
// Upload file
async function uploadFileToEntry(entryId, file, options = {}) {
  const formData = new FormData();
  formData.append('file', file);

  if (options.category) formData.append('category', options.category);
  if (options.attachmentType) formData.append('attachment_type', options.attachmentType);
  if (options.description) formData.append('description', options.description);
  if (options.isPublic !== undefined) formData.append('is_public', String(options.isPublic));

  const response = await fetch(`/api/terminal/entries/${entryId}/upload_file/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`
    },
    body: formData
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Upload failed');
  }

  return response.json();
}

// Get files for entry
async function getEntryFiles(entryId) {
  const response = await fetch(`/api/terminal/entries/${entryId}/files/`, {
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`
    }
  });

  if (!response.ok) throw new Error('Failed to fetch files');
  return response.json();
}

// Remove file from entry
async function removeFileFromEntry(entryId, attachmentId) {
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
const fileInput = document.querySelector('input[type="file"]');
const result = await uploadFileToEntry(123, fileInput.files[0], {
  category: 'container_image',
  attachmentType: 'damage_evidence',
  description: 'Damage on left side',
  isPublic: false
});
console.log('Uploaded:', result.file.url);

// Remove file
await removeFileFromEntry(123, result.attachment_id);
console.log('File removed');
```

## Expected Deliverables

1. Reusable file upload component with progress indication
2. File gallery/list component showing uploaded files
3. Integration into container entry screens
4. Error handling and user feedback
5. Loading states during upload/fetch operations

## Questions?

If anything is unclear or you need backend endpoint modifications, contact the backend team.
