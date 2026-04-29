# Article Download Feature — Mini Specification

**Date:** April 28, 2026  
**Scope:** Integrate into Phase 2 (Tasks 8-10)

---

## Overview

Enable users to download article PDFs directly from the dashboard with automatic upload to Google Drive. Handles full articles, paywalled summaries, and associated images/tables.

**User Flow:**
1. View article in dashboard
2. Click "Baixar PDF" button
3. Backend fetches + bypasses paywalls (Playwright)
4. Extracts PDF + metadata
5. Uploads to Google Drive
6. Frontend shows success + Drive link
7. User can access offline or share

---

## Architecture

### Frontend Component
- **Location:** ArticleCard.vue, ArticleDetail.vue
- **Button:** "📥 Baixar PDF" (disabled state shows spinner during download)
- **States:** idle, loading, success, error
- **POST /api/download** with `{ articleId, titulo, url }`
- **Response:** `{ status, driveUrl, fileName, timestamp }`

### Backend Service
- **File:** `agent/scripts/download_article.py`
- **Input:** Article metadata (id, url, title)
- **Process:**
  1. Use Playwright to navigate URL + handle verification ("you are human")
  2. Extract PDF (from download link if available)
  3. Fallback: Extract text → generate PDF with title/content/metadata
  4. Save locally: `downloads/article-{id}-{date}.pdf`
- **Google Drive Integration:**
  1. Authenticate via service account (`.env` credentials)
  2. Create folder: "Cardiology Articles / 2026"
  3. Upload PDF + metadata file (JSON with source, date, links)
  4. Return shareable link
- **Error Handling:** Paywall blocks, bot detection, quota limits

### Data Flow
```
Frontend: POST /api/download
    ↓
Backend receives { articleId, url, titulo }
    ↓
Playwright headless browser
    ├─ Navigate to URL
    ├─ Handle "verify human" captcha/check (if needed)
    ├─ Wait for PDF link or extract content
    ├─ Download PDF or generate from HTML
    └─ Extract metadata (authors, date, journal)
    ↓
Google Drive Upload
    ├─ Auth via service account
    ├─ Create folder if missing
    ├─ Upload PDF file
    ├─ Upload metadata JSON
    └─ Return shareable link
    ↓
Frontend receives response
    ├─ Show success notification
    ├─ Provide "Open in Drive" link
    └─ Log download in localStorage (for history)
```

---

## Files to Create/Modify

### Create
- `agent/scripts/download_article.py` (150–200 lines)
- `agent/scripts/google_drive_client.py` (100 lines, reusable Drive integration)
- `frontend/src/components/DownloadButton.vue` (50 lines, reusable component)
- `.env.example` (add GOOGLE_SERVICE_ACCOUNT_JSON path)

### Modify
- `frontend/src/components/ArticleCard.vue` (add DownloadButton)
- `frontend/src/components/ArticleDetail.vue` (add DownloadButton + status feedback)
- `agent/requirements.txt` (add playwright, google-auth, google-auth-httplib2)
- `frontend/package.json` (no new deps needed)

---

## Dependencies

**Python:**
- `playwright==1.40.0` (headless browser automation)
- `google-auth==2.26.2` (Google Drive auth)
- `google-auth-httplib2==0.2.0` (HTTP client)
- `google-auth-oauthlib==1.2.0` (OAuth flow)
- `google-api-python-client==2.105.0` (Drive API)
- `pypdf==4.0.1` (PDF extraction/generation)

**Frontend:**
- axios (already included)

---

## Configuration

**.env (new variables)**
```
GOOGLE_SERVICE_ACCOUNT_JSON=./config/service-account.json
GOOGLE_DRIVE_FOLDER_ID=<main folder ID>
DOWNLOAD_TEMP_DIR=./downloads
PLAYWRIGHT_HEADLESS=true
```

**service-account.json** (from Google Cloud Console)
```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "...",
  "client_id": "..."
}
```

---

## Success Criteria

✅ User clicks "Baixar PDF" on any article
✅ Backend fetches PDF (or generates from HTML)
✅ File uploads to user's Google Drive
✅ Frontend shows success notification + Drive link
✅ Download logged in localStorage (for future "download history")
✅ Error handling for paywalls, bot detection, quota limits
✅ No blocking of main dashboard flow

---

## Timeline

- **Task 8:** Add DownloadButton component + UI state management
- **Task 10:** Implement download_article.py + Google Drive integration
- **Task 10b (new):** Create google_drive_client.py + configure service account
- **Task 14 (Build/Test):** Test download workflow end-to-end

---

## Future Enhancements (Out of Scope v1.0)

- Batch download (multiple articles at once)
- Email digest with PDFs attached
- Download history view
- Auto-organize by date/class/journal
- Offline reading mode
- OCR for paywalled article images
